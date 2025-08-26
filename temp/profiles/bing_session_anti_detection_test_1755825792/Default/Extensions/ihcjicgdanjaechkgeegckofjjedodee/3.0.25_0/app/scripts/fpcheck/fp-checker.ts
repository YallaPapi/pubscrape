import { putHash } from "./hubble";

export class FPChecker {
  private static CACHE: Record<number, CacheEntry> = {};
  private static readonly MAX_CACHE_SIZE = 1_000;
  private static readonly IMMINENT_EXPIRY_THRESHOLD_MS = 60 * 60 * 1000; // 1 hour
  private debugMode: boolean = false;

  constructor(debugMode?: boolean) {
    this.debugMode = debugMode ?? false;
  }

  public async shouldBlock(
    ruleId: number
  ): Promise<boolean> {
    const cacheEntry = await this.getOrCreateCachedEntry(ruleId);
    if (cacheEntry) {
      return cacheEntry.fpClassification !== "good";
    }

    return true;
  }

  // Check only the cache, don't fetch from hubble
  public shouldBlockCached(ruleId: number): boolean | null {
    const cacheEntry = FPChecker.CACHE[ruleId];
    if (cacheEntry) {
      if (!cacheEntry.isExpired) {
        return cacheEntry.fpClassification !== "good";
      } else {
        delete FPChecker.CACHE[ruleId];
      }
    }

    return null;
  }

  // check to see if we have the hash in cache
  // if we do, check if it's expired
  // if it's expired, fetch from hubble
  // if it's not expired, return the cached value
  private async getOrCreateCachedEntry(
    ruleId: number
  ): Promise<CacheEntry | null> {
    const cacheEntry = FPChecker.CACHE[ruleId];
    if (cacheEntry && !cacheEntry.isExpired) {
      return cacheEntry;
    }

    const env = this.debugMode ? "staging" : "prod";
    const hash = await generateSHA256(ruleId.toString());
    const putHashResp = await putHash(hash, ruleId, { env });
    if (putHashResp.results.length === 0) {
      return null;
    }

    const result = putHashResp.results[0];
    let classification: FpClassification = "unknown";
    if (result.classification === "GOOD") {
      classification = "good";
    } else if (result.classification === "UNKNOWN") {
      classification = "unknown";
    }

    let expiresAt: Date | undefined;
    if (result.trust_expires_at) {
      if (typeof result.trust_expires_at === "string") {
        expiresAt = new Date(result.trust_expires_at);
      } else {
        const expirySeconds = result.trust_expires_at;
        // expires x seconds from now
        expiresAt = new Date(Date.now() + expirySeconds * 1000);
      }
    }

    const newEntry = new CacheEntry(
      ruleId,
      classification,
      expiresAt,
    );

    // Trim cache periodically to maintain size limit
    this.trimCache();

    FPChecker.CACHE[ruleId] = newEntry;

    return newEntry;
  }

  /**
   * Trims the cache to maintain the maximum size limit.
   * Removes entries in the following order:
   * 1. Expired entries (past expiry time)
   * 2. Entries with imminent expiry (within 1 hour)
   * 3. Entries without expiry dates in FIFO order (oldest first)
   */
  private trimCache(): void {
    const cacheSize = Object.keys(FPChecker.CACHE).length;
    if (cacheSize <= FPChecker.MAX_CACHE_SIZE) {
      return;
    }

    const now = new Date();
    const entriesToRemove: string[] = [];

    // Get all cache entries with their hashes
    const cacheEntries = Object.entries(FPChecker.CACHE).map(
      ([ruleId, entry]) => ({
        ruleId,
        entry,
      })
    );

    // First, collect expired entries
    const expiredEntries = cacheEntries.filter(({ entry }) => entry.isExpired);
    entriesToRemove.push(...expiredEntries.map(({ ruleId }) => ruleId));

    // If we still need to remove more entries, collect imminent expiry entries
    if (cacheSize - entriesToRemove.length > FPChecker.MAX_CACHE_SIZE) {
      const imminentExpiryEntries = cacheEntries.filter(({ entry }) => {
        if (entry.isExpired || !entry.expiresAt) {
          return false;
        }
        const timeUntilExpiry = entry.expiresAt.getTime() - now.getTime();
        return timeUntilExpiry <= FPChecker.IMMINENT_EXPIRY_THRESHOLD_MS;
      });

      // Add imminent expiry entries that aren't already marked for removal
      const newImminentEntries = imminentExpiryEntries
        .filter(({ ruleId }) => !entriesToRemove.includes(ruleId))
        .map(({ ruleId }) => ruleId);
      entriesToRemove.push(...newImminentEntries);
    }

    // If we still need to remove more entries, remove oldest entries without expiry dates (FIFO)
    if (cacheSize - entriesToRemove.length > FPChecker.MAX_CACHE_SIZE) {
      const nonExpiryEntries = cacheEntries
        .filter(
          ({ ruleId, entry }) =>
            !entriesToRemove.includes(ruleId) && !entry.expiresAt
        )
        .sort(
          (a, b) => a.entry.createdAt.getTime() - b.entry.createdAt.getTime()
        ); // Sort by creation time (oldest first)

      const remainingToRemove =
        cacheSize - entriesToRemove.length - FPChecker.MAX_CACHE_SIZE;
      const oldestEntriesToRemove = nonExpiryEntries
        .slice(0, remainingToRemove)
        .map(({ ruleId }) => ruleId);
      entriesToRemove.push(...oldestEntriesToRemove);
    }

    // Remove the selected entries
    entriesToRemove.forEach((ruleId) => {
      delete FPChecker.CACHE[ruleId];
    });

    if (entriesToRemove.length > 0) {
      console.debug(
        `FPChecker: Trimmed ${
          entriesToRemove.length
        } cache entries. Cache size: ${Object.keys(FPChecker.CACHE).length}`
      );
    }
  }
}

type FpClassification = 'good' | 'unknown';

class CacheEntry {
  private ruleId: number;
  private classification: FpClassification;
  private _expiresAt?: Date;
  private _createdAt: Date;

  constructor(
    ruleId: number,
    classification: FpClassification,
    expiresAt?: Date,
  ) {
    this.ruleId = ruleId;
    this.classification = classification;
    this._expiresAt = expiresAt;
    this._createdAt = new Date();
  }

  get fpClassification(): FpClassification {
    return this.classification;
  }

  get trustAlways(): boolean {
    return !!this._expiresAt === false;
  }

  get isExpired(): boolean {
    if (!this._expiresAt) {
      return false;
    }
    return this._expiresAt < new Date();
  }

  get createdAt(): Date {
    return this._createdAt;
  }

  get expiresAt(): Date | undefined {
    return this._expiresAt;
  }
}

async function generateSHA256(text: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

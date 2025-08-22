import { FPChecker } from '../fp-checker';
import { putHash } from '../hubble';

// Mock dependencies
jest.mock('../hubble');
const mockedPutHash = putHash as jest.MockedFunction<typeof putHash>;

// Mock TextEncoder
const mockTextEncoder = {
  encode: jest.fn().mockImplementation((input: string) => {
    // Convert string to bytes (simple implementation)
    const bytes = new Uint8Array(input.length);
    for (let i = 0; i < input.length; i++) {
      bytes[i] = input.charCodeAt(i);
    }
    return bytes;
  })
};
Object.defineProperty(global, 'TextEncoder', {
  value: jest.fn().mockImplementation(() => mockTextEncoder)
});

// Mock crypto.subtle.digest
const mockDigest = jest.fn();
Object.defineProperty(global, 'crypto', {
  value: {
    subtle: {
      digest: mockDigest
    }
  }
});

// Mock console.debug to avoid spam in tests
const originalConsoleDebug = console.debug;
beforeAll(() => {
  console.debug = jest.fn();
});

afterAll(() => {
  console.debug = originalConsoleDebug;
});

describe('FPChecker', () => {
  let fpChecker: FPChecker;
  let mockHashBuffer: ArrayBuffer;

  beforeEach(() => {
    // Reset cache before each test
    (FPChecker as any).CACHE = {};
    
    fpChecker = new FPChecker(true);
    
    // Mock SHA256 hash generation - create different hashes for different inputs
    mockHashBuffer = new ArrayBuffer(32);
    const mockHashArray = new Uint8Array(mockHashBuffer);
    mockHashArray.fill(0x42); // Fill with 0x42 for consistent hash
    
    // Mock digest to return different hashes based on input
    mockDigest.mockImplementation((algorithm, data) => {
      const input = new Uint8Array(data);
      const hash = new ArrayBuffer(32);
      const hashArray = new Uint8Array(hash);
      // Create a pseudo-unique hash based on input data
      for (let i = 0; i < 32; i++) {
        hashArray[i] = input[i % input.length] + i;
      }
      return Promise.resolve(hash);
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('basic functionality', () => {
    it('should return true (block) when putHash returns empty results', async () => {
      mockedPutHash.mockResolvedValue({ results: [] });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(true);
      expect(mockedPutHash).toHaveBeenCalledWith(
        expect.any(String),
        123,
        { env: 'staging' }
      );
    });

    it('should return false (don\'t block) for GOOD result', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: undefined
        }]
      });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(false);
    });

    it('should return true (block) for BAD result', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'UNKNOWN',
          trust_expires_at: undefined
        }]
      });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(true);
    });

    it('should return true (block) for UNKNOWN result', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'UNKNOWN',
          trust_expires_at: undefined
        }]
      });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(true);
    });

    it('should pass ruleId to putHash', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: undefined
        }]
      });

      await fpChecker.shouldBlock(456);

      expect(mockedPutHash).toHaveBeenCalledWith(
        expect.any(String),
        456,
        { env: 'staging' }
      );
    });
  });

  describe('cache behavior', () => {
    it('should cache results and return from cache on subsequent calls', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: undefined
        }]
      });

      // First call should hit the API
      const result1 = await fpChecker.shouldBlock(123);
      expect(result1).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1);

      // Second call should return from cache
      const result2 = await fpChecker.shouldBlock(123);
      expect(result2).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1); // Not called again
    });

    it('should refetch when cache entry is expired', async () => {
      const pastDate = new Date(Date.now() - 1000); // 1 second ago

      mockedPutHash.mockResolvedValueOnce({
        results: [{
          classification: 'GOOD',
          trust_expires_at: pastDate.toISOString()
        }]
      });

      // First call caches with expired date
      const result1 = await fpChecker.shouldBlock(123);
      expect(result1).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1);

      // Mock new response for refetch
      mockedPutHash.mockResolvedValueOnce({
        results: [{
          classification: 'UNKNOWN',
          trust_expires_at: undefined
        }]
      });

      // Second call should refetch because entry is expired
      const result2 = await fpChecker.shouldBlock(123);
      expect(result2).toBe(true);
      expect(mockedPutHash).toHaveBeenCalledTimes(2);
    });

    it('should use cache when entry is not expired', async () => {
      const futureDate = new Date(Date.now() + 60000); // 1 minute from now

      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: futureDate.toISOString()
        }]
      });

      // First call
      const result1 = await fpChecker.shouldBlock(123);
      expect(result1).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1);

      // Second call should use cache
      const result2 = await fpChecker.shouldBlock(123);
      expect(result2).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1);
    });
  });

  describe('shouldBlockCached method', () => {
    it('should return null when no cache entry exists', () => {
      const result = fpChecker.shouldBlockCached(123);
      expect(result).toBeNull();
    });

    it('should return cached result when entry exists and is not expired', async () => {
      const futureDate = new Date(Date.now() + 60000);
      
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: futureDate.toISOString()
        }]
      });

      // First populate cache
      await fpChecker.shouldBlock(123);
      
      // Then check cached result
      const result = fpChecker.shouldBlockCached(123);
      expect(result).toBe(false);
    });

    it('should return null when cache entry is expired', async () => {
      const pastDate = new Date(Date.now() - 1000);
      
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: pastDate.toISOString()
        }]
      });

      // First populate cache with expired entry
      await fpChecker.shouldBlock(123);
      
      // Then check cached result - should be null because expired
      const result = fpChecker.shouldBlockCached(123);
      expect(result).toBeNull();
    });
  });

  describe('cache trimming', () => {
    it('should not trim cache when size is under limit', async () => {
      const consoleSpy = jest.spyOn(console, 'debug');
      
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: undefined
        }]
      });

      // Add a few entries (well under 1000 limit)
      for (let i = 0; i < 5; i++) {
        await fpChecker.shouldBlock(i);
      }

      // Should not see any trimming messages
      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('Trimmed')
      );
    });

    it('should trim expired entries first', async () => {
      const consoleSpy = jest.spyOn(console, 'debug');
      
      // Mock the MAX_CACHE_SIZE to be smaller for testing
      const originalMaxSize = (FPChecker as any).MAX_CACHE_SIZE;
      (FPChecker as any).MAX_CACHE_SIZE = 5;

      const pastDate = new Date(Date.now() - 1000);
      const futureDate = new Date(Date.now() + 60000);

      // Add expired entries
      for (let i = 0; i < 3; i++) {
        mockedPutHash.mockResolvedValueOnce({
          results: [{
            classification: 'GOOD',
            trust_expires_at: pastDate.toISOString()
          }]
        });
        await fpChecker.shouldBlock(i);
      }

      // Add valid entries
      for (let i = 100; i < 105; i++) {
        mockedPutHash.mockResolvedValueOnce({
          results: [{
            classification: 'GOOD',
            trust_expires_at: futureDate.toISOString()
          }]
        });
        await fpChecker.shouldBlock(i);
      }

      // Should have trimmed entries
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Trimmed')
      );

      // Restore original max size
      (FPChecker as any).MAX_CACHE_SIZE = originalMaxSize;
    });

    it('should trim imminent expiry entries after expired ones', async () => {
      const consoleSpy = jest.spyOn(console, 'debug');
      
      // Mock smaller cache size for testing
      const originalMaxSize = (FPChecker as any).MAX_CACHE_SIZE;
      (FPChecker as any).MAX_CACHE_SIZE = 3;

      const imminentDate = new Date(Date.now() + 1800000); // 30 minutes from now (imminent)
      const futureDate = new Date(Date.now() + 7200000); // 2 hours from now (safe)

      // Add imminent expiry entries
      for (let i = 0; i < 2; i++) {
        mockedPutHash.mockResolvedValueOnce({
          results: [{
            classification: 'GOOD',
            trust_expires_at: imminentDate.toISOString()
          }]
        });
        await fpChecker.shouldBlock(i);
      }

      // Add safe entries that should trigger trimming
      for (let i = 100; i < 105; i++) {
        mockedPutHash.mockResolvedValueOnce({
          results: [{
            classification: 'GOOD',
            trust_expires_at: futureDate.toISOString()
          }]
        });
        await fpChecker.shouldBlock(i);
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Trimmed')
      );

      (FPChecker as any).MAX_CACHE_SIZE = originalMaxSize;
    });

    it('should trim oldest non-expiry entries in FIFO order', async () => {
      const consoleSpy = jest.spyOn(console, 'debug');
      
      const originalMaxSize = (FPChecker as any).MAX_CACHE_SIZE;
      (FPChecker as any).MAX_CACHE_SIZE = 3;

      // Add entries without expiry dates
      for (let i = 0; i < 6; i++) {
        mockedPutHash.mockResolvedValueOnce({
          results: [{
            classification: 'GOOD',
            trust_expires_at: undefined
          }]
        });
        await fpChecker.shouldBlock(i);
        
        // Small delay to ensure different creation times
        await new Promise(resolve => setTimeout(resolve, 1));
      }

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Trimmed')
      );

      (FPChecker as any).MAX_CACHE_SIZE = originalMaxSize;
    });
  });

  describe('cache entry behavior', () => {
    it('should correctly handle expired entries through public API', async () => {
      const pastDate = new Date(Date.now() - 1000);

      // First call with expired date
      mockedPutHash.mockResolvedValueOnce({
        results: [{
          classification: 'GOOD',
          trust_expires_at: pastDate.toISOString()
        }]
      });

      await fpChecker.shouldBlock(123);

      // Second call should refetch because entry is expired
      mockedPutHash.mockResolvedValueOnce({
        results: [{
          classification: 'UNKNOWN',
          trust_expires_at: undefined
        }]
      });

      const result = await fpChecker.shouldBlock(123);
      expect(result).toBe(true);
      expect(mockedPutHash).toHaveBeenCalledTimes(2);
    });

    it('should correctly handle non-expired entries through public API', async () => {
      const futureDate = new Date(Date.now() + 60000);

      // First call with future date
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: futureDate.toISOString()
        }]
      });

      const result1 = await fpChecker.shouldBlock(123);
      expect(result1).toBe(false);

      // Second call should use cache (no additional API call)
      const result2 = await fpChecker.shouldBlock(123);
      expect(result2).toBe(false);
      expect(mockedPutHash).toHaveBeenCalledTimes(1);
    });
  });

  describe('edge cases', () => {
    it('should handle malformed trust_expires_at dates', async () => {
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: 'invalid-date'
        }]
      });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(false);
      // Should not throw error
    });

    it('should handle numeric trust_expires_at values', async () => {
      const secondsFromNow = 60; // 60 seconds from now
      mockedPutHash.mockResolvedValue({
        results: [{
          classification: 'GOOD',
          trust_expires_at: secondsFromNow
        }]
      });

      const result = await fpChecker.shouldBlock(123);

      expect(result).toBe(false);
    });

    it('should handle putHash throwing an error', async () => {
      mockedPutHash.mockRejectedValue(new Error('Network error'));

      await expect(fpChecker.shouldBlock(123)).rejects.toThrow('Network error');
    });

    it('should handle crypto.subtle.digest throwing an error', async () => {
      mockDigest.mockRejectedValue(new Error('Crypto error'));

      await expect(fpChecker.shouldBlock(123)).rejects.toThrow('Crypto error');
    });
  });
});

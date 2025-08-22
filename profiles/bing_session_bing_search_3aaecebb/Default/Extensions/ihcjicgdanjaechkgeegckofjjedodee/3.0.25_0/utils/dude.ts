import { TARGET_BROWSER } from "@/app/scripts/browser-const";
import { chrome } from "./polyfill";
import { simpleStorageGet, simpleStorageSet } from "./storage";
import {
  browserName,
  fetchJSON,
  isIncognito,
  uuidCreate,
  uuidGet,
} from "./utils";

/*
  Base URL format:
  Prod: https://[productCode]-[versionMajor]-[versionMinor]-[patchNumber].v2.tel.malwarebytes.com
  Staging: https://[productCode]-[versionMajor]-[versionMinor]-[patchNumber].v2.tel.mwbsys-stage.com
*/
export class DudeClient {
  static readonly productCode = "mbgc-c";
  private baseUrl: string | undefined;
  private machineId: string | undefined;

  constructor(private readonly isProd: boolean = true) {}

  async getBaseUrl(): Promise<string> {
    if (this.baseUrl) {
      return this.baseUrl;
    }

    const manifestVersion = chrome.runtime.getManifest().version;
    // extract major, minor, patch
    const [major, minor, patch] = manifestVersion.split(".");

    this.baseUrl = this.isProd
      ? `https://${DudeClient.productCode}-${major}-${minor}-${patch}.v2.tel.malwarebytes.com`
      : `https://${DudeClient.productCode}-${major}-${minor}-${patch}.v2.tel.mwbsys-stage.com`;

    return this.baseUrl;
  }

  public async trackDailyStats(
    ads: number,
    malware: number,
    scams: number,
    skipThrottle: boolean = false
  ): Promise<boolean> {
    const adsPostId = uuidCreate();
    const malwarePostId = uuidCreate();
    const scamsPostId = uuidCreate();

    const reportDate = new Date().toISOString().split("T")[0];

    const measurements: Record<string, DudeAggregate[]> = {};
    if (ads > 0) {
      measurements.blocked_ads = [
        {
          date: reportDate,
          value: ads,
          post_id: adsPostId,
        },
      ];
    }
    if (malware > 0) {
      measurements.blocked_malware = [
        {
          date: reportDate,
          value: malware,
          post_id: malwarePostId,
        },
      ];
    }
    if (scams > 0) {
      measurements.blocked_scams = [
        {
          date: reportDate,
          value: scams,
          post_id: scamsPostId,
        },
      ];
    }

    return this.trackStats(
      {
        report_date: reportDate,
        measurements,
      },
      skipThrottle
    );
  }

  private async trackStats(
    stats: Pick<DudeStatsPayload, "report_date" | "measurements">,
    skipThrottle: boolean = false
  ): Promise<boolean> {
    const machineId = await this.getMachineId();
    if (!machineId) {
      console.debug("DudeClient: Machine ID not found. No data was sent.");
      return false;
    }

    if (!skipThrottle && (await this.throttle("stats", 1000 * 60 * 60 * 24))) {
      return false;
    }

    const uuid = await uuidGet();
    const _bName = browserName();
    console.debug(`DudeClient: BNAME IS: ${JSON.stringify(_bName)}`);

    const payload: DudeStatsPayload = {
      ...stats, // report_date, measurements
      machine_id: machineId,
      installation_token: `${_bName}-${uuid}`,
      user_id: "",
      client_uuid: uuid,
    };

    const baseUrl = await this.getBaseUrl();
    const url = `${baseUrl}/api/v1/device_stats`;
    try {
      await fetchJSON(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      console.debug("DudeClient: Stats sent to Data Dude");
      return true;
    } catch (err) {
      console.error("DudeClient: Error sending stats to Data Dude", err);
      return false;
    }
  }

  private async throttle(type: string, interval: number): Promise<boolean> {
    // @ts-ignore
    if (TARGET_BROWSER === "Firefox") {
      return true;
    }

    if (isIncognito()) {
      console.debug("DudeClient:Incognito Mode: No data was sent.");
      return true;
    }

    let dudeThrottle = await simpleStorageGet("dudeThrottle");
    if (
      dudeThrottle &&
      dudeThrottle[type] &&
      dudeThrottle[type].lastSendTime &&
      dudeThrottle[type].lastSendTime < Date.now() &&
      Date.now() < dudeThrottle[type].lastSendTime + interval
    ) {
      return true;
    }

    dudeThrottle = dudeThrottle || {};
    dudeThrottle[type] = dudeThrottle[type] || {};
    dudeThrottle[type].lastSendTime = Date.now();

    await simpleStorageSet({ dudeThrottle });
    return false;
  }

  public async getMachineId(): Promise<string | undefined> {
    if (!this.machineId) {
      this.machineId = await new Promise((resolve) => {
        simpleStorageGet("machineId").then((machineId) => {
          if (machineId) {
            this.machineId = machineId;
            console.log("DudeClient: machineId", this.machineId);
            resolve(machineId);
          } else {
            resolve(undefined);
          }
        });
      });
    }

    console.log("DudeClient: machineId", this.machineId);
    return this.machineId;
  }
}

interface DudeStatsPayload {
  machine_id: string;
  installation_token: string;
  user_id: string | undefined;
  client_uuid: string | undefined;
  report_date: string;
  measurements: {
    [key: string]: string | number | DudeAggregate[];
  };
}

export interface DudeAggregate {
  date: string;
  value: number;
  post_id: string;
}

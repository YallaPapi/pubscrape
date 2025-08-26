import { fetchJSON } from "@/utils/utils";
// import jwt from "jsonwebtoken";
import * as jose from "jose";
import { BUILD_NUMBER } from "../build-consts";
import { HUBBLE_ACCESS_KEY, HUBBLE_SECRET_KEY } from "../secrets-consts";
import { simpleStorageGet } from "@/utils/storage";

const HUBBLE_URL_PROD = "https://hubble.mb-cosmos.com/hashes";
const HUBBLE_URL_STAGING = "https://staging-hubble.mb-cosmos.com/hashes";


export async function putHash(
  hash: string,
  ruleId: number,
  { env = "prod" }: { env?: "prod" | "staging" } = {}
): Promise<PutHashResponse> {
  const url = env === "prod" ? HUBBLE_URL_PROD : HUBBLE_URL_STAGING;
  const version = chrome.runtime.getManifest().version;
  const machineId =
    (await simpleStorageGet("machineId")) || crypto.randomUUID();

  const token = await buildToken(
    HUBBLE_ACCESS_KEY,
    HUBBLE_SECRET_KEY,
    version,
    machineId
  );

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.hubble+json; version=2",
  };

  const payload = {
    hashes: [
      {
        rule_id: `${ruleId}`,
        sha256: hash,        
      },
    ],
    product_code: "bg",
    product_version: version,
    product_component: "bg",
    product_component_version: "1.0",
    product_build: `${BUILD_NUMBER}`,
    product_scantype: "scan",
    machine_id: machineId,
  };
  if (ruleId) {
    payload["rule_id"] = `${ruleId}`;
  }

  const response = await fetchJSON(url, {
    method: "PUT",
    headers: headers,
    body: JSON.stringify(payload),
  });
  return response as PutHashResponse;
}

async function buildToken(
  accessKey: string,
  secretKey: string,
  productVersion: string,
  machineId: string
): Promise<string> {
  const payload = {
    accesskey: accessKey,
    productcode: "mbgc-c",
    productversion: productVersion,
    productbuild: `${BUILD_NUMBER}`,
    machineid: machineId,
  };
  const secret = new TextEncoder().encode(secretKey);
  const jwt = await new jose.SignJWT(payload)
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .sign(secret);

  return jwt;
}

type PutHashResponse = {
  results: HubbleHash[];
};

type HubbleHash = {
  sha256?: string;
  md5?: string;
  send_file?: boolean;
  trust_expires_at?: string | number | undefined;
  classification: "UNKNOWN" | "GOOD";
  trust_always?: boolean;
};

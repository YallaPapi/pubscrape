
/**
 * @fileoverview Types for external messages in the Malwarebytes Browser Guard applicatin.
 * All messages should end with the suffix "Request" to indicate they are requests.
 */
export const MB_MY_ACCOUNT_DOMAIN = 'https://my.malwarebytes.com';

export const MSG_MA_GET_BASE_DATA_REQUEST = 'MSG_MA_GET_BASE_DATA_REQUEST';
export const MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST = 'MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST';

export const MSG_MA_GET_BASE_DATA_RESPONSE = 'MSG_MA_GET_BASE_DATA_RESPONSE';
export const MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE = 'MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE';

export const MESSAGE_TYPES = [
    MSG_MA_GET_BASE_DATA_REQUEST,
    MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST
    // Add more message types as needed
] as const;

export const RESPONSE_TYPES = {
    MSG_MA_GET_BASE_DATA_REQUEST: MSG_MA_GET_BASE_DATA_RESPONSE,
    MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST: MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE
    // Add more response types as needed
} as const;

export type MessageType = typeof MESSAGE_TYPES[number];

export type ResponseType = typeof RESPONSE_TYPES[MessageType];

export type DetectionTypeRecord =  { date: string; count: number }[];

export type AllTypesDetection = {
    ads: number;
    content: number;
    malwares: number;
    scams: number;
    silentAds: number;
    silentContent: number;
    silentMalwares: number;
    silentScams: number;
    ts: number;
};

export type BaseDataResponse = {
    version: string;
    settings: { [key: string]: unknown; };
    detectionSummary: Record<string, DetectionTypeRecord>;
    supportedMessageTypes: MessageType[]; // Optional, for future extensibility
};


// Example of a structured message type
export interface ExternalMessage {
    type: MessageType;
    [key: string]: unknown; // additional optional properties depending on the message type
}

// BG to My Account messages response
export interface ToMyAccountResponse {
    type: ResponseType;
    success: boolean; // Indicates if the request was successful
    data?: BaseDataResponse; // Optional data for specific requests
    error?: string; // Optional error message
}
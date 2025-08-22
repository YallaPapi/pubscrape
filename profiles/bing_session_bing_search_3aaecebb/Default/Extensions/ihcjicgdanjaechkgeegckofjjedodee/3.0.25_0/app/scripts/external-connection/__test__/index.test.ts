import { onMessageExternalListener } from '../index';
import { MSG_MA_GET_BASE_DATA_REQUEST, MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, ExternalMessage } from '../types';
import * as handlers from '../handlers';
import * as Sentry from '@sentry/browser';
import { chrome } from '@/utils/polyfill';

jest.mock('../handlers', () => ({
    baseDataAggregationHandler: jest.fn(),
    enableAllProtectionsHandler: jest.fn(),
}));

jest.mock('@sentry/browser', () => ({
    captureException: jest.fn(),
}));

jest.mock('@/utils/polyfill', () => ({
    chrome: {
        runtime: {
            getManifest: jest.fn(() => ({ version: '3.0.21' })),
        },
        storage: {
            local: {
                get: jest.fn(),
                set: jest.fn(),
                remove: jest.fn(),
                clear: jest.fn(),
            },
        },
    },
}));

// Mock the settings module
jest.mock('@/app/scripts/settings', () => ({
    settings: {
        enableProtection: true,
        enableProtectionAds: true,
        enableProtectionMalware: true,
        enableProtectionScams: true,
        get: jest.fn(),
        set: jest.fn(),
        setAll: jest.fn(),
        update: jest.fn(),
        clearMemory: jest.fn(),
        clearFromStorage: jest.fn().mockResolvedValue(undefined),
        getFromStorage: jest.fn().mockResolvedValue(null),
        setToStorage: jest.fn().mockResolvedValue(true),
        addSetToStorageHook: jest.fn()
    }
}));

describe('onMessageExternalListener', () => {
    let mockSendResponse;

    beforeEach(() => {
        mockSendResponse = jest.fn();
        jest.clearAllMocks();
    });

    test('should allow requests from malwarebytes.com', () => {
        const sender = { url: 'https://myaccount-stage.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_GET_BASE_DATA_REQUEST, data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.baseDataAggregationHandler).toHaveBeenCalledWith(mockSendResponse);
        expect(mockSendResponse).not.toHaveBeenCalledWith(expect.objectContaining({ error: expect.any(String) }));
    });

    test('should reject requests from other domains', () => {
        const sender = { url: 'https://myaccount-stage.malwareNotBytes.com', origin: 'https://www.malwareNotBytes.com' };
        const request: ExternalMessage = { type: MSG_MA_GET_BASE_DATA_REQUEST, data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.baseDataAggregationHandler).not.toHaveBeenCalled();
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "MSG_MA_GET_BASE_DATA_RESPONSE",
            success: false,
            error: 'Error processing external message: Unregistered domain: malwarenotbytes.com'
        });
        expect(Sentry.captureException).toHaveBeenCalled();
    });

    test('should handle invalid request type', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: any = { type: 'INVALID_TYPE', data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.baseDataAggregationHandler).not.toHaveBeenCalled();
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "UNKNOWN_RESPONSE",
            success: false,
            error: 'Error processing external message: Invalid request: Missing type'
        });
        expect(Sentry.captureException).toHaveBeenCalled();
    });

    test('should handle unknown message type', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: 'UNKNOWN_MESSAGE_TYPE' as any, data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.baseDataAggregationHandler).not.toHaveBeenCalled();
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "UNKNOWN_RESPONSE",
            success: false,
            error: 'Error processing external message: Invalid request: Missing type'
        });
        expect(Sentry.captureException).toHaveBeenCalled();
    });
    
    test('should call baseDataAggregationHandler for MSG_MA_GET_BASE_DATA_REQUEST', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_GET_BASE_DATA_REQUEST, data: {} };
        const result = onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.baseDataAggregationHandler).toHaveBeenCalledWith(mockSendResponse);
        expect(result).toBe(true);
    });

    test('should capture exception and send error response on general error', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_GET_BASE_DATA_REQUEST, data: {} };
        (handlers.baseDataAggregationHandler as jest.Mock).mockImplementation(() => {
            throw new Error('Handler error');
        });
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(Sentry.captureException).toHaveBeenCalledWith(expect.objectContaining({
            message: 'Error processing external message: Handler error',
        }));
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "MSG_MA_GET_BASE_DATA_RESPONSE",
            success: false,
            error: 'Error processing external message: Handler error'
        });
    });

    test('should call enableAllProtectionsHandler for MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, data: {} };
        const result = onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.enableAllProtectionsHandler).toHaveBeenCalledWith(mockSendResponse);
        expect(result).toBe(true);
    });

    test('should allow MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST requests from malwarebytes.com', () => {
        const sender = { url: 'https://myaccount-stage.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.enableAllProtectionsHandler).toHaveBeenCalledWith(mockSendResponse);
        expect(mockSendResponse).not.toHaveBeenCalledWith(expect.objectContaining({ error: expect.any(String) }));
    });

    test('should reject MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST requests from other domains', () => {
        const sender = { url: 'https://myaccount-stage.malwareNotBytes.com', origin: 'https://www.malwareNotBytes.com' };
        const request: ExternalMessage = { type: MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, data: {} };
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(handlers.enableAllProtectionsHandler).not.toHaveBeenCalled();
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE",
            success: false,
            error: 'Error processing external message: Unregistered domain: malwarenotbytes.com'
        });
        expect(Sentry.captureException).toHaveBeenCalled();
    });

    test('should handle error in enableAllProtectionsHandler', () => {
        const sender = { url: 'https://myaccount.malwarebytes.com', origin: 'https://www.malwarebytes.com' };
        const request: ExternalMessage = { type: MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, data: {} };
        (handlers.enableAllProtectionsHandler as jest.Mock).mockImplementation(() => {
            throw new Error('Enable all protections error');
        });
        onMessageExternalListener(request, sender, mockSendResponse);
        expect(Sentry.captureException).toHaveBeenCalledWith(expect.objectContaining({
            message: 'Error processing external message: Enable all protections error',
        }));
        expect(mockSendResponse).toHaveBeenCalledWith({
            type: "MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE",
            success: false,
            error: 'Error processing external message: Enable all protections error'
        });
    });
});

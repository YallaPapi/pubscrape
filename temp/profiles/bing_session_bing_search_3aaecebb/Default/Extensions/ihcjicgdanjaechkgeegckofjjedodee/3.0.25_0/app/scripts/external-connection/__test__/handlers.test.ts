import { baseDataAggregationHandler, enableAllProtectionsHandler } from '../handlers';
import { filterEnableSettingsProps, turnOnKillSwitch, turnOnAllIndividualProtections, refreshPage } from '../helpers';
import { simpleStorageGet } from '@/utils/storage';
import { chrome } from '@/utils/polyfill';
import { 
    BaseDataResponse, 
    AllTypesDetection, 
    MESSAGE_TYPES, 
    ToMyAccountResponse,
    MSG_MA_GET_BASE_DATA_RESPONSE,
    MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE
} from '../types';

// mock settings
jest.mock('@/app/scripts/settings', () => {
    const mockSettings = {
        enableProtection: true,
        enableProtectionAds: true,
        enableProtectionGtld: false,
        enableProtectionMalware: true,
        enableProtectionScams: true,
        enableNativeMessaging: null,
        enableVerboseLogging: false,
        enableMonthlyNotification: true,
        enableMaliciousNotification: true,
        enableBreachNotification: true,
        enableBlockCountDisplay: true,
        enableBlockYoutubeCustomAds: true,
        enableSkimmerProtection: true,
        enableVisualDebugging: false,
        enablePingTrackerRemover: true,
        sendTelemetry: null,

        // Mock methods
        get: jest.fn((key) => mockSettings[key]),
        set: jest.fn((key, value) => { mockSettings[key] = value; }),
        setAll: jest.fn((settings) => Object.assign(mockSettings, settings)),
        update: jest.fn((settings) => Object.assign(mockSettings, settings)),
        clearMemory: jest.fn(),
        clearFromStorage: jest.fn().mockResolvedValue(undefined),
        getFromStorage: jest.fn().mockResolvedValue(null),
        setToStorage: jest.fn().mockResolvedValue(true),
        addSetToStorageHook: jest.fn()
    };

    return {
        Settings: jest.fn().mockImplementation(() => mockSettings),
        settings: mockSettings
    };
});

jest.mock('@/utils/storage');
jest.mock('@/utils/polyfill', () => ({
    chrome: {
        runtime: {
            getManifest: jest.fn(() => ({ version: '3.0.21' })),
        },
    },
}));

// Mock helpers
jest.mock('../helpers', () => ({
    ...jest.requireActual('../helpers'),
    turnOnKillSwitch: jest.fn(),
    turnOnAllIndividualProtections: jest.fn(),
    refreshPage: jest.fn(),
}));

const { settings } = require("@/app/scripts/settings");

describe('baseDataAggregationHandler', () => {
    let mockCallback: jest.Mock;
    const mockSettingsInstance = filterEnableSettingsProps(settings);
    const mockVersion = '3.0.21';
    const mockRawData: Record<string, AllTypesDetection> = {
        '2023-10-01': { ads: 1, malwares: 2, scams: 0, content: 5, silentAds: 1, silentContent: 2, silentMalwares: 3, silentScams: 4, ts: 12345 },
        '2023-10-02': { ads: 3, malwares: 0, scams: 1, content: 2, silentAds: 4, silentContent: 3, silentMalwares: 2, silentScams: 1, ts: 12346 },
    };

    // This is what the actual transformDetectionData should produce based on the mockRawData above
    const expectedTransformedData = {
        ads: [{ date: '2023-10-01', count: 1 }, { date: '2023-10-02', count: 3 }],
        malwares: [{ date: '2023-10-01', count: 2 }, { date: '2023-10-02', count: 0 }],
        scams: [{ date: '2023-10-01', count: 0 }, { date: '2023-10-02', count: 1 }],
        content: [{ date: '2023-10-01', count: 5 }, { date: '2023-10-02', count: 2 }],
        silentAds: [{ date: '2023-10-01', count: 1 }, { date: '2023-10-02', count: 4 }],
        silentContent: [{ date: '2023-10-01', count: 2 }, { date: '2023-10-02', count: 3 }],
        silentMalwares: [{ date: '2023-10-01', count: 3 }, { date: '2023-10-02', count: 2 }],
        silentScams: [{ date: '2023-10-01', count: 4 }, { date: '2023-10-02', count: 1 }],
    };

    beforeEach(() => {
        mockCallback = jest.fn();
        (simpleStorageGet as jest.Mock).mockResolvedValue(mockRawData);
        (chrome.runtime.getManifest as jest.Mock).mockReturnValue({ version: mockVersion });
    });

    test('should call callback with aggregated data using actual transformDetectionData', async () => {
        await baseDataAggregationHandler(mockCallback);

        expect(simpleStorageGet).toHaveBeenCalledWith('records');
        expect(chrome.runtime.getManifest).toHaveBeenCalledTimes(1);

        const expectedData: BaseDataResponse = {
            version: mockVersion,
            settings: mockSettingsInstance,
            detectionSummary: expectedTransformedData,
            supportedMessageTypes: Array.from(MESSAGE_TYPES),
        };

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_GET_BASE_DATA_RESPONSE,
            success: true,
            data: expectedData
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });

    test('should handle empty rawData from storage using actual transformDetectionData', async () => {
        (simpleStorageGet as jest.Mock).mockResolvedValue(null); // Simulate no data in storage

        // The actual transformDetectionData will return an empty object for null input
        const emptyTransformedData = {};

        await baseDataAggregationHandler(mockCallback);

        const expectedData: BaseDataResponse = {
            version: mockVersion,
            settings: mockSettingsInstance,
            detectionSummary: emptyTransformedData,
            supportedMessageTypes: Array.from(MESSAGE_TYPES),
        };

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_GET_BASE_DATA_RESPONSE,
            success: true,
            data: expectedData
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });

    test('should handle undefined rawData from storage using actual transformDetectionData', async () => {
        (simpleStorageGet as jest.Mock).mockResolvedValue(undefined); // Simulate undefined data in storage

        const emptyTransformedData = {}; // Expecting empty object for undefined input as well

        await baseDataAggregationHandler(mockCallback);

        const expectedData: BaseDataResponse = {
            version: mockVersion,
            settings: mockSettingsInstance,
            detectionSummary: emptyTransformedData,
            supportedMessageTypes: Array.from(MESSAGE_TYPES),
        };

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_GET_BASE_DATA_RESPONSE,
            success: true,
            data: expectedData
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });

    test('should handle rawData with missing AllTypesDetection properties using actual transformDetectionData', async () => {
        const partialMockRawData: Record<string, Partial<AllTypesDetection>> = {
            '2023-10-03': { ads: 5, ts: 12347 }, // Missing other properties
        };
        (simpleStorageGet as jest.Mock).mockResolvedValue(partialMockRawData as Record<string, AllTypesDetection>); 

        const expectedPartialTransformedData = {
            ads: [{ date: '2023-10-03', count: 5 }],
        };

        await baseDataAggregationHandler(mockCallback);

        const expectedData: BaseDataResponse = {
            version: mockVersion,
            settings: mockSettingsInstance,
            detectionSummary: expectedPartialTransformedData,
            supportedMessageTypes: Array.from(MESSAGE_TYPES),
        };

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_GET_BASE_DATA_RESPONSE,
            success: true,
            data: expectedData
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });
});

describe('enableAllProtectionsHandler', () => {
    let mockCallback: jest.Mock;

    beforeEach(() => {
        mockCallback = jest.fn();
        jest.clearAllMocks();
    });

    test('should successfully enable all protections and call callback with success', async () => {
        (turnOnKillSwitch as jest.Mock).mockResolvedValue(undefined);
        (turnOnAllIndividualProtections as jest.Mock).mockResolvedValue(undefined);
        (refreshPage as jest.Mock).mockImplementation(() => {});

        await enableAllProtectionsHandler(mockCallback);

        expect(turnOnKillSwitch).toHaveBeenCalledTimes(1);
        expect(turnOnAllIndividualProtections).toHaveBeenCalledTimes(1);
        expect(refreshPage).toHaveBeenCalledTimes(1);

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE,
            success: true
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });

    test('should call functions in the correct order', async () => {
        const callOrder: string[] = [];
        
        (turnOnKillSwitch as jest.Mock).mockImplementation(async () => {
            callOrder.push('killSwitch');
        });
        (turnOnAllIndividualProtections as jest.Mock).mockImplementation(async () => {
            callOrder.push('individualProtections');
        });
        (refreshPage as jest.Mock).mockImplementation(() => {
            callOrder.push('refreshPage');
        });

        await enableAllProtectionsHandler(mockCallback);

        expect(callOrder).toEqual(['killSwitch', 'individualProtections', 'refreshPage']);

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE,
            success: true
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });

    test('should handle error when turnOnKillSwitch fails', async () => {
        const error = new Error('Kill switch error');
        (turnOnKillSwitch as jest.Mock).mockRejectedValue(error);

        await expect(enableAllProtectionsHandler(mockCallback)).rejects.toThrow('Kill switch error');
        
        expect(turnOnKillSwitch).toHaveBeenCalledTimes(1);
        expect(turnOnAllIndividualProtections).not.toHaveBeenCalled();
        expect(refreshPage).not.toHaveBeenCalled();
        expect(mockCallback).not.toHaveBeenCalled();
    });

    test('should handle error when turnOnAllIndividualProtections fails', async () => {
        const error = new Error('Individual protections error');
        (turnOnKillSwitch as jest.Mock).mockResolvedValue(undefined);
        (turnOnAllIndividualProtections as jest.Mock).mockRejectedValue(error);

        await expect(enableAllProtectionsHandler(mockCallback)).rejects.toThrow('Individual protections error');
        
        expect(turnOnKillSwitch).toHaveBeenCalledTimes(1);
        expect(turnOnAllIndividualProtections).toHaveBeenCalledTimes(1);
        expect(refreshPage).not.toHaveBeenCalled();
        expect(mockCallback).not.toHaveBeenCalled();
    });

    test('should handle error when refreshPage throws an error', async () => {
        (turnOnKillSwitch as jest.Mock).mockResolvedValue(undefined);
        (turnOnAllIndividualProtections as jest.Mock).mockResolvedValue(undefined);
        (refreshPage as jest.Mock).mockImplementation(() => {
            throw new Error('Refresh page error');
        });

        // The handler should fail if refreshPage throws an error
        await expect(enableAllProtectionsHandler(mockCallback)).rejects.toThrow('Refresh page error');

        expect(turnOnKillSwitch).toHaveBeenCalledTimes(1);
        expect(turnOnAllIndividualProtections).toHaveBeenCalledTimes(1);
        expect(refreshPage).toHaveBeenCalledTimes(1);
        expect(mockCallback).not.toHaveBeenCalled();
    });

    test('should call callback exactly once', async () => {
        (turnOnKillSwitch as jest.Mock).mockResolvedValue(undefined);
        (turnOnAllIndividualProtections as jest.Mock).mockResolvedValue(undefined);
        (refreshPage as jest.Mock).mockImplementation(() => {});

        await enableAllProtectionsHandler(mockCallback);

        expect(mockCallback).toHaveBeenCalledTimes(1);

        const expectedResponse: ToMyAccountResponse = {
            type: MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE,
            success: true
        };

        expect(mockCallback).toHaveBeenCalledWith(expectedResponse);
    });
});

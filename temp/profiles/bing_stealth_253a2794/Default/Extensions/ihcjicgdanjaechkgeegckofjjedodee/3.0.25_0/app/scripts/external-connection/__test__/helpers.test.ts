import {
    turnOnKillSwitch,
    turnOnAllIndividualProtections,
    refreshPage,
    isMyAccountMessageType,
    filterEnableSettingsProps,
    transformDetectionData
} from '../helpers';
import { MSG_MA_GET_BASE_DATA_REQUEST, MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST, AllTypesDetection } from '../types';
import { chrome } from '@/utils/polyfill';
import { settings } from '@/app/scripts/settings';
import {
    SETTING_KILLSWITCH,
    SETTING_SCAMS,
    SETTING_MALWARE,
    SETTING_ADS,
} from '@/app/scripts/app-consts.js';
import { toggleAllEnabledRulesets, toggleEnabledRuleset } from '@/app/scripts/mv3/ruleset-utils.js';

// Mock dependencies
jest.mock('@/utils/polyfill', () => ({
    chrome: {
        tabs: {
            query: jest.fn(),
            reload: jest.fn(),
        },
        runtime: {
            lastError: null,
        },
    },
}));

jest.mock('@/app/scripts/settings', () => ({
    settings: {
        setToStorage: jest.fn(),
    },
}));

jest.mock('@/app/scripts/mv3/ruleset-utils.js', () => ({
    toggleAllEnabledRulesets: jest.fn(),
    toggleEnabledRuleset: jest.fn(),
}));

describe('Helper Functions', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (chrome.runtime as any).lastError = null;
    });

    describe('isMyAccountMessageType', () => {
        test('should return true for valid message types', () => {
            expect(isMyAccountMessageType(MSG_MA_GET_BASE_DATA_REQUEST)).toBe(true);
            expect(isMyAccountMessageType(MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST)).toBe(true);
        });

        test('should return false for invalid message types', () => {
            expect(isMyAccountMessageType('INVALID_TYPE')).toBe(false);
            expect(isMyAccountMessageType('')).toBe(false);
            expect(isMyAccountMessageType('UNKNOWN_MESSAGE')).toBe(false);
        });

        test('should handle non-string values', () => {
            expect(isMyAccountMessageType(null as any)).toBe(false);
            expect(isMyAccountMessageType(undefined as any)).toBe(false);
            expect(isMyAccountMessageType(123 as any)).toBe(false);
            expect(isMyAccountMessageType({} as any)).toBe(false);
        });
    });

    describe('filterEnableSettingsProps', () => {
        test('should filter properties that start with "enable"', () => {
            const mockSettings = {
                enableProtection: true,
                enableProtectionAds: false,
                enableProtectionMalware: true,
                someOtherSetting: 'value',
                anotherProperty: 123,
                enableDebug: false,
            };

            const result = filterEnableSettingsProps(mockSettings);

            expect(result).toEqual({
                enableProtection: true,
                enableProtectionAds: false,
                enableProtectionMalware: true,
                enableDebug: false,
            });
            expect(result).not.toHaveProperty('someOtherSetting');
            expect(result).not.toHaveProperty('anotherProperty');
        });

        test('should return empty object when no enable properties exist', () => {
            const mockSettings = {
                someProperty: 'value',
                anotherProperty: 123,
                thirdProperty: false,
            };

            const result = filterEnableSettingsProps(mockSettings);

            expect(result).toEqual({});
        });

        test('should handle empty object', () => {
            const result = filterEnableSettingsProps({});
            expect(result).toEqual({});
        });
    });

    describe('transformDetectionData', () => {
        test('should transform detection data correctly', () => {
            const mockData: Record<string, AllTypesDetection> = {
                '2023-10-01': { ads: 1, malwares: 2, scams: 0, content: 5, silentAds: 1, silentContent: 2, silentMalwares: 3, silentScams: 4, ts: 12345 },
                '2023-10-02': { ads: 3, malwares: 0, scams: 1, content: 2, silentAds: 4, silentContent: 3, silentMalwares: 2, silentScams: 1, ts: 12346 },
            };

            const result = transformDetectionData(mockData);

            expect(result).toEqual({
                ads: [{ date: '2023-10-01', count: 1 }, { date: '2023-10-02', count: 3 }],
                malwares: [{ date: '2023-10-01', count: 2 }, { date: '2023-10-02', count: 0 }],
                scams: [{ date: '2023-10-01', count: 0 }, { date: '2023-10-02', count: 1 }],
                content: [{ date: '2023-10-01', count: 5 }, { date: '2023-10-02', count: 2 }],
                silentAds: [{ date: '2023-10-01', count: 1 }, { date: '2023-10-02', count: 4 }],
                silentContent: [{ date: '2023-10-01', count: 2 }, { date: '2023-10-02', count: 3 }],
                silentMalwares: [{ date: '2023-10-01', count: 3 }, { date: '2023-10-02', count: 2 }],
                silentScams: [{ date: '2023-10-01', count: 4 }, { date: '2023-10-02', count: 1 }],
            });
        });

        test('should return empty object for null input', () => {
            const result = transformDetectionData(null as any);
            expect(result).toEqual({});
        });

        test('should return empty object for undefined input', () => {
            const result = transformDetectionData(undefined as any);
            expect(result).toEqual({});
        });

        test('should handle empty data object', () => {
            const result = transformDetectionData({});
            expect(result).toEqual({});
        });

        test('should exclude ts property from transformation', () => {
            const mockData: Record<string, AllTypesDetection> = {
                '2023-10-01': { ads: 1, malwares: 2, scams: 0, content: 5, silentAds: 1, silentContent: 2, silentMalwares: 3, silentScams: 4, ts: 12345 },
            };

            const result = transformDetectionData(mockData);

            expect(result).not.toHaveProperty('ts');
        });
    });

    describe('turnOnKillSwitch', () => {
        test('should call toggleAllEnabledRulesets and settings.setToStorage', async () => {
            (toggleAllEnabledRulesets as jest.Mock).mockResolvedValue(undefined);
            (settings.setToStorage as jest.Mock).mockResolvedValue(undefined);

            await turnOnKillSwitch();

            expect(toggleAllEnabledRulesets).toHaveBeenCalledWith(true);
            expect(settings.setToStorage).toHaveBeenCalledWith({ [SETTING_KILLSWITCH]: true });
        });

        test('should handle errors from toggleAllEnabledRulesets', async () => {
            const error = new Error('Ruleset error');
            (toggleAllEnabledRulesets as jest.Mock).mockRejectedValue(error);

            await expect(turnOnKillSwitch()).rejects.toThrow('Ruleset error');
            expect(settings.setToStorage).not.toHaveBeenCalled();
        });

        test('should handle errors from settings.setToStorage', async () => {
            const error = new Error('Storage error');
            (toggleAllEnabledRulesets as jest.Mock).mockResolvedValue(undefined);
            (settings.setToStorage as jest.Mock).mockRejectedValue(error);

            await expect(turnOnKillSwitch()).rejects.toThrow('Storage error');
            expect(toggleAllEnabledRulesets).toHaveBeenCalledWith(true);
        });
    });

    describe('turnOnAllIndividualProtections', () => {
        test('should enable all individual protections', async () => {
            (toggleEnabledRuleset as jest.Mock).mockResolvedValue(undefined);
            (settings.setToStorage as jest.Mock).mockResolvedValue(undefined);

            await turnOnAllIndividualProtections();

            expect(toggleEnabledRuleset).toHaveBeenCalledTimes(3);
            expect(toggleEnabledRuleset).toHaveBeenCalledWith(SETTING_SCAMS, true);
            expect(toggleEnabledRuleset).toHaveBeenCalledWith(SETTING_MALWARE, true);
            expect(toggleEnabledRuleset).toHaveBeenCalledWith(SETTING_ADS, true);

            expect(settings.setToStorage).toHaveBeenCalledTimes(3);
            expect(settings.setToStorage).toHaveBeenCalledWith({ [SETTING_SCAMS]: true });
            expect(settings.setToStorage).toHaveBeenCalledWith({ [SETTING_MALWARE]: true });
            expect(settings.setToStorage).toHaveBeenCalledWith({ [SETTING_ADS]: true });
        });

        test('should handle errors from toggleEnabledRuleset', async () => {
            const error = new Error('Toggle ruleset error');
            (toggleEnabledRuleset as jest.Mock).mockRejectedValue(error);

            await expect(turnOnAllIndividualProtections()).rejects.toThrow('Toggle ruleset error');
        });

        test('should handle errors from settings.setToStorage', async () => {
            const error = new Error('Storage error');
            (toggleEnabledRuleset as jest.Mock).mockResolvedValue(undefined);
            (settings.setToStorage as jest.Mock).mockRejectedValue(error);

            await expect(turnOnAllIndividualProtections()).rejects.toThrow('Storage error');
        });
    });

    describe('refreshPage', () => {
        test('should reload the active tab successfully', () => {
            const mockTab = { id: 123 };
            (chrome.tabs.query as jest.Mock).mockImplementation((query, callback) => {
                callback([mockTab]);
            });
            (chrome.tabs.reload as jest.Mock).mockImplementation((tabId, options, callback) => {
                callback();
            });

            refreshPage();

            expect(chrome.tabs.query).toHaveBeenCalledWith({ active: true, currentWindow: true }, expect.any(Function));
            expect(chrome.tabs.reload).toHaveBeenCalledWith(123, { bypassCache: true }, expect.any(Function));
        });

        test('should handle case when no tabs are found', () => {
            (chrome.tabs.query as jest.Mock).mockImplementation((query, callback) => {
                callback([]);
            });

            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

            refreshPage();

            expect(chrome.tabs.query).toHaveBeenCalledWith({ active: true, currentWindow: true }, expect.any(Function));
            expect(chrome.tabs.reload).not.toHaveBeenCalled();
            expect(consoleSpy).toHaveBeenCalledWith('BG_CLD: No active tab found to reload');

            consoleSpy.mockRestore();
        });

        test('should handle case when active tab has no valid id', () => {
            const mockTab = { id: undefined };
            (chrome.tabs.query as jest.Mock).mockImplementation((query, callback) => {
                callback([mockTab]);
            });

            const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

            refreshPage();

            expect(chrome.tabs.query).toHaveBeenCalledWith({ active: true, currentWindow: true }, expect.any(Function));
            expect(chrome.tabs.reload).not.toHaveBeenCalled();
            expect(consoleSpy).toHaveBeenCalledWith('BG_CLD: Active tab does not have a valid id');

            consoleSpy.mockRestore();
        });

        test('should handle reload error', () => {
            const mockTab = { id: 123 };
            (chrome.tabs.query as jest.Mock).mockImplementation((query, callback) => {
                callback([mockTab]);
            });
            (chrome.tabs.reload as jest.Mock).mockImplementation((tabId, options, callback) => {
                (chrome.runtime as any).lastError = { message: 'Reload failed' };
                callback();
            });

            const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

            refreshPage();

            expect(chrome.tabs.reload).toHaveBeenCalledWith(123, { bypassCache: true }, expect.any(Function));
            expect(consoleSpy).toHaveBeenCalledWith('BG_CLD: Error reloading tab:', 'Reload failed');

            consoleSpy.mockRestore();
        });

        test('should log success when reload completes without error', () => {
            const mockTab = { id: 123 };
            (chrome.tabs.query as jest.Mock).mockImplementation((query, callback) => {
                callback([mockTab]);
            });
            (chrome.tabs.reload as jest.Mock).mockImplementation((tabId, options, callback) => {
                (chrome.runtime as any).lastError = null;
                callback();
            });

            const consoleSpy = jest.spyOn(console, 'debug').mockImplementation();

            refreshPage();

            expect(chrome.tabs.reload).toHaveBeenCalledWith(123, { bypassCache: true }, expect.any(Function));
            expect(consoleSpy).toHaveBeenCalledWith('BG_CLD: Tab reloaded successfully');

            consoleSpy.mockRestore();
        });
    });
});

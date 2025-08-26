import { MessageType, MESSAGE_TYPES, AllTypesDetection, DetectionTypeRecord } from './types';
import { chrome } from '@/utils/polyfill';
import { settings } from '@/app/scripts/settings';
import {
    SETTING_KILLSWITCH,
    SETTING_SCAMS,
    SETTING_MALWARE,
    SETTING_ADS,
} from '@/app/scripts/app-consts.js';
import { toggleAllEnabledRulesets, toggleEnabledRuleset } from '@/app/scripts/mv3/ruleset-utils.js'

export function isMyAccountMessageType(value: string): value is MessageType {
    return typeof value === "string" && (MESSAGE_TYPES as readonly string[]).includes(value);
}

export const filterEnableSettingsProps = <T extends Record<string, any>>(obj: T): Partial<T> => {
  const result: Partial<T> = {};

  for (const key in obj) {
    if (key.startsWith('enable')) {
      result[key] = obj[key];
    }
  }

  return result;
}


export const transformDetectionData = (input: Record<string, AllTypesDetection>): Record<string, DetectionTypeRecord> => {
    if (!input) {
        return {};
    }
    const result: Record<string, DetectionTypeRecord> = {};

    for (const [date, data] of Object.entries(input)) {
        for (const [key, value] of Object.entries(data)) {
            if (key === "ts") continue;
            if (!result[key]) {
                result[key] = [];
            }
            result[key].push({
                date,
                count: value,
            });
        }
    }

    return result;
}

export const turnOnKillSwitch = async (): Promise<void> => {

    await toggleAllEnabledRulesets(true);

    // await settingsSetAsync({ [SETTING_KILLSWITCH]: true });
    await settings.setToStorage({ [SETTING_KILLSWITCH]: true });

};

export const turnOnAllIndividualProtections = async (): Promise<void> => {

    const allProtections = [SETTING_SCAMS, SETTING_MALWARE, SETTING_ADS];

    await Promise.all(
        allProtections.map(async (setting) => {
            await toggleEnabledRuleset(setting, true);
            await settings.setToStorage({ [setting]: true });
        })
    );
}

export const refreshPage = (): void => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs.length > 0) {
            const activeTab = tabs[0];
            if (typeof activeTab.id === 'number') {
                chrome.tabs.reload(activeTab.id, { bypassCache: true }, () => {
                    if (chrome.runtime.lastError) {
                        console.error('BG_CLD: Error reloading tab:', chrome.runtime.lastError.message);
                    } else {
                        console.debug('BG_CLD: Tab reloaded successfully');
                    }
                });
            } else {
                console.warn('BG_CLD: Active tab does not have a valid id');
            }
        } else {
            console.warn('BG_CLD: No active tab found to reload');
        }
    });
}

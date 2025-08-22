
import {
    MESSAGE_TYPES,
    AllTypesDetection,
    BaseDataResponse,
    ToMyAccountResponse,
    MSG_MA_GET_BASE_DATA_RESPONSE,
    MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE
} from './types';
import { chrome } from '@/utils/polyfill';
import { settings } from '@/app/scripts/settings';
import { simpleStorageGet }from '@/utils/storage'
import {
    transformDetectionData,
    filterEnableSettingsProps,
    turnOnKillSwitch,
    turnOnAllIndividualProtections,
    refreshPage
} from './helpers';

export const baseDataAggregationHandler = async (callback: (response?: ToMyAccountResponse) => unknown): Promise<void> => {

    const settingsObj = filterEnableSettingsProps(settings);
    const version = chrome.runtime.getManifest().version;
    const rawData = await simpleStorageGet('records');
    const detectionSummary = transformDetectionData(rawData as Record<string, AllTypesDetection>);

    const data : BaseDataResponse = {
        version,
        settings: settingsObj,
        detectionSummary,
        supportedMessageTypes: Array.from(MESSAGE_TYPES)
    };

    console.log('BG_CLD: message request', data);

    callback({
        type: MSG_MA_GET_BASE_DATA_RESPONSE,
        success: true,
        data
    });
}

export const enableAllProtectionsHandler = async (callback: (response?: ToMyAccountResponse) => unknown): Promise<void> => {

    // #1 Turn on the killswitch
    await turnOnKillSwitch();
    console.debug('BG_CLD: Kill switch turned on');

    // #2 Turn on all protections
    await turnOnAllIndividualProtections();
    console.debug('BG_CLD: All individual protections turned on');

    // #3 Refresh the page
    refreshPage();
    console.debug('BG_CLD: Page refreshed');

    console.debug('BG_CLD: All protections enabled successfully');

    callback({
        type: MSG_MA_ENABLE_ALL_PROTECTIONS_RESPONSE,
        success: true
    });  
}

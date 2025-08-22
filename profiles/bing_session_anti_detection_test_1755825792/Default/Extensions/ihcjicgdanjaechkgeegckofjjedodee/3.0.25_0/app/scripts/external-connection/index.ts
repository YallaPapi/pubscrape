import { domain } from '@/utils/utils';
import * as Sentry from '@sentry/browser';
import { chrome } from '@/utils/polyfill';
import {
    ExternalMessage,
    MSG_MA_GET_BASE_DATA_REQUEST,
    MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST,
    ToMyAccountResponse,
    RESPONSE_TYPES,
    MB_MY_ACCOUNT_DOMAIN
} from './types';
import { isMyAccountMessageType } from './helpers';
import {
    baseDataAggregationHandler,
    enableAllProtectionsHandler
} from './handlers';

/**
 * Listener for external messages.
 * 
 * @param request - The message sent from the external source.
 * @param sender - The sender of the message.
 * @param sendResponse - A function to send a response back to the sender.
 */
export const onMessageExternalListener = (
    request: ExternalMessage,
    sender: chrome.runtime.MessageSender,
    sendResponse: (response?: ToMyAccountResponse) => unknown
): boolean | void => {

    try {

        const senderURL = domain(sender.url || sender.origin || '');

        if (senderURL !== domain(MB_MY_ACCOUNT_DOMAIN) ) { // to filter out other domains
            throw new Error(`Unregistered domain: ${senderURL}`);
        }

        if (!request || !request.type || !isMyAccountMessageType(request.type)) {
            throw new Error('Invalid request: Missing type');
        }

        switch (request.type) {
            case MSG_MA_GET_BASE_DATA_REQUEST:
                baseDataAggregationHandler(sendResponse);
                return true;
            case MSG_MA_ENABLE_ALL_PROTECTIONS_REQUEST:
                enableAllProtectionsHandler(sendResponse);
                return true;
            default:
                throw new Error(`Unknown message type: ${request.type}`);
        }


    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        const message = `Error processing external message: ${errorMsg}`;
        console.warn(errorMsg);
        Sentry.captureException({
            message,
            logentry: {
                message,
                params: [JSON.stringify(request), JSON.stringify(sender)],
            },
            level: 'warning',
            tags: {
                custom: true,
                'bg-source': 'externally_connectable',
                version: chrome.runtime.getManifest().version,
            }
        });
        sendResponse({
            type: RESPONSE_TYPES[request?.type] || "UNKNOWN_RESPONSE",
            success: false,
            error: message
        });
        return;
    }
};

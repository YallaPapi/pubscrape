import { DudeClient } from "./dude";
import { chrome } from '@/utils/polyfill';
import { simpleStorageGet } from "./storage";
import { fetchJSON } from "./utils";

jest.mock('@/utils/polyfill');
jest.mock('@/utils/storage');
jest.mock('@/utils/utils');

describe('DudeClient Tests', () => {
    beforeEach(() => {
        jest.clearAllMocks();

        (simpleStorageGet as jest.Mock).mockImplementation((keys) => {
            if (keys === 'machineId') {
                return Promise.resolve('1234567890');
            }
            return Promise.resolve(undefined);
        });
        (chrome.runtime.getManifest as jest.Mock).mockReturnValue({ version: '3.0.12' });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    
    describe('Test getBaseUrl', () => {
        it('should return the correct base URL for prod', async () => {
            const client = new DudeClient(true);
            expect((await client.getBaseUrl())).toBe('https://mbgc-c-3-0-12.v2.tel.malwarebytes.com');
        });
    
        it('should return the correct base URL for staging', async () => {        
            const client = new DudeClient(false);
            expect(await client.getBaseUrl()).toBe('https://mbgc-c-3-0-12.v2.tel.mwbsys-stage.com');
        });
     
    });

    describe('Test getMachineId', () => {
        it('should return the correct machine ID if it exists in storage', async () => {        
            const client = new DudeClient(true);
            // wait for a second
            await new Promise(resolve => setTimeout(resolve, 1000));
            expect(await client.getMachineId()).toBe('1234567890');
        });
    
        it('should return undefined if machine ID does not exist in storage', async () => {                
            (simpleStorageGet as jest.Mock).mockImplementation((_keys) => {
                return Promise.resolve(undefined);
            });
            const client = new DudeClient(true);
            await new Promise(resolve => setTimeout(resolve, 1000));
            expect(await client.getMachineId()).toBe(undefined);
        });        
    });

    describe('Test trackDailyStats', () => {
        beforeEach(() => {
            (fetchJSON as jest.Mock).mockResolvedValue({});
        });

        it('should return false if the machine ID is not found', async () => {
            (simpleStorageGet as jest.Mock).mockImplementation((_keys) => {
                return Promise.resolve(undefined);
            });
            const client = new DudeClient(true);
            expect(await client.trackDailyStats(10, 1, 2)).toBe(false);
            expect(simpleStorageGet).toHaveBeenCalledWith('machineId');
        });

        it('should return true if the machine ID is found but the stats are throttled', async () => {
            (simpleStorageGet as jest.Mock).mockImplementation((_keys) => {
                if (_keys === 'machineId') {
                    return Promise.resolve('1234567890');
                } else if (_keys === 'dudeThrottle') {
                    return Promise.resolve({
                        stats: {
                            // set to a time in the future to simulate that the stats were sent recently
                            lastSendTime: Date.now() + (1000 * 60 * 60 * 24 * 7 + 1),
                        }
                    });
                }
                return Promise.resolve(undefined);
            });

            const client = new DudeClient(true);
            const skipThrottle = true;
            expect(await client.trackDailyStats(10, 1, 2, skipThrottle)).toBe(true);
        });

        it('should return true if the stats are not throttled', async () => {
            (simpleStorageGet as jest.Mock).mockImplementation((_keys) => {
                if (_keys === 'machineId') {
                    return Promise.resolve('1234567890');
                } else if (_keys === 'dudeThrottle') {
                    return Promise.resolve({
                        stats: {
                            // set to a time to 2 days from now to simulate that the stats were not sent recently
                            lastSendTime: Date.now() + (1000 * 60 * 60 * 48 - 1),
                        }
                    });
                }
                return Promise.resolve(undefined);
            });
            const skipThrottle = true;
            const client = new DudeClient(true);
            expect(await client.trackDailyStats(10, 1, 2, skipThrottle)).toBe(true);            
        });
    });
});
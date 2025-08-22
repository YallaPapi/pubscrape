import * as dynamicRuleUtils from "../dynamic-rule-utils";
import { chrome } from "@/utils/polyfill";
import { isMV3 } from "@/utils/utils";

jest.mock("@/utils/polyfill", () => ({
    chrome: {
        declarativeNetRequest: {
            getDynamicRules: jest.fn(() => Promise.resolve([])),
            updateDynamicRules: jest.fn(() => Promise.resolve()),
            getSessionRules: jest.fn(() => Promise.resolve([])),
            getAvailableStaticRuleCount: jest.fn(() => Promise.resolve(100))
        },
        runtime: {
            lastError: null
        }
    }
}));

jest.mock("@/utils/utils", () => ({
    isMV3: jest.fn(() => true),
    urlHost: jest.fn((url) => new URL(url).hostname),
    browserName: jest.fn(() => "Chrome")
}));

describe("Dynamic Rule Utils", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    test("should return an empty array if MV3 is not enabled", async () => {
        (isMV3 as jest.Mock).mockReturnValueOnce(false);
        const result = await dynamicRuleUtils.getExistingDynamicRules();
        expect(result).toEqual([]);
    });

    test("should get existing dynamic rules", async () => {
        (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([
            { id: 1, priority: 10 },
            { id: 2, priority: 20 }
        ]);
        const result = await dynamicRuleUtils.getExistingDynamicRules();
        expect(result).toHaveLength(2);
        expect(result[0]).toEqual({ id: 1, priority: 10 });
    });

    test("should filter existing dynamic rules by priority", async () => {
        (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([
            { id: 1, priority: 10 },
            { id: 2, priority: 20 }
        ]);
        const result = await dynamicRuleUtils.getExistingDynamicRules(10);
        expect(result).toEqual([{ id: 1, priority: 10 }]);
    });

    test("should get last dynamic rule ID", async () => {
        (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([
            { id: 5 },
            { id: 10 }
        ]);
        const result = await dynamicRuleUtils.getLastDynamicRuleId();
        expect(result).toBe(10);
    });

    test("should clear all dynamic rules when MV3 is enabled", async () => {
        (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([
            { id: 1 },
            { id: 2 }
        ]);
        await dynamicRuleUtils.clearAllDynamicRules();
        expect(chrome.declarativeNetRequest.updateDynamicRules).toHaveBeenCalledWith({
            addRules: [],
            removeRuleIds: [1, 2]
        });
    });

    describe("getNextDynamicRuleId", () => {
        afterEach(() => {            
            // reset the mock
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockReset();
            dynamicRuleUtils.resetHighestAllocatedRuleId();
        });

        test("should return 2 when no existing rules", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([]);
            const result = await dynamicRuleUtils.getNextDynamicRuleId();
            expect(result).toBe(2);
        });

        test("should return next ID after last dynamic rule", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValueOnce([
                { id: 5 },
                { id: 10 }
            ]);
            const result = await dynamicRuleUtils.getNextDynamicRuleId();
            expect(result).toBe(11);
        });
        
        test("should handle when rules are saved between calls", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock)
                .mockResolvedValueOnce([{ id: 5 }])   // First call
                .mockResolvedValueOnce([{ id: 6 }]);  // Second call (first rule was saved)
            
            const result1 = await dynamicRuleUtils.getNextDynamicRuleId();
            const result2 = await dynamicRuleUtils.getNextDynamicRuleId();
            
            expect(result1).toBe(6);
            expect(result2).toBe(7); // Should still be 7
        });

        test("should prevent race conditions with simultaneous calls", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValue([{ id: 10 }]);
            
            // Make multiple simultaneous calls
            const promises = Array.from({ length: 5 }, () => dynamicRuleUtils.getNextDynamicRuleId());
            const results = await Promise.all(promises);
            
            // All results should be unique and sequential
            expect(new Set(results).size).toBe(5); // All different
            expect(Math.min(...results)).toBe(11);
            expect(Math.max(...results)).toBe(15);
            expect(results.sort((a, b) => a - b)).toEqual([11, 12, 13, 14, 15]);
        });

        test("calling multiple times without saving should not affect the next ID", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock)
                .mockResolvedValueOnce([{ id: 5 }])  // First call
                .mockResolvedValueOnce([{ id: 5 }]); // Second call (no rules saved yet)
            
            const result1 = await dynamicRuleUtils.getNextDynamicRuleId();
            const result2 = await dynamicRuleUtils.getNextDynamicRuleId();
            
            expect(result1).toBe(6);
            expect(result2).toBe(7); // Should be 7, not 6 again
        });

    });

    describe("getNextSessionRuleId", () => {
        afterEach(() => {            
            // reset the mock
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockReset();
            dynamicRuleUtils.resetHighestAllocatedRuleId();
        });

        test("should return next ID after last session rule", async () => {
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockResolvedValueOnce([
                { id: 3 },
                { id: 8 }
            ]);
            const result = await dynamicRuleUtils.getNextSessionRuleId();
            expect(result).toBe(9);
        });

        test("should return 2 when no existing session rules", async () => {
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockResolvedValueOnce([]);
            const result = await dynamicRuleUtils.getNextSessionRuleId();
            expect(result).toBe(2);
        });

        test("should maintain high-water mark across multiple calls", async () => {
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock)
                .mockResolvedValueOnce([{ id: 3 }])  // First call
                .mockResolvedValueOnce([{ id: 3 }]); // Second call (no rules saved yet)
            
            const result1 = await dynamicRuleUtils.getNextSessionRuleId();
            const result2 = await dynamicRuleUtils.getNextSessionRuleId();
            
            expect(result1).toBe(4);
            expect(result2).toBe(5); // Should be 5, not 4 again
        });

        test("should prevent race conditions with simultaneous calls", async () => {
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockResolvedValue([{ id: 20 }]);
            
            // Make multiple simultaneous calls
            const promises = Array.from({ length: 3 }, () => dynamicRuleUtils.getNextSessionRuleId());
            const results = await Promise.all(promises);
            
            // All results should be unique and sequential
            expect(new Set(results).size).toBe(3); // All different
            expect(Math.min(...results)).toBe(21);
            expect(Math.max(...results)).toBe(23);
            expect(results.sort((a, b) => a - b)).toEqual([21, 22, 23]);
        });

        test("should share high-water mark with getNextDynamicRuleId", async () => {
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValue([{ id: 5 }]);
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockResolvedValue([{ id: 3 }]);
            
            // Call getNextDynamicRuleId first
            const dynamicResult = await dynamicRuleUtils.getNextDynamicRuleId();
            expect(dynamicResult).toBe(6);
            
            // Then call getNextSessionRuleId - should continue from the high-water mark
            const sessionResult = await dynamicRuleUtils.getNextSessionRuleId();
            expect(sessionResult).toBe(7); // Should be 7, not 4
        });
        
    });

    describe("Mixed function calls", () => {
        test("should prevent race conditions between getNextDynamicRuleId and getNextSessionRuleId", async () => {
            dynamicRuleUtils.resetHighestAllocatedRuleId();
            (chrome.declarativeNetRequest.getDynamicRules as jest.Mock).mockResolvedValue([{ id: 10 }]);
            (chrome.declarativeNetRequest.getSessionRules as jest.Mock).mockResolvedValue([{ id: 8 }]);
            
            // Make mixed simultaneous calls
            const promises = [
                dynamicRuleUtils.getNextDynamicRuleId(),
                dynamicRuleUtils.getNextSessionRuleId(),
                dynamicRuleUtils.getNextDynamicRuleId(),
                dynamicRuleUtils.getNextSessionRuleId(),
            ];
            const results = await Promise.all(promises);
            
            // All results should be unique and sequential
            expect(new Set(results).size).toBe(4); // All different
            expect(Math.min(...results)).toBe(11);
            expect(Math.max(...results)).toBe(14);
            expect(results.sort((a, b) => a - b)).toEqual([11, 12, 13, 14]);
        });
    });
});

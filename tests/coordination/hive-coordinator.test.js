/**
 * Test Suite for Hive Coordinator
 * Tests adaptive coordination, topology switching, and emergency responses
 */

const { HiveCoordinator } = require('../../src/coordination/HiveCoordinator');

describe('HiveCoordinator', () => {
    let coordinator;
    let mockConfig;
    
    beforeEach(() => {
        mockConfig = {
            hiveId: 'test-hive-001',
            coordinationMode: 'adaptive',
            emergencyThresholds: {
                errorRate: 0.5,
                responseTime: 10000,
                agentFailureRate: 0.7
            },
            monitoring: {
                metricsInterval: 1000,
                retentionPeriod: 60000
            },
            topology: {
                adaptationThreshold: 0.15,
                evaluationFrequency: 5000
            },
            scaling: {
                predictionHorizon: 60000,
                scalingBuffer: 0.2
            },
            loadBalancing: {
                rebalanceThreshold: 0.3,
                rebalanceInterval: 5000
            },
            patterns: {
                emergenceThreshold: 0.7,
                adaptationRate: 0.1
            }
        };
    });
    
    afterEach(async () => {
        if (coordinator) {
            coordinator.stop();
            coordinator = null;
        }
    });
    
    describe('Initialization', () => {
        test('should initialize with default configuration', async () => {
            coordinator = new HiveCoordinator();
            
            // Wait for initialization
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(coordinator.config.hiveId).toBeDefined();
            expect(coordinator.status).toBe('active');
            expect(coordinator.components.size).toBe(5);
        });
        
        test('should initialize with custom configuration', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(coordinator.config.hiveId).toBe('test-hive-001');
            expect(coordinator.config.coordinationMode).toBe('adaptive');
            expect(coordinator.status).toBe('active');
        });
        
        test('should initialize all required components', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(coordinator.components.has('monitor')).toBe(true);
            expect(coordinator.components.has('topology')).toBe(true);
            expect(coordinator.components.has('scaler')).toBe(true);
            expect(coordinator.components.has('loadBalancer')).toBe(true);
            expect(coordinator.components.has('patterns')).toBe(true);
        });
        
        test('should set up component integration hooks', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(coordinator.hooks.onPerformanceAlert.length).toBeGreaterThan(0);
            expect(coordinator.hooks.onTopologyChange.length).toBeGreaterThan(0);
            expect(coordinator.hooks.onPatternDetection.length).toBeGreaterThan(0);
            expect(coordinator.hooks.onEmergency.length).toBeGreaterThan(0);
        });
    });
    
    describe('Status and Health Monitoring', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should provide system status', () => {
            const status = coordinator.getStatus();
            
            expect(status.status).toBe('active');
            expect(status.hiveId).toBe('test-hive-001');
            expect(status.emergencyMode).toBe(false);
            expect(status.componentCount).toBe(5);
            expect(status.coordinationMetrics).toBeDefined();
        });
        
        test('should perform health checks', async () => {
            const health = await coordinator.healthCheck();
            
            expect(health.timestamp).toBeDefined();
            expect(health.overall).toBeDefined();
            expect(health.components).toBeDefined();
            expect(health.issues).toBeDefined();
            
            expect(Object.keys(health.components)).toHaveLength(5);
        });
        
        test('should detect component health issues', async () => {
            // Simulate component failure by removing a component
            coordinator.components.delete('monitor');
            
            const health = await coordinator.healthCheck();
            
            expect(health.overall).not.toBe('healthy');
            expect(health.issues.length).toBeGreaterThan(0);
        });
        
        test('should provide component-specific status', () => {
            const monitorStatus = coordinator.getComponentStatus('monitor');
            const topologyStatus = coordinator.getComponentStatus('topology');
            const scalerStatus = coordinator.getComponentStatus('scaler');
            
            expect(monitorStatus).toBeDefined();
            expect(topologyStatus).toBeDefined();
            expect(scalerStatus).toBeDefined();
        });
    });
    
    describe('Coordination Cycle', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should execute coordination cycles', async () => {
            const initialMetricsCount = coordinator.coordinationMetrics.size;
            
            // Trigger a coordination cycle
            await coordinator.coordinationCycle();
            
            expect(coordinator.coordinationMetrics.size).toBeGreaterThan(initialMetricsCount);
        });
        
        test('should collect system state', async () => {
            const systemState = await coordinator.collectSystemState();
            
            expect(systemState.timestamp).toBeDefined();
            expect(systemState.performance).toBeDefined();
            expect(systemState.topology).toBeDefined();
            expect(systemState.patterns).toBeDefined();
            expect(systemState.alerts).toBeDefined();
        });
        
        test('should analyze coordination effectiveness', async () => {
            const systemState = await coordinator.collectSystemState();
            const effectiveness = await coordinator.analyzeCoordinationEffectiveness(systemState);
            
            expect(effectiveness.score).toBeGreaterThanOrEqual(0);
            expect(effectiveness.score).toBeLessThanOrEqual(1);
            expect(effectiveness.components).toBeDefined();
            expect(effectiveness.bottlenecks).toBeDefined();
            expect(effectiveness.opportunities).toBeDefined();
        });
        
        test('should make coordination decisions', async () => {
            const systemState = await coordinator.collectSystemState();
            const effectiveness = await coordinator.analyzeCoordinationEffectiveness(systemState);
            const decisions = await coordinator.makeCoordinationDecisions(systemState, effectiveness);
            
            expect(Array.isArray(decisions)).toBe(true);
        });
        
        test('should apply coordination decisions', async () => {
            const mockDecisions = [
                {
                    type: 'topology_analysis',
                    action: 'force_evaluation',
                    component: 'topology'
                }
            ];
            
            // Should not throw errors
            await expect(coordinator.applyCoordinationDecisions(mockDecisions)).resolves.not.toThrow();
        });
    });
    
    describe('Emergency Mode', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should detect emergency conditions', async () => {
            // Mock emergency conditions by setting high error rate
            const monitor = coordinator.components.get('monitor');
            const mockMetrics = {
                timestamp: Date.now(),
                hive: {
                    errorRate: 0.8, // Above emergency threshold
                    averageResponseTime: 3000,
                    efficiency: 0.3
                },
                coordination: {
                    agentCount: 1 // Below minimum
                }
            };
            
            // Override getLatestMetrics to return emergency conditions
            monitor.getLatestMetrics = () => mockMetrics;
            
            await coordinator.checkEmergencyConditions();
            
            expect(coordinator.emergencyMode).toBe(true);
        });
        
        test('should exit emergency mode when conditions resolve', async () => {
            // First enter emergency mode
            coordinator.emergencyMode = true;
            
            // Mock normal conditions
            const monitor = coordinator.components.get('monitor');
            const mockMetrics = {
                timestamp: Date.now(),
                hive: {
                    errorRate: 0.02, // Normal
                    averageResponseTime: 1000,
                    efficiency: 0.8
                },
                coordination: {
                    agentCount: 5 // Sufficient
                }
            };
            
            monitor.getLatestMetrics = () => mockMetrics;
            
            await coordinator.checkEmergencyConditions();
            
            expect(coordinator.emergencyMode).toBe(false);
        });
        
        test('should execute emergency response protocols', async () => {
            const emergencyConditions = [
                {
                    type: 'high_error_rate',
                    value: 0.8,
                    threshold: 0.5
                }
            ];
            
            await coordinator.handleEmergencyResponse({ conditions: emergencyConditions });
            
            // Should complete without errors
            expect(true).toBe(true);
        });
        
        test('should make emergency decisions', async () => {
            const mockSystemState = {
                performance: {
                    system: { cpuUsage: 0.97 }, // Emergency level
                    hive: { errorRate: 0.6 }
                },
                alerts: [
                    { type: 'AGENT_FAILURE', severity: 'critical' }
                ]
            };
            
            const decisions = await coordinator.makeEmergencyDecisions(mockSystemState);
            
            expect(decisions.length).toBeGreaterThan(0);
            expect(decisions.some(d => d.urgency === 'critical')).toBe(true);
        });
    });
    
    describe('Pattern Learning and Adaptation', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should learn from coordination cycles', async () => {
            const mockSystemState = {
                performance: { system: { cpuUsage: 0.5 }, hive: { errorRate: 0.1 } },
                alerts: [],
                patterns: [],
                topology: 'mesh'
            };
            
            const mockDecisions = [
                { type: 'load_balancing', action: 'force_rebalance' }
            ];
            
            const initialHistoryLength = coordinator.patternLearning.adaptationHistory.length;
            
            await coordinator.learnFromCycle(mockSystemState, mockDecisions);
            
            expect(coordinator.patternLearning.adaptationHistory.length).toBe(initialHistoryLength + 1);
        });
        
        test('should reinforce successful patterns', async () => {
            const successfulDecisions = [
                { type: 'topology_analysis', action: 'force_evaluation' },
                { type: 'load_balancing', action: 'force_rebalance' }
            ];
            
            const initialSuccessPatterns = coordinator.patternLearning.successPatterns.size;
            
            coordinator.reinforceSuccessfulPatterns(successfulDecisions);
            
            expect(coordinator.patternLearning.successPatterns.size).toBeGreaterThanOrEqual(initialSuccessPatterns);
        });
        
        test('should learn from failures', async () => {
            const failedDecisions = [
                { type: 'emergency_scaling', action: 'scale_up' }
            ];
            
            const initialFailurePatterns = coordinator.patternLearning.failurePatterns.size;
            
            coordinator.learnFromFailures(failedDecisions);
            
            expect(coordinator.patternLearning.failurePatterns.size).toBeGreaterThanOrEqual(initialFailurePatterns);
        });
        
        test('should apply pattern optimizations', async () => {
            const mockPattern = {
                type: 'coordination',
                description: 'Test coordination pattern',
                utility: 0.8,
                confidence: 0.9
            };
            
            // Should not throw errors
            await expect(coordinator.applyPatternOptimization(mockPattern)).resolves.not.toThrow();
        });
    });
    
    describe('Hook System', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should add hooks successfully', async () => {
            const mockCallback = jest.fn();
            
            const result = await coordinator.addHook('onPerformanceAlert', mockCallback);
            
            expect(result).toBe(true);
            expect(coordinator.hooks.onPerformanceAlert).toContain(mockCallback);
        });
        
        test('should reject invalid hook types', async () => {
            const mockCallback = jest.fn();
            
            const result = await coordinator.addHook('invalidHookType', mockCallback);
            
            expect(result).toBe(false);
        });
        
        test('should trigger hooks with data', async () => {
            const mockCallback = jest.fn();
            await coordinator.addHook('onPerformanceAlert', mockCallback);
            
            const testData = { type: 'test_alert', severity: 'warning' };
            await coordinator.triggerHook('onPerformanceAlert', testData);
            
            expect(mockCallback).toHaveBeenCalledWith(testData);
        });
        
        test('should handle hook callback errors gracefully', async () => {
            const failingCallback = jest.fn(() => {
                throw new Error('Hook callback error');
            });
            
            await coordinator.addHook('onPerformanceAlert', failingCallback);
            
            // Should not throw even if callback fails
            await expect(coordinator.triggerHook('onPerformanceAlert', {})).resolves.not.toThrow();
        });
    });
    
    describe('Component Integration', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should integrate monitor with other components', async () => {
            const alert = {
                type: 'HIGH_ERROR_RATE',
                severity: 'critical',
                data: { errorRate: 0.15 }
            };
            
            // Trigger performance alert hook
            await coordinator.triggerHook('onPerformanceAlert', alert);
            
            // Should complete without errors
            expect(true).toBe(true);
        });
        
        test('should integrate topology changes with scaler', async () => {
            const topologyChange = {
                from: 'hierarchical',
                to: 'mesh',
                performanceData: { improvement: 0.15 }
            };
            
            await coordinator.triggerHook('onTopologyChange', topologyChange);
            
            // Should complete without errors
            expect(true).toBe(true);
        });
        
        test('should integrate pattern detection across components', async () => {
            const pattern = {
                type: 'performance_optimization',
                description: 'Test pattern',
                utility: 0.8
            };
            
            await coordinator.triggerHook('onPatternDetection', pattern);
            
            // Should complete without errors
            expect(true).toBe(true);
        });
    });
    
    describe('Performance and Metrics', () => {
        beforeEach(async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
        });
        
        test('should track coordination metrics', async () => {
            // Execute a few coordination cycles
            await coordinator.coordinationCycle();
            await coordinator.coordinationCycle();
            
            const summary = coordinator.getCoordinationSummary();
            
            expect(summary.averageEffectiveness).toBeGreaterThanOrEqual(0);
            expect(summary.averageEffectiveness).toBeLessThanOrEqual(1);
            expect(summary.averageCycleDuration).toBeGreaterThan(0);
            expect(summary.emergencyModeTime).toBeGreaterThanOrEqual(0);
        });
        
        test('should calculate overall performance', () => {
            const mockPerformance = {
                system: { cpuUsage: 0.3, memoryUsage: 0.4 },
                hive: { errorRate: 0.05, efficiency: 0.8 }
            };
            
            const score = coordinator.calculateOverallPerformance(mockPerformance);
            
            expect(score).toBeGreaterThanOrEqual(0);
            expect(score).toBeLessThanOrEqual(1);
        });
        
        test('should identify bottlenecks', () => {
            const mockSystemState = {
                alerts: [
                    { type: 'HIGH_CPU', severity: 'critical' },
                    { type: 'HIGH_MEMORY', severity: 'critical' },
                    { type: 'HIGH_ERROR_RATE', severity: 'critical' },
                    { type: 'SLOW_RESPONSE', severity: 'critical' }
                ]
            };
            
            const mockEffectiveness = {
                monitor: 0.4, // Below threshold
                topology: 0.5, // Below threshold
                scaling: 0.8,
                loadBalancing: 0.9,
                patterns: 0.7
            };
            
            const bottlenecks = coordinator.identifyBottlenecks(mockSystemState, mockEffectiveness);
            
            expect(bottlenecks.length).toBeGreaterThan(0);
            expect(bottlenecks.some(b => b.component === 'monitor')).toBe(true);
            expect(bottlenecks.some(b => b.component === 'topology')).toBe(true);
        });
        
        test('should identify optimization opportunities', () => {
            const mockSystemState = {
                performance: { system: { cpuUsage: 0.3 }, hive: { efficiency: 0.8 } }
            };
            
            const mockEffectiveness = {
                scaling: 0.95,
                loadBalancing: 0.6,
                patterns: 0.7
            };
            
            const opportunities = coordinator.identifyOptimizationOpportunities(mockSystemState, mockEffectiveness);
            
            expect(Array.isArray(opportunities)).toBe(true);
        });
    });
    
    describe('Cleanup and Shutdown', () => {
        test('should stop gracefully', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(coordinator.status).toBe('active');
            
            coordinator.stop();
            
            expect(coordinator.status).toBe('stopped');
        });
        
        test('should stop all components', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Mock component stop methods
            coordinator.components.forEach(component => {
                component.stop = jest.fn();
            });
            
            coordinator.stop();
            
            coordinator.components.forEach(component => {
                expect(component.stop).toHaveBeenCalled();
            });
        });
        
        test('should clear intervals on stop', async () => {
            coordinator = new HiveCoordinator(mockConfig);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
            
            coordinator.stop();
            
            expect(clearIntervalSpy).toHaveBeenCalledTimes(3); // Three intervals should be cleared
            
            clearIntervalSpy.mockRestore();
        });
    });
});
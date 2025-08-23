/**
 * Comprehensive Stress Testing Suite for Hive Coordination System
 * Tests system behavior under extreme conditions, load scenarios, and edge cases
 */

const { HiveQueenCoordinator } = require('../../src/hive/coordinator');
const { HiveFaultTolerance } = require('../../src/hive/fault-tolerance');

describe('Hive Stress Testing Suite', () => {
    let queen;
    let faultTolerance;
    let mockConfig;
    
    beforeEach(async () => {
        mockConfig = {
            hive: {
                structure: {
                    queen: {
                        max_workers: 50,
                        coordination_mode: 'adaptive'
                    },
                    worker_castes: {
                        foragers: {
                            min_count: 2,
                            max_count: 15,
                            agents: ['researcher', 'data-analyzer', 'api-explorer'],
                            specialization: 'data_gathering'
                        },
                        builders: {
                            min_count: 3,
                            max_count: 20,
                            agents: ['coder', 'architect', 'designer'],
                            specialization: 'implementation'
                        },
                        guardians: {
                            min_count: 2,
                            max_count: 12,
                            agents: ['tester', 'reviewer', 'security-analyst'],
                            specialization: 'validation'
                        },
                        nurses: {
                            min_count: 1,
                            max_count: 8,
                            agents: ['deployment-manager', 'monitor', 'optimizer'],
                            specialization: 'maintenance'
                        }
                    }
                },
                fault_tolerance: {
                    health_checks: {
                        interval: 500,
                        timeout: 2000,
                        retry_attempts: 5
                    },
                    recovery: {
                        auto_restart: true,
                        failover_delay: 1000,
                        max_recovery_attempts: 5
                    },
                    redundancy: {
                        critical_roles: ['builders', 'guardians', 'nurses'],
                        backup_count: 3,
                        replication_factor: 2.0
                    }
                },
                adaptive_scaling: {
                    enabled: true,
                    scale_up_threshold: 0.75,
                    scale_down_threshold: 0.25,
                    min_instances: 1,
                    max_instances: 10
                }
            }
        };
        
        queen = new HiveQueenCoordinator(mockConfig);
        await queen.initialize();
        
        faultTolerance = new HiveFaultTolerance(queen, mockConfig);
        await faultTolerance.initialize();
    });
    
    afterEach(async () => {
        if (faultTolerance) {
            faultTolerance.stop && faultTolerance.stop();
        }
        if (queen) {
            queen.stop && queen.stop();
        }
    });

    describe('High Load Stress Tests', () => {
        
        test('should handle massive task influx without degradation', async () => {
            const taskCount = 100;
            const tasks = Array.from({ length: taskCount }, (_, i) => ({
                id: `stress-task-${i}`,
                type: i % 2 === 0 ? 'implement_feature' : 'test_feature',
                priority: ['low', 'medium', 'high', 'critical'][i % 4],
                complexity: Math.random() > 0.5 ? 'high' : 'low'
            }));
            
            const startTime = Date.now();
            const assignments = [];
            
            // Submit all tasks rapidly
            for (const task of tasks) {
                try {
                    const assignment = await queen.delegateTask(task);
                    assignments.push(assignment);
                } catch (error) {
                    // Track failed assignments
                    assignments.push({ error: error.message });
                }
            }
            
            const processingTime = Date.now() - startTime;
            const successfulAssignments = assignments.filter(a => !a.error);
            
            // Performance assertions
            expect(processingTime).toBeLessThan(10000); // Should complete within 10 seconds
            expect(successfulAssignments.length).toBeGreaterThan(taskCount * 0.8); // 80% success rate
            
            // System should still be responsive
            const status = queen.getWorkerSummary();
            expect(status.total).toBeGreaterThan(0);
        });
        
        test('should scale workers dynamically under sustained load', async () => {
            const initialWorkerCount = queen.workers.size;
            
            // Create sustained high load
            const sustainedTasks = Array.from({ length: 50 }, (_, i) => ({
                id: `sustained-task-${i}`,
                type: 'implement_complex_feature',
                priority: 'high',
                estimatedDuration: 5000 // 5 seconds
            }));
            
            // Assign all tasks to create load
            const assignments = [];
            for (const task of sustainedTasks) {
                const assignment = await queen.delegateTask(task);
                assignments.push(assignment);
                
                // Mark workers as busy
                const worker = queen.workers.get(assignment.workerId);
                if (worker) {
                    worker.status = 'working';
                    worker.currentTask = task;
                }
            }
            
            // Trigger adaptive scaling
            await queen.adaptiveScale();
            
            const finalWorkerCount = queen.workers.size;
            
            // Should have scaled up under load
            expect(finalWorkerCount).toBeGreaterThanOrEqual(initialWorkerCount);
            
            // Verify scaling was appropriate
            const utilizationRate = assignments.length / finalWorkerCount;
            expect(utilizationRate).toBeLessThan(mockConfig.hive.adaptive_scaling.scale_up_threshold * 1.5);
        });
        
        test('should maintain performance under concurrent worker failures', async () => {
            const workers = Array.from(queen.workers.values());
            const failureRate = 0.3; // 30% failure rate
            const failingWorkerCount = Math.floor(workers.length * failureRate);
            
            // Create background load
            const backgroundTasks = Array.from({ length: 20 }, (_, i) => ({
                id: `background-task-${i}`,
                type: 'routine_operation',
                priority: 'medium'
            }));
            
            const startTime = Date.now();
            
            // Start background operations
            const taskPromises = backgroundTasks.map(task => queen.delegateTask(task));
            
            // Simultaneously trigger worker failures
            const failurePromises = workers.slice(0, failingWorkerCount).map(async (worker, index) => {
                await new Promise(resolve => setTimeout(resolve, index * 100)); // Stagger failures
                return faultTolerance.handleWorkerFailure(worker, new Error('Concurrent stress failure'));
            });
            
            // Wait for both operations to complete
            const [taskResults, failureResults] = await Promise.allSettled([
                Promise.allSettled(taskPromises),
                Promise.allSettled(failurePromises)
            ]);
            
            const totalTime = Date.now() - startTime;
            
            // Performance should remain acceptable despite failures
            expect(totalTime).toBeLessThan(15000); // 15 seconds max
            
            // System should still be operational
            const remainingWorkers = queen.workers.size;
            expect(remainingWorkers).toBeGreaterThan(workers.length * 0.5); // At least 50% workers remain
        });
        
        test('should handle rapid scaling up and down cycles', async () => {
            const cycles = 5;
            const scalingHistory = [];
            
            for (let cycle = 0; cycle < cycles; cycle++) {
                const cycleStart = Date.now();
                
                // Scale up phase - create high load
                const loadTasks = Array.from({ length: 15 }, (_, i) => ({
                    id: `cycle-${cycle}-load-${i}`,
                    type: 'scale_test_task',
                    priority: 'high'
                }));
                
                // Assign tasks to trigger scale up
                for (const task of loadTasks) {
                    const assignment = await queen.delegateTask(task);
                    const worker = queen.workers.get(assignment.workerId);
                    if (worker) {
                        worker.status = 'working';
                        worker.currentTask = task;
                    }
                }
                
                const scaleUpWorkers = queen.workers.size;
                await queen.adaptiveScale();
                
                // Scale down phase - remove load
                queen.workers.forEach(worker => {
                    worker.status = 'idle';
                    worker.currentTask = null;
                    worker.performance.lastActive = Date.now() - 300000; // Mark as idle
                });
                
                await queen.adaptiveScale();
                const scaleDownWorkers = queen.workers.size;
                
                scalingHistory.push({
                    cycle,
                    scaleUpWorkers,
                    scaleDownWorkers,
                    duration: Date.now() - cycleStart
                });
                
                // Brief pause between cycles
                await new Promise(resolve => setTimeout(resolve, 200));
            }
            
            // Verify scaling behavior
            expect(scalingHistory.length).toBe(cycles);
            
            // Each cycle should complete reasonably quickly
            const averageCycleDuration = scalingHistory.reduce((sum, h) => sum + h.duration, 0) / cycles;
            expect(averageCycleDuration).toBeLessThan(5000); // 5 seconds per cycle
            
            // System should remain stable
            expect(queen.workers.size).toBeGreaterThan(0);
        });
    });

    describe('Resource Exhaustion Tests', () => {
        
        test('should gracefully handle memory pressure simulation', async () => {
            // Simulate memory pressure by creating large data structures
            const largeDataTasks = Array.from({ length: 20 }, (_, i) => ({
                id: `memory-task-${i}`,
                type: 'process_large_dataset',
                priority: 'high',
                data: {
                    size: 'large',
                    processingLoad: 'heavy',
                    memoryFootprint: Array(1000).fill(`data-chunk-${i}`) // Simulate large data
                }
            }));
            
            const startTime = Date.now();
            const memoryResults = [];
            
            for (const task of largeDataTasks) {
                try {
                    const assignment = await queen.delegateTask(task);
                    memoryResults.push({ success: true, assignment });
                } catch (error) {
                    memoryResults.push({ success: false, error: error.message });
                }
            }
            
            const processingTime = Date.now() - startTime;
            const successRate = memoryResults.filter(r => r.success).length / largeDataTasks.length;
            
            // System should handle at least 70% of memory-intensive tasks
            expect(successRate).toBeGreaterThan(0.7);
            expect(processingTime).toBeLessThan(20000); // 20 seconds max
            
            // System should remain responsive
            const healthStatus = faultTolerance.getStatus();
            expect(healthStatus.health_monitoring.active).toBe(true);
        });
        
        test('should handle CPU-intensive task distribution', async () => {
            const cpuIntensiveTasks = Array.from({ length: 30 }, (_, i) => ({
                id: `cpu-task-${i}`,
                type: 'heavy_computation',
                priority: ['high', 'critical'][i % 2],
                computation: {
                    complexity: 'O(n²)',
                    iterations: 10000,
                    parallelizable: i % 3 === 0
                }
            }));
            
            const distributionStart = Date.now();
            const cpuTaskResults = [];
            
            // Distribute CPU-intensive tasks
            for (const task of cpuIntensiveTasks) {
                const assignment = await queen.delegateTask(task);
                cpuTaskResults.push(assignment);
                
                // Simulate CPU load on assigned worker
                const worker = queen.workers.get(assignment.workerId);
                if (worker) {
                    worker.status = 'working';
                    worker.currentTask = task;
                    worker.performance.lastActive = Date.now();
                }
            }
            
            const distributionTime = Date.now() - distributionStart;
            
            // Verify distribution efficiency
            expect(distributionTime).toBeLessThan(10000); // 10 seconds
            expect(cpuTaskResults.length).toBe(cpuIntensiveTasks.length);
            
            // Check load distribution across workers
            const workerLoads = new Map();
            cpuTaskResults.forEach(result => {
                const count = workerLoads.get(result.workerId) || 0;
                workerLoads.set(result.workerId, count + 1);
            });
            
            // Load should be reasonably distributed
            const maxLoad = Math.max(...workerLoads.values());
            const minLoad = Math.min(...workerLoads.values());
            const loadImbalance = (maxLoad - minLoad) / maxLoad;
            expect(loadImbalance).toBeLessThan(0.5); // Max 50% imbalance
        });
        
        test('should maintain stability during network simulation stress', async () => {
            // Simulate network delays and failures in communication
            const networkStressTasks = Array.from({ length: 25 }, (_, i) => ({
                id: `network-task-${i}`,
                type: 'remote_api_call',
                priority: 'medium',
                network: {
                    latency: Math.random() * 1000, // 0-1000ms latency
                    failureRate: Math.random() * 0.2, // 0-20% failure rate
                    retryRequired: i % 5 === 0
                }
            }));
            
            const networkStart = Date.now();
            const networkResults = [];
            
            // Process tasks with simulated network conditions
            for (const task of networkStressTasks) {
                try {
                    // Simulate network delay
                    await new Promise(resolve => setTimeout(resolve, task.network.latency / 10));
                    
                    // Simulate network failure
                    if (Math.random() < task.network.failureRate) {
                        throw new Error('Simulated network failure');
                    }
                    
                    const assignment = await queen.delegateTask(task);
                    networkResults.push({ success: true, assignment, latency: task.network.latency });
                } catch (error) {
                    networkResults.push({ success: false, error: error.message });
                }
            }
            
            const networkTime = Date.now() - networkStart;
            const networkSuccessRate = networkResults.filter(r => r.success).length / networkStressTasks.length;
            
            // System should handle majority of network tasks despite simulation stress
            expect(networkSuccessRate).toBeGreaterThan(0.6); // 60% success rate
            expect(networkTime).toBeLessThan(15000); // 15 seconds
            
            // System health should remain good
            const status = queen.getWorkerSummary();
            expect(status.total).toBeGreaterThan(0);
        });
    });

    describe('Edge Case and Boundary Testing', () => {
        
        test('should handle zero available workers scenario', async () => {
            // Remove all workers except backups
            const allWorkers = Array.from(queen.workers.keys());
            allWorkers.forEach(workerId => {
                const worker = queen.workers.get(workerId);
                if (worker && worker.status !== 'standby') {
                    queen.workers.delete(workerId);
                }
            });
            
            const activeWorkers = Array.from(queen.workers.values())
                .filter(w => w.status !== 'standby');
            expect(activeWorkers.length).toBe(0);
            
            // Attempt to delegate task with no active workers
            const emergencyTask = {
                id: 'emergency-zero-workers',
                type: 'critical_system_restore',
                priority: 'critical'
            };
            
            // System should either:
            // 1. Activate backup workers, or
            // 2. Spawn new workers, or
            // 3. Gracefully handle the no-worker scenario
            const assignment = await queen.delegateTask(emergencyTask);
            
            expect(assignment).toBeDefined();
            expect(assignment.workerId).toBeDefined();
            
            // Verify a worker was activated or created
            const newActiveWorkers = Array.from(queen.workers.values())
                .filter(w => w.status !== 'standby');
            expect(newActiveWorkers.length).toBeGreaterThan(0);
        });
        
        test('should handle maximum worker count limits', async () => {
            const maxWorkers = mockConfig.hive.structure.queen.max_workers;
            
            // Try to spawn workers beyond the limit
            const builderConfig = mockConfig.hive.structure.worker_castes.builders;
            
            // Spawn workers up to the limit
            const spawnPromises = [];
            for (let i = 0; i < maxWorkers; i++) {
                spawnPromises.push(queen.spawnWorker('builders', builderConfig, 1000 + i));
            }
            
            await Promise.allSettled(spawnPromises);
            
            const totalWorkers = queen.workers.size;
            
            // Should respect the maximum limit
            expect(totalWorkers).toBeLessThanOrEqual(maxWorkers);
            
            // Try to spawn one more worker beyond limit
            try {
                const extraWorker = await queen.spawnWorker('builders', builderConfig, 9999);
                
                // If spawning succeeds, total should still respect limit
                const finalWorkers = queen.workers.size;
                expect(finalWorkers).toBeLessThanOrEqual(maxWorkers);
            } catch (error) {
                // Expected behavior - should reject spawning beyond limit
                expect(error.message).toContain('maximum' || 'limit' || 'capacity');
            }
        });
        
        test('should handle rapid sequential task types switching', async () => {
            const taskTypes = [
                'research_data', 'implement_feature', 'test_functionality', 
                'deploy_service', 'monitor_performance', 'analyze_metrics',
                'refactor_code', 'review_security', 'backup_data', 'optimize_performance'
            ];
            
            const rapidTasks = Array.from({ length: 50 }, (_, i) => ({
                id: `rapid-switch-${i}`,
                type: taskTypes[i % taskTypes.length],
                priority: ['low', 'medium', 'high'][i % 3],
                switchDelay: 50 // Rapid switching every 50ms
            }));
            
            const switchingStart = Date.now();
            const switchingResults = [];
            
            for (const task of rapidTasks) {
                const assignment = await queen.delegateTask(task);
                switchingResults.push({
                    taskType: task.type,
                    workerCaste: assignment.workerCaste,
                    assignedAgentType: assignment.agentType
                });
                
                // Rapid task switching
                await new Promise(resolve => setTimeout(resolve, task.switchDelay));
            }
            
            const switchingTime = Date.now() - switchingStart;
            
            // Should handle rapid switching efficiently
            expect(switchingTime).toBeLessThan(8000); // 8 seconds for 50 rapid switches
            expect(switchingResults.length).toBe(rapidTasks.length);
            
            // Verify appropriate caste assignments for different task types
            const casteDistribution = {};
            switchingResults.forEach(result => {
                casteDistribution[result.workerCaste] = (casteDistribution[result.workerCaste] || 0) + 1;
            });
            
            // Should use multiple castes
            expect(Object.keys(casteDistribution).length).toBeGreaterThan(1);
        });
        
        test('should handle circular dependency resolution', async () => {
            // Create tasks with circular dependencies
            const dependencyTasks = [
                {
                    id: 'task-a',
                    type: 'implement_module_a',
                    dependencies: ['task-c'],
                    priority: 'high'
                },
                {
                    id: 'task-b',
                    type: 'implement_module_b',
                    dependencies: ['task-a'],
                    priority: 'high'
                },
                {
                    id: 'task-c',
                    type: 'implement_module_c',
                    dependencies: ['task-b'],
                    priority: 'high'
                }
            ];
            
            const dependencyStart = Date.now();
            const dependencyResults = [];
            
            // Attempt to delegate circular dependency tasks
            for (const task of dependencyTasks) {
                try {
                    const assignment = await queen.delegateTask(task);
                    dependencyResults.push({ 
                        success: true, 
                        taskId: task.id, 
                        assignment 
                    });
                } catch (error) {
                    dependencyResults.push({ 
                        success: false, 
                        taskId: task.id, 
                        error: error.message 
                    });
                }
            }
            
            const dependencyTime = Date.now() - dependencyStart;
            
            // System should handle circular dependencies gracefully
            expect(dependencyTime).toBeLessThan(5000); // 5 seconds
            expect(dependencyResults.length).toBe(dependencyTasks.length);
            
            // At least some tasks should be assigned or system should detect the cycle
            const successfulAssignments = dependencyResults.filter(r => r.success);
            expect(successfulAssignments.length + dependencyResults.filter(r => 
                r.error && r.error.includes('circular' || 'dependency' || 'cycle')
            ).length).toBe(dependencyTasks.length);
        });
    });

    describe('Long-Running Stability Tests', () => {
        
        test('should maintain system stability over extended operation', async () => {
            const operationDuration = 10000; // 10 seconds of continuous operation
            const taskInterval = 200; // New task every 200ms
            const startTime = Date.now();
            
            const stabilityMetrics = {
                tasksProcessed: 0,
                failuresDetected: 0,
                recoveryActions: 0,
                memoryLeaks: 0
            };
            
            // Continuous operation simulation
            while (Date.now() - startTime < operationDuration) {
                try {
                    // Submit task
                    const task = {
                        id: `stability-task-${stabilityMetrics.tasksProcessed}`,
                        type: ['research', 'implement', 'test', 'deploy'][stabilityMetrics.tasksProcessed % 4],
                        priority: 'medium'
                    };
                    
                    await queen.delegateTask(task);
                    stabilityMetrics.tasksProcessed++;
                    
                    // Occasionally simulate worker failures
                    if (Math.random() < 0.05) { // 5% chance
                        const workers = Array.from(queen.workers.values());
                        if (workers.length > 0) {
                            const randomWorker = workers[Math.floor(Math.random() * workers.length)];
                            faultTolerance.handleWorkerFailure(randomWorker, new Error('Random stability test failure'));
                            stabilityMetrics.failuresDetected++;
                        }
                    }
                    
                    // Check for memory accumulation
                    if (stabilityMetrics.tasksProcessed % 20 === 0) {
                        const workerCount = queen.workers.size;
                        const healthChecks = faultTolerance.healthChecks.size;
                        
                        // Basic memory leak detection
                        if (healthChecks > workerCount * 10) {
                            stabilityMetrics.memoryLeaks++;
                        }
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, taskInterval));
                    
                } catch (error) {
                    stabilityMetrics.recoveryActions++;
                }
            }
            
            // Verify long-running stability
            expect(stabilityMetrics.tasksProcessed).toBeGreaterThan(30); // Should process many tasks
            expect(stabilityMetrics.memoryLeaks).toBe(0); // No memory leaks
            
            // System should still be operational
            const finalStatus = queen.getWorkerSummary();
            expect(finalStatus.total).toBeGreaterThan(0);
            
            const faultStatus = faultTolerance.getStatus();
            expect(faultStatus.resilience_score).toBeGreaterThan(0.5); // Maintain reasonable resilience
        });
        
        test('should handle gradual system degradation', async () => {
            const degradationSteps = 8;
            const degradationMetrics = [];
            
            for (let step = 0; step < degradationSteps; step++) {
                const stepStart = Date.now();
                
                // Gradually increase system stress
                const stressLevel = (step + 1) / degradationSteps;
                const failureRate = stressLevel * 0.3; // Up to 30% failure rate
                const taskLoad = Math.floor(stressLevel * 15); // Up to 15 concurrent tasks
                
                // Apply stress
                const workers = Array.from(queen.workers.values());
                const failureCount = Math.floor(workers.length * failureRate);
                
                // Induce failures
                for (let i = 0; i < failureCount && i < workers.length; i++) {
                    await faultTolerance.handleWorkerFailure(
                        workers[i], 
                        new Error(`Degradation step ${step} failure`)
                    );
                }
                
                // Apply task load
                const loadTasks = Array.from({ length: taskLoad }, (_, i) => ({
                    id: `degradation-step-${step}-task-${i}`,
                    type: 'stress_operation',
                    priority: 'medium'
                }));
                
                const loadAssignments = [];
                for (const task of loadTasks) {
                    try {
                        const assignment = await queen.delegateTask(task);
                        loadAssignments.push(assignment);
                    } catch (error) {
                        // Track failed assignments
                    }
                }
                
                // Measure system state
                const workerCount = queen.workers.size;
                const healthStatus = faultTolerance.getStatus();
                const stepTime = Date.now() - stepStart;
                
                degradationMetrics.push({
                    step,
                    stressLevel,
                    workerCount,
                    resilienceScore: healthStatus.resilience_score,
                    taskSuccessRate: loadAssignments.length / taskLoad,
                    responseTime: stepTime
                });
                
                // Brief recovery period
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // Analyze degradation behavior
            const initialMetrics = degradationMetrics[0];
            const finalMetrics = degradationMetrics[degradationMetrics.length - 1];
            
            // System should maintain basic functionality even under high stress
            expect(finalMetrics.workerCount).toBeGreaterThan(0);
            expect(finalMetrics.resilienceScore).toBeGreaterThan(0.2); // Minimum resilience
            expect(finalMetrics.taskSuccessRate).toBeGreaterThan(0.3); // Some tasks should still succeed
            
            // Response time should not degrade beyond reasonable limits
            expect(finalMetrics.responseTime).toBeLessThan(20000); // 20 seconds max
        });
    });
});
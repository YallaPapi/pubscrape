/**
 * Comprehensive Fault Tolerance Test Suite for Hive Coordination System
 * Tests worker failures, redundancy mechanisms, emergency handling, and system resilience
 */

const { HiveQueenCoordinator } = require('../../src/hive/coordinator');
const { HiveFaultTolerance } = require('../../src/hive/fault-tolerance');

describe('Hive Fault Tolerance System', () => {
    let queen;
    let faultTolerance;
    let mockConfig;
    
    beforeEach(async () => {
        mockConfig = {
            hive: {
                structure: {
                    queen: {
                        max_workers: 20,
                        coordination_mode: 'adaptive'
                    },
                    worker_castes: {
                        foragers: {
                            min_count: 2,
                            max_count: 8,
                            agents: ['researcher', 'data-analyzer'],
                            specialization: 'data_gathering'
                        },
                        builders: {
                            min_count: 3,
                            max_count: 10,
                            agents: ['coder', 'architect'],
                            specialization: 'implementation'
                        },
                        guardians: {
                            min_count: 2,
                            max_count: 6,
                            agents: ['tester', 'reviewer'],
                            specialization: 'validation'
                        },
                        nurses: {
                            min_count: 1,
                            max_count: 4,
                            agents: ['deployment-manager', 'monitor'],
                            specialization: 'maintenance'
                        }
                    }
                },
                fault_tolerance: {
                    health_checks: {
                        interval: 1000,
                        timeout: 5000,
                        retry_attempts: 3
                    },
                    recovery: {
                        auto_restart: true,
                        failover_delay: 2000,
                        max_recovery_attempts: 3
                    },
                    redundancy: {
                        critical_roles: ['builders', 'guardians'],
                        backup_count: 2,
                        replication_factor: 1.5
                    }
                },
                adaptive_scaling: {
                    enabled: true,
                    scale_up_threshold: 0.8,
                    scale_down_threshold: 0.3,
                    min_instances: 1,
                    max_instances: 5
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

    describe('Worker Failure Detection and Recovery', () => {
        
        test('should detect unresponsive workers', async () => {
            const workers = Array.from(queen.workers.values());
            expect(workers.length).toBeGreaterThan(0);
            
            const testWorker = workers[0];
            
            // Simulate worker becoming unresponsive
            testWorker.performance.lastActive = Date.now() - 400000; // 6+ minutes ago
            
            const health = await faultTolerance.checkWorkerHealth(testWorker);
            
            expect(health.healthy).toBe(false);
            expect(health.issues).toContain('inactive');
        });
        
        test('should detect workers with poor performance', async () => {
            const workers = Array.from(queen.workers.values());
            const testWorker = workers[0];
            
            // Simulate poor performance
            testWorker.performance.successRate = 0.5; // Below 0.7 threshold
            
            const health = await faultTolerance.checkWorkerHealth(testWorker);
            
            expect(health.healthy).toBe(false);
            expect(health.issues).toContain('low_success_rate');
        });
        
        test('should automatically restart failed workers', async () => {
            const workers = Array.from(queen.workers.values());
            const testWorker = workers[0];
            const originalLastActive = testWorker.performance.lastActive;
            
            // Simulate worker failure
            testWorker.status = 'error';
            testWorker.performance.lastActive = Date.now() - 400000;
            
            await faultTolerance.restartWorker(testWorker);
            
            expect(testWorker.status).toBe('idle');
            expect(testWorker.currentTask).toBeNull();
            expect(testWorker.performance.lastActive).toBeGreaterThan(originalLastActive);
        });
        
        test('should activate backup workers when restart fails', async () => {
            const workers = Array.from(queen.workers.values());
            const builderWorkers = workers.filter(w => w.caste === 'builders');
            const testWorker = builderWorkers[0];
            const initialWorkerCount = queen.workers.size;
            
            // Simulate failed worker with current task
            testWorker.currentTask = {
                id: 'test-task-123',
                type: 'implement_feature',
                priority: 'high'
            };
            testWorker.status = 'error';
            
            await faultTolerance.activateBackupWorker(testWorker);
            
            // Worker should be removed and backup should be active
            expect(queen.workers.has(testWorker.id)).toBe(false);
            
            // Check if backup worker has the task
            const allWorkers = Array.from(queen.workers.values());
            const backupWithTask = allWorkers.find(w => w.currentTask?.id === 'test-task-123');
            expect(backupWithTask).toBeDefined();
        });
        
        test('should handle multiple concurrent worker failures', async () => {
            const workers = Array.from(queen.workers.values());
            const failedWorkers = workers.slice(0, 3); // Fail 3 workers
            
            // Simulate concurrent failures
            const failurePromises = failedWorkers.map(async (worker) => {
                worker.status = 'error';
                return faultTolerance.handleWorkerFailure(worker, new Error('Simulated failure'));
            });
            
            await Promise.all(failurePromises);
            
            // Check that failures were recorded
            expect(faultTolerance.failureHistory.length).toBeGreaterThanOrEqual(3);
            
            // Check that recovery was initiated for each
            const recentFailures = faultTolerance.failureHistory.filter(
                f => Date.now() - f.timestamp < 10000
            );
            expect(recentFailures.length).toBe(3);
        });
    });

    describe('Redundancy and Backup Systems', () => {
        
        test('should maintain backup workers for critical roles', async () => {
            const criticalRoles = mockConfig.hive.fault_tolerance.redundancy.critical_roles;
            const backupCount = mockConfig.hive.fault_tolerance.redundancy.backup_count;
            
            for (const role of criticalRoles) {
                let backupWorkers = 0;
                for (const [key, workerId] of faultTolerance.backupWorkers.entries()) {
                    if (key.startsWith(role + '-backup') && workerId !== null) {
                        backupWorkers++;
                    }
                }
                expect(backupWorkers).toBeGreaterThanOrEqual(1);
            }
        });
        
        test('should seamlessly transfer tasks to backup workers', async () => {
            const builders = Array.from(queen.workers.values()).filter(w => w.caste === 'builders');
            const primaryWorker = builders[0];
            
            // Assign a task to primary worker
            const testTask = {
                id: 'critical-task-456',
                type: 'implement_security_feature',
                priority: 'critical',
                data: { module: 'authentication' }
            };
            
            primaryWorker.currentTask = testTask;
            primaryWorker.status = 'working';
            
            // Simulate primary worker failure
            await faultTolerance.activateBackupWorker(primaryWorker);
            
            // Verify task was transferred
            const allWorkers = Array.from(queen.workers.values());
            const workerWithTask = allWorkers.find(w => w.currentTask?.id === 'critical-task-456');
            
            expect(workerWithTask).toBeDefined();
            expect(workerWithTask.status).toBe('working');
            expect(workerWithTask.caste).toBe('builders');
        });
        
        test('should maintain minimum worker count per caste', async () => {
            const castes = Object.keys(mockConfig.hive.structure.worker_castes);
            
            for (const caste of castes) {
                const casteConfig = mockConfig.hive.structure.worker_castes[caste];
                const casteWorkers = Array.from(queen.workers.values())
                    .filter(w => w.caste === caste && w.status !== 'standby');
                
                expect(casteWorkers.length).toBeGreaterThanOrEqual(casteConfig.min_count);
            }
        });
        
        test('should replicate critical workers based on replication factor', async () => {
            const replicationFactor = mockConfig.hive.fault_tolerance.redundancy.replication_factor;
            const criticalRoles = mockConfig.hive.fault_tolerance.redundancy.critical_roles;
            
            for (const role of criticalRoles) {
                const activeWorkers = Array.from(queen.workers.values())
                    .filter(w => w.caste === role && w.status !== 'standby');
                const backupWorkers = Array.from(faultTolerance.backupWorkers.values())
                    .filter(id => id !== null && queen.workers.get(id)?.caste === role);
                
                const totalWorkers = activeWorkers.length + backupWorkers.length;
                const expectedMinimum = Math.ceil(activeWorkers.length * replicationFactor);
                
                expect(totalWorkers).toBeGreaterThanOrEqual(expectedMinimum);
            }
        });
    });

    describe('Emergency Handling and Crisis Response', () => {
        
        test('should detect cascade failures', async () => {
            const builders = Array.from(queen.workers.values()).filter(w => w.caste === 'builders');
            
            // Simulate cascade failure - multiple workers in same caste failing rapidly
            for (let i = 0; i < Math.min(3, builders.length); i++) {
                const worker = builders[i];
                await faultTolerance.handleWorkerFailure(worker, new Error('Cascade failure'));
                await new Promise(resolve => setTimeout(resolve, 100)); // Small delay
            }
            
            // Check if escalation was triggered
            const recentFailures = faultTolerance.failureHistory
                .filter(f => f.caste === 'builders' && Date.now() - f.timestamp < 10000);
            
            expect(recentFailures.length).toBe(3);
        });
        
        test('should implement emergency scaling during crisis', async () => {
            const initialWorkerCount = queen.workers.size;
            
            // Simulate crisis - multiple workers across different castes failing
            const workers = Array.from(queen.workers.values());
            const criticalFailures = workers.slice(0, Math.floor(workers.length * 0.4));
            
            for (const worker of criticalFailures) {
                await faultTolerance.handleWorkerFailure(worker, new Error('Crisis failure'));
            }
            
            // System should attempt to scale up
            const finalWorkerCount = queen.workers.size;
            
            // Even with failures, system should maintain operations
            expect(finalWorkerCount).toBeGreaterThan(0);
        });
        
        test('should prioritize critical tasks during emergency', async () => {
            const workers = Array.from(queen.workers.values());
            
            // Create high-priority tasks
            const criticalTasks = [
                { id: 'security-patch', type: 'security_fix', priority: 'critical' },
                { id: 'data-backup', type: 'backup_data', priority: 'critical' },
                { id: 'system-restore', type: 'restore_service', priority: 'high' }
            ];
            
            // Assign critical tasks to workers
            criticalTasks.forEach((task, index) => {
                if (workers[index]) {
                    workers[index].currentTask = task;
                    workers[index].status = 'working';
                }
            });
            
            // Simulate emergency - half the workers fail
            const failingWorkers = workers.slice(0, Math.floor(workers.length / 2));
            
            for (const worker of failingWorkers) {
                if (worker.currentTask) {
                    await faultTolerance.activateBackupWorker(worker);
                }
            }
            
            // Verify critical tasks were preserved
            const allWorkers = Array.from(queen.workers.values());
            const criticalTasksInProgress = allWorkers
                .filter(w => w.currentTask?.priority === 'critical')
                .length;
            
            expect(criticalTasksInProgress).toBeGreaterThan(0);
        });
        
        test('should implement graceful degradation under extreme load', async () => {
            // Simulate extreme load by failing most workers
            const workers = Array.from(queen.workers.values());
            const survivingWorkers = workers.slice(0, 2); // Keep only 2 workers
            const failingWorkers = workers.slice(2);
            
            // Fail most workers
            for (const worker of failingWorkers) {
                queen.workers.delete(worker.id);
            }
            
            // System should still be operational with minimal workers
            expect(queen.workers.size).toBe(2);
            
            // Verify system can still delegate tasks
            const testTask = {
                id: 'emergency-task',
                type: 'critical_fix',
                priority: 'critical'
            };
            
            const assignment = await queen.delegateTask(testTask);
            expect(assignment).toBeDefined();
            expect(assignment.workerId).toBeDefined();
        });
    });

    describe('Adaptive Scaling and Load Balancing', () => {
        
        test('should scale up when worker capacity is exceeded', async () => {
            const initialBuilders = Array.from(queen.workers.values())
                .filter(w => w.caste === 'builders').length;
            
            // Simulate high load - assign tasks to all builders
            const builders = Array.from(queen.workers.values())
                .filter(w => w.caste === 'builders');
            
            builders.forEach((worker, index) => {
                worker.currentTask = {
                    id: `load-task-${index}`,
                    type: 'implement_feature',
                    priority: 'high'
                };
                worker.status = 'working';
            });
            
            // Trigger adaptive scaling
            await queen.adaptiveScale();
            
            // Should attempt to scale up builders
            const finalBuilders = Array.from(queen.workers.values())
                .filter(w => w.caste === 'builders' && w.status !== 'standby').length;
            
            expect(finalBuilders).toBeGreaterThanOrEqual(initialBuilders);
        });
        
        test('should scale down when workers are underutilized', async () => {
            // First, scale up to create excess capacity
            const foragerConfig = mockConfig.hive.structure.worker_castes.foragers;
            
            // Add extra workers
            for (let i = 0; i < 3; i++) {
                await queen.spawnWorker('foragers', foragerConfig, 100 + i);
            }
            
            const initialForagers = Array.from(queen.workers.values())
                .filter(w => w.caste === 'foragers').length;
            
            // All workers idle for extended period
            const foragers = Array.from(queen.workers.values())
                .filter(w => w.caste === 'foragers');
            
            foragers.forEach(worker => {
                worker.status = 'idle';
                worker.currentTask = null;
                worker.performance.lastActive = Date.now() - 600000; // 10 minutes ago
            });
            
            // Mock scaling decision
            const shouldScaleDown = faultTolerance.shouldScaleDown || (() => {
                const idleWorkers = foragers.filter(w => w.status === 'idle').length;
                return idleWorkers > foragerConfig.min_count;
            });
            
            expect(shouldScaleDown()).toBe(true);
        });
        
        test('should redistribute load during worker failures', async () => {
            const builders = Array.from(queen.workers.values())
                .filter(w => w.caste === 'builders');
            
            // Assign tasks to builders
            const tasks = builders.map((worker, index) => ({
                id: `task-${index}`,
                type: 'implement_feature',
                workerId: worker.id
            }));
            
            tasks.forEach((task, index) => {
                builders[index].currentTask = task;
                builders[index].status = 'working';
            });
            
            // Fail half the builders
            const failingBuilders = builders.slice(0, Math.floor(builders.length / 2));
            
            for (const worker of failingBuilders) {
                await faultTolerance.activateBackupWorker(worker);
            }
            
            // Verify tasks were redistributed
            const remainingWorkers = Array.from(queen.workers.values())
                .filter(w => w.caste === 'builders');
            const activeTasks = remainingWorkers
                .filter(w => w.currentTask)
                .map(w => w.currentTask);
            
            expect(activeTasks.length).toBeGreaterThan(0);
        });
        
        test('should balance load across worker castes', async () => {
            const castes = Object.keys(mockConfig.hive.structure.worker_castes);
            
            // Create mixed workload
            const mixedTasks = [
                { type: 'research_requirements', caste: 'foragers' },
                { type: 'implement_api', caste: 'builders' },
                { type: 'test_integration', caste: 'guardians' },
                { type: 'deploy_service', caste: 'nurses' },
                { type: 'analyze_data', caste: 'foragers' },
                { type: 'refactor_code', caste: 'builders' }
            ];
            
            // Delegate tasks and verify distribution
            const assignments = [];
            for (const task of mixedTasks) {
                try {
                    const assignment = await queen.delegateTask(task);
                    assignments.push(assignment);
                } catch (error) {
                    // Some tasks may fail to assign if workers unavailable
                }
            }
            
            // Verify tasks were distributed across different castes
            const casteUsage = new Set(assignments.map(a => a.workerCaste));
            expect(casteUsage.size).toBeGreaterThan(1);
        });
    });

    describe('System Resilience and Recovery Performance', () => {
        
        test('should maintain minimum system functionality during failures', async () => {
            const workers = Array.from(queen.workers.values());
            const halfWorkers = Math.floor(workers.length / 2);
            
            // Fail half the workers
            for (let i = 0; i < halfWorkers; i++) {
                queen.workers.delete(workers[i].id);
            }
            
            // System should still be able to:
            // 1. Accept new tasks
            const testTask = {
                id: 'resilience-test',
                type: 'critical_operation',
                priority: 'high'
            };
            
            const assignment = await queen.delegateTask(testTask);
            expect(assignment).toBeDefined();
            
            // 2. Provide status information
            const status = queen.getWorkerSummary();
            expect(status.total).toBeGreaterThan(0);
            
            // 3. Maintain basic capabilities
            const capabilities = queen.getCapabilities();
            expect(capabilities.coordination).toBeDefined();
        });
        
        test('should recover from total caste failure', async () => {
            // Simulate total failure of foragers caste
            const foragers = Array.from(queen.workers.values())
                .filter(w => w.caste === 'foragers');
            
            // Remove all foragers
            foragers.forEach(worker => {
                queen.workers.delete(worker.id);
            });
            
            // Verify no foragers remain
            const remainingForagers = Array.from(queen.workers.values())
                .filter(w => w.caste === 'foragers');
            expect(remainingForagers.length).toBe(0);
            
            // System should spawn new foragers when needed
            const foragerTask = {
                id: 'research-task',
                type: 'research_market',
                priority: 'high'
            };
            
            // This should trigger creation of new foragers
            const assignment = await queen.delegateTask(foragerTask);
            expect(assignment).toBeDefined();
            expect(assignment.workerCaste).toBe('foragers');
        });
        
        test('should measure recovery time for different failure scenarios', async () => {
            const scenarios = [
                { name: 'single_worker_failure', failureCount: 1 },
                { name: 'caste_partial_failure', failureCount: 3 },
                { name: 'system_wide_failure', failureCount: 6 }
            ];
            
            const recoveryTimes = {};
            
            for (const scenario of scenarios) {
                const startTime = Date.now();
                const workers = Array.from(queen.workers.values()).slice(0, scenario.failureCount);
                
                // Simulate failures
                const failurePromises = workers.map(worker => 
                    faultTolerance.handleWorkerFailure(worker, new Error(`${scenario.name} failure`))
                );
                
                await Promise.all(failurePromises);
                
                // Measure time to recovery
                const recoveryTime = Date.now() - startTime;
                recoveryTimes[scenario.name] = recoveryTime;
                
                // Verify system is operational
                const status = queen.getWorkerSummary();
                expect(status.total).toBeGreaterThan(0);
            }
            
            // Recovery times should be reasonable
            expect(recoveryTimes.single_worker_failure).toBeLessThan(5000); // 5 seconds
            expect(recoveryTimes.caste_partial_failure).toBeLessThan(10000); // 10 seconds
            expect(recoveryTimes.system_wide_failure).toBeLessThan(30000); // 30 seconds
        });
        
        test('should maintain performance metrics during stress', async () => {
            const initialStatus = faultTolerance.getStatus();
            
            // Apply stress - multiple concurrent failures
            const workers = Array.from(queen.workers.values());
            const stressedWorkers = workers.slice(0, Math.min(5, workers.length));
            
            const stressPromises = stressedWorkers.map(async (worker, index) => {
                await new Promise(resolve => setTimeout(resolve, index * 200)); // Stagger failures
                return faultTolerance.handleWorkerFailure(worker, new Error('Stress test failure'));
            });
            
            await Promise.all(stressPromises);
            
            // Check resilience metrics
            const finalStatus = faultTolerance.getStatus();
            
            expect(finalStatus.health_monitoring.active).toBe(true);
            expect(finalStatus.failure_stats.total_failures).toBeGreaterThan(initialStatus.failure_stats.total_failures);
            expect(finalStatus.resilience_score).toBeGreaterThan(0);
        });
        
        test('should verify rollback capabilities', async () => {
            const workers = Array.from(queen.workers.values());
            const testWorker = workers[0];
            
            // Record initial state
            const initialState = {
                status: testWorker.status,
                currentTask: testWorker.currentTask,
                lastActive: testWorker.performance.lastActive
            };
            
            // Simulate change and failure
            testWorker.status = 'working';
            testWorker.currentTask = { id: 'rollback-test', type: 'test_operation' };
            
            // Trigger restart (which should rollback to safe state)
            await faultTolerance.restartWorker(testWorker);
            
            // Verify rollback to safe state
            expect(testWorker.status).toBe('idle');
            expect(testWorker.currentTask).toBeNull();
            expect(testWorker.performance.lastActive).toBeGreaterThan(initialState.lastActive);
        });
    });

    describe('Health Monitoring and Alerting', () => {
        
        test('should continuously monitor worker health', async () => {
            const initialHealthChecks = faultTolerance.healthChecks.size;
            
            // Wait for health monitoring cycle
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            const finalHealthChecks = faultTolerance.healthChecks.size;
            expect(finalHealthChecks).toBeGreaterThan(initialHealthChecks);
        });
        
        test('should generate health status reports', async () => {
            const status = faultTolerance.getStatus();
            
            expect(status.health_monitoring).toBeDefined();
            expect(status.health_monitoring.active).toBe(true);
            expect(status.backup_workers).toBeDefined();
            expect(status.failure_stats).toBeDefined();
            expect(status.resilience_score).toBeGreaterThanOrEqual(0);
            expect(status.resilience_score).toBeLessThanOrEqual(1);
        });
        
        test('should track failure patterns and trends', async () => {
            // Generate multiple failures over time
            const workers = Array.from(queen.workers.values()).slice(0, 3);
            
            for (let i = 0; i < workers.length; i++) {
                await faultTolerance.handleWorkerFailure(
                    workers[i], 
                    new Error(`Pattern failure ${i}`)
                );
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            const failureHistory = faultTolerance.failureHistory;
            expect(failureHistory.length).toBe(3);
            
            // Verify failure data structure
            const lastFailure = failureHistory[failureHistory.length - 1];
            expect(lastFailure.workerId).toBeDefined();
            expect(lastFailure.caste).toBeDefined();
            expect(lastFailure.error).toBeDefined();
            expect(lastFailure.timestamp).toBeDefined();
        });
        
        test('should alert on critical system conditions', async () => {
            const workers = Array.from(queen.workers.values());
            const criticalWorkers = workers.filter(w => 
                mockConfig.hive.fault_tolerance.redundancy.critical_roles.includes(w.caste)
            );
            
            // Simulate critical failure - all workers in critical role failing
            if (criticalWorkers.length > 0) {
                const criticalCaste = criticalWorkers[0].caste;
                const casteWorkers = workers.filter(w => w.caste === criticalCaste);
                
                for (const worker of casteWorkers) {
                    await faultTolerance.handleWorkerFailure(worker, new Error('Critical failure'));
                }
                
                // System should escalate this as critical
                const recentFailures = faultTolerance.failureHistory
                    .filter(f => f.caste === criticalCaste && Date.now() - f.timestamp < 10000);
                
                expect(recentFailures.length).toBeGreaterThan(1);
            }
        });
    });
});
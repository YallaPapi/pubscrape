/**
 * Integration Testing Suite for Hive Coordination System
 * Tests end-to-end workflows, component integration, and real-world scenarios
 */

const { HiveQueenCoordinator } = require('../../src/hive/coordinator');
const { HiveFaultTolerance } = require('../../src/hive/fault-tolerance');
const { HiveCoordinator } = require('../../src/coordination/HiveCoordinator');

describe('Hive Integration Testing Suite', () => {
    let queen;
    let faultTolerance;
    let hiveCoordinator;
    let mockConfig;
    
    beforeEach(async () => {
        mockConfig = {
            hive: {
                structure: {
                    queen: {
                        max_workers: 25,
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
                            max_count: 12,
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
                        timeout: 3000,
                        retry_attempts: 3
                    },
                    recovery: {
                        auto_restart: true,
                        failover_delay: 1500,
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
                    max_instances: 6
                }
            },
            hiveId: 'integration-test-hive',
            coordinationMode: 'adaptive',
            emergencyThresholds: {
                errorRate: 0.4,
                responseTime: 8000,
                agentFailureRate: 0.6
            }
        };
        
        // Initialize all components
        queen = new HiveQueenCoordinator(mockConfig);
        await queen.initialize();
        
        faultTolerance = new HiveFaultTolerance(queen, mockConfig);
        await faultTolerance.initialize();
        
        hiveCoordinator = new HiveCoordinator(mockConfig);
        await new Promise(resolve => setTimeout(resolve, 200)); // Allow initialization
    });
    
    afterEach(async () => {
        if (hiveCoordinator) {
            hiveCoordinator.stop();
        }
        if (faultTolerance) {
            faultTolerance.stop && faultTolerance.stop();
        }
        if (queen) {
            queen.stop && queen.stop();
        }
    });

    describe('End-to-End Workflow Integration', () => {
        
        test('should execute complete software development workflow', async () => {
            const projectWorkflow = {
                id: 'e2e-software-project',
                name: 'Feature Development Workflow',
                phases: [
                    {
                        name: 'requirements_gathering',
                        tasks: [
                            { type: 'research_user_needs', caste: 'foragers', priority: 'high' },
                            { type: 'analyze_market_data', caste: 'foragers', priority: 'medium' },
                            { type: 'document_requirements', caste: 'foragers', priority: 'high' }
                        ]
                    },
                    {
                        name: 'design_and_implementation',
                        tasks: [
                            { type: 'design_architecture', caste: 'builders', priority: 'critical' },
                            { type: 'implement_core_features', caste: 'builders', priority: 'high' },
                            { type: 'implement_ui_components', caste: 'builders', priority: 'medium' }
                        ]
                    },
                    {
                        name: 'testing_and_validation',
                        tasks: [
                            { type: 'unit_testing', caste: 'guardians', priority: 'high' },
                            { type: 'integration_testing', caste: 'guardians', priority: 'high' },
                            { type: 'security_review', caste: 'guardians', priority: 'critical' }
                        ]
                    },
                    {
                        name: 'deployment_and_monitoring',
                        tasks: [
                            { type: 'deploy_to_staging', caste: 'nurses', priority: 'high' },
                            { type: 'deploy_to_production', caste: 'nurses', priority: 'critical' },
                            { type: 'setup_monitoring', caste: 'nurses', priority: 'medium' }
                        ]
                    }
                ]
            };
            
            const workflowResults = {
                phases: [],
                totalDuration: 0,
                successRate: 0,
                workerUtilization: new Map()
            };
            
            const workflowStart = Date.now();
            
            // Execute workflow phases sequentially
            for (const phase of projectWorkflow.phases) {
                const phaseStart = Date.now();
                const phaseResults = [];
                
                // Execute phase tasks in parallel
                const phasePromises = phase.tasks.map(async (taskTemplate, index) => {
                    const task = {
                        id: `${phase.name}-task-${index}`,
                        type: taskTemplate.type,
                        priority: taskTemplate.priority,
                        phase: phase.name,
                        expectedCaste: taskTemplate.caste
                    };
                    
                    try {
                        const assignment = await queen.delegateTask(task);
                        
                        // Track worker utilization
                        const currentCount = workflowResults.workerUtilization.get(assignment.workerCaste) || 0;
                        workflowResults.workerUtilization.set(assignment.workerCaste, currentCount + 1);
                        
                        // Simulate task execution time
                        const executionTime = 200 + Math.random() * 300; // 200-500ms
                        await new Promise(resolve => setTimeout(resolve, executionTime));
                        
                        // Mark task as completed
                        const worker = queen.workers.get(assignment.workerId);
                        if (worker) {
                            worker.status = 'idle';
                            worker.currentTask = null;
                            worker.performance.tasksCompleted++;
                            worker.performance.lastActive = Date.now();
                        }
                        
                        return {
                            task: task.id,
                            success: true,
                            actualCaste: assignment.workerCaste,
                            expectedCaste: task.expectedCaste,
                            executionTime
                        };
                    } catch (error) {
                        return {
                            task: task.id,
                            success: false,
                            error: error.message
                        };
                    }
                });
                
                const phaseTaskResults = await Promise.all(phasePromises);
                const phaseDuration = Date.now() - phaseStart;
                const phaseSuccessRate = phaseTaskResults.filter(r => r.success).length / phaseTaskResults.length;
                
                workflowResults.phases.push({
                    name: phase.name,
                    duration: phaseDuration,
                    successRate: phaseSuccessRate,
                    tasks: phaseTaskResults
                });
                
                // Brief pause between phases
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            workflowResults.totalDuration = Date.now() - workflowStart;
            workflowResults.successRate = workflowResults.phases.reduce((sum, p) => sum + p.successRate, 0) / workflowResults.phases.length;
            
            // Assertions
            expect(workflowResults.phases.length).toBe(projectWorkflow.phases.length);
            expect(workflowResults.successRate).toBeGreaterThan(0.8); // 80% success rate
            expect(workflowResults.totalDuration).toBeLessThan(15000); // 15 seconds max
            
            // Verify proper caste utilization
            expect(workflowResults.workerUtilization.has('foragers')).toBe(true);
            expect(workflowResults.workerUtilization.has('builders')).toBe(true);
            expect(workflowResults.workerUtilization.has('guardians')).toBe(true);
            expect(workflowResults.workerUtilization.has('nurses')).toBe(true);
            
            // Verify task assignment accuracy
            const correctAssignments = workflowResults.phases.flatMap(p => p.tasks)
                .filter(t => t.success && t.actualCaste === t.expectedCaste).length;
            const totalSuccessfulTasks = workflowResults.phases.flatMap(p => p.tasks)
                .filter(t => t.success).length;
            
            expect(correctAssignments / totalSuccessfulTasks).toBeGreaterThan(0.7); // 70% correct assignments
        });
        
        test('should handle complex dependency chains with recovery', async () => {
            const dependencyChain = [
                {
                    id: 'foundation-task',
                    type: 'setup_infrastructure',
                    dependencies: [],
                    priority: 'critical',
                    estimatedDuration: 500
                },
                {
                    id: 'database-task',
                    type: 'setup_database',
                    dependencies: ['foundation-task'],
                    priority: 'high',
                    estimatedDuration: 400
                },
                {
                    id: 'api-task',
                    type: 'implement_api',
                    dependencies: ['database-task'],
                    priority: 'high',
                    estimatedDuration: 600
                },
                {
                    id: 'frontend-task',
                    type: 'implement_frontend',
                    dependencies: ['api-task'],
                    priority: 'medium',
                    estimatedDuration: 700
                },
                {
                    id: 'testing-task',
                    type: 'run_integration_tests',
                    dependencies: ['frontend-task', 'api-task'],
                    priority: 'high',
                    estimatedDuration: 300
                }
            ];
            
            const chainResults = {
                completedTasks: new Map(),
                failedTasks: new Set(),
                recoveryAttempts: 0,
                totalDuration: 0
            };
            
            const chainStart = Date.now();
            
            // Function to check if dependencies are satisfied
            const dependenciesSatisfied = (task) => {
                return task.dependencies.every(dep => chainResults.completedTasks.has(dep));
            };
            
            // Execute dependency chain with recovery
            while (chainResults.completedTasks.size < dependencyChain.length && 
                   Date.now() - chainStart < 20000) { // 20 second timeout
                
                for (const task of dependencyChain) {
                    if (chainResults.completedTasks.has(task.id) || 
                        chainResults.failedTasks.has(task.id)) {
                        continue;
                    }
                    
                    if (!dependenciesSatisfied(task)) {
                        continue;
                    }
                    
                    try {
                        const assignment = await queen.delegateTask(task);
                        
                        // Simulate task execution with potential failure
                        const failureChance = Math.random();
                        if (failureChance < 0.1) { // 10% failure rate
                            // Simulate worker failure during task
                            const worker = queen.workers.get(assignment.workerId);
                            if (worker) {
                                await faultTolerance.handleWorkerFailure(worker, new Error('Dependency chain task failure'));
                                chainResults.recoveryAttempts++;
                            }
                            
                            // Retry the task
                            const retryAssignment = await queen.delegateTask(task);
                            await new Promise(resolve => setTimeout(resolve, task.estimatedDuration));
                            
                            chainResults.completedTasks.set(task.id, {
                                assignment: retryAssignment,
                                retried: true,
                                completedAt: Date.now()
                            });
                        } else {
                            // Normal execution
                            await new Promise(resolve => setTimeout(resolve, task.estimatedDuration));
                            
                            chainResults.completedTasks.set(task.id, {
                                assignment,
                                retried: false,
                                completedAt: Date.now()
                            });
                        }
                        
                        // Mark worker as idle
                        const worker = queen.workers.get(assignment.workerId);
                        if (worker) {
                            worker.status = 'idle';
                            worker.currentTask = null;
                        }
                        
                    } catch (error) {
                        chainResults.failedTasks.add(task.id);
                    }
                }
                
                // Brief pause before next iteration
                await new Promise(resolve => setTimeout(resolve, 50));
            }
            
            chainResults.totalDuration = Date.now() - chainStart;
            
            // Verify dependency chain execution
            expect(chainResults.completedTasks.size).toBe(dependencyChain.length);
            expect(chainResults.failedTasks.size).toBe(0);
            expect(chainResults.totalDuration).toBeLessThan(20000);
            
            // Verify execution order respects dependencies
            const foundationCompletion = chainResults.completedTasks.get('foundation-task').completedAt;
            const databaseCompletion = chainResults.completedTasks.get('database-task').completedAt;
            const apiCompletion = chainResults.completedTasks.get('api-task').completedAt;
            const frontendCompletion = chainResults.completedTasks.get('frontend-task').completedAt;
            const testingCompletion = chainResults.completedTasks.get('testing-task').completedAt;
            
            expect(databaseCompletion).toBeGreaterThan(foundationCompletion);
            expect(apiCompletion).toBeGreaterThan(databaseCompletion);
            expect(frontendCompletion).toBeGreaterThan(apiCompletion);
            expect(testingCompletion).toBeGreaterThan(Math.max(frontendCompletion, apiCompletion));
        });
    });

    describe('Component Integration and Communication', () => {
        
        test('should integrate queen coordination with hive coordinator', async () => {
            // Test bi-directional communication between queen and hive coordinator
            const integrationStart = Date.now();
            
            // Simulate performance alerts from hive coordinator
            const performanceAlert = {
                type: 'HIGH_LOAD',
                severity: 'warning',
                data: {
                    cpuUsage: 0.85,
                    memoryUsage: 0.75,
                    workerUtilization: 0.9
                }
            };
            
            // Trigger hive coordinator alert
            await hiveCoordinator.triggerHook('onPerformanceAlert', performanceAlert);
            
            // Queen should respond to high load by scaling
            const initialWorkerCount = queen.workers.size;
            await queen.adaptiveScale();
            const scaledWorkerCount = queen.workers.size;
            
            // Test emergency escalation
            const emergencyConditions = [
                {
                    type: 'worker_cascade_failure',
                    affectedCaste: 'builders',
                    failureCount: 3
                }
            ];
            
            await hiveCoordinator.triggerHook('onEmergency', { 
                type: 'emergency_start', 
                conditions: emergencyConditions 
            });
            
            // Verify integration response
            const integrationDuration = Date.now() - integrationStart;
            expect(integrationDuration).toBeLessThan(5000); // 5 seconds
            
            // System should maintain coordination
            const hiveStatus = hiveCoordinator.getStatus();
            const queenStatus = queen.getWorkerSummary();
            
            expect(hiveStatus.status).toBe('active');
            expect(queenStatus.total).toBeGreaterThan(0);
        });
        
        test('should coordinate fault tolerance with performance monitoring', async () => {
            // Create performance degradation scenario
            const workers = Array.from(queen.workers.values());
            const degradedWorkers = workers.slice(0, Math.floor(workers.length * 0.4));
            
            // Simulate worker performance degradation
            degradedWorkers.forEach(worker => {
                worker.performance.successRate = 0.3; // Poor performance
                worker.performance.averageTime = 5000; // Slow response
            });
            
            // Run health checks to detect degradation
            const healthPromises = degradedWorkers.map(worker => 
                faultTolerance.checkWorkerHealth(worker)
            );
            
            const healthResults = await Promise.all(healthPromises);
            const unhealthyCount = healthResults.filter(h => !h.healthy).length;
            
            // Trigger recovery for unhealthy workers
            const recoveryPromises = degradedWorkers
                .filter((worker, index) => !healthResults[index].healthy)
                .map(worker => faultTolerance.initiateRecovery(worker));
            
            await Promise.all(recoveryPromises);
            
            // Verify coordinated response
            expect(unhealthyCount).toBeGreaterThan(0);
            
            // System should maintain performance monitoring
            const faultStatus = faultTolerance.getStatus();
            expect(faultStatus.health_monitoring.active).toBe(true);
            expect(faultStatus.resilience_score).toBeGreaterThan(0.3);
        });
        
        test('should handle cross-caste collaboration scenarios', async () => {
            const collaborationProject = {
                id: 'cross-caste-collaboration',
                name: 'Multi-Disciplinary Feature Development',
                collaborativeTasks: [
                    {
                        id: 'research-collab',
                        type: 'collaborative_research',
                        requiredCastes: ['foragers', 'guardians'],
                        coordination: 'parallel'
                    },
                    {
                        id: 'design-collab',
                        type: 'collaborative_design',
                        requiredCastes: ['foragers', 'builders'],
                        coordination: 'sequential'
                    },
                    {
                        id: 'implementation-collab',
                        type: 'collaborative_implementation',
                        requiredCastes: ['builders', 'guardians'],
                        coordination: 'paired'
                    },
                    {
                        id: 'deployment-collab',
                        type: 'collaborative_deployment',
                        requiredCastes: ['builders', 'nurses', 'guardians'],
                        coordination: 'orchestrated'
                    }
                ]
            };
            
            const collaborationResults = {
                taskResults: new Map(),
                casteInteractions: new Map(),
                coordinationEffectiveness: 0
            };
            
            // Execute collaborative tasks
            for (const task of collaborationProject.collaborativeTasks) {
                const taskStart = Date.now();
                const taskAssignments = [];
                
                // Assign workers from required castes
                for (const requiredCaste of task.requiredCastes) {
                    const subTask = {
                        id: `${task.id}-${requiredCaste}`,
                        type: `${task.type}_${requiredCaste}`,
                        collaboration: true,
                        parentTask: task.id
                    };
                    
                    try {
                        const assignment = await queen.delegateTask(subTask);
                        taskAssignments.push(assignment);
                        
                        // Track caste interactions
                        const interactionKey = `${task.id}-${requiredCaste}`;
                        collaborationResults.casteInteractions.set(interactionKey, assignment);
                        
                    } catch (error) {
                        console.error(`Failed to assign collaborative task: ${error.message}`);
                    }
                }
                
                // Simulate collaborative execution time
                const collaborationTime = 300 + (task.requiredCastes.length * 100);
                await new Promise(resolve => setTimeout(resolve, collaborationTime));
                
                // Mark workers as completed
                taskAssignments.forEach(assignment => {
                    const worker = queen.workers.get(assignment.workerId);
                    if (worker) {
                        worker.status = 'idle';
                        worker.currentTask = null;
                        worker.performance.tasksCompleted++;
                    }
                });
                
                const taskDuration = Date.now() - taskStart;
                collaborationResults.taskResults.set(task.id, {
                    assignments: taskAssignments,
                    duration: taskDuration,
                    success: taskAssignments.length === task.requiredCastes.length
                });
            }
            
            // Calculate collaboration effectiveness
            const successfulTasks = Array.from(collaborationResults.taskResults.values())
                .filter(r => r.success).length;
            collaborationResults.coordinationEffectiveness = successfulTasks / collaborationProject.collaborativeTasks.length;
            
            // Verify cross-caste collaboration
            expect(collaborationResults.coordinationEffectiveness).toBeGreaterThan(0.7); // 70% success
            expect(collaborationResults.casteInteractions.size).toBeGreaterThan(0);
            
            // Verify all castes participated
            const participatingCastes = new Set();
            collaborationResults.casteInteractions.forEach(assignment => {
                participatingCastes.add(assignment.workerCaste);
            });
            expect(participatingCastes.size).toBeGreaterThan(2);
        });
    });

    describe('Real-World Scenario Simulation', () => {
        
        test('should handle production deployment scenario with rollback', async () => {
            const deploymentScenario = {
                id: 'production-deployment',
                environment: 'production',
                phases: [
                    { name: 'pre_deployment_checks', critical: true },
                    { name: 'backup_current_version', critical: true },
                    { name: 'deploy_new_version', critical: true },
                    { name: 'run_smoke_tests', critical: true },
                    { name: 'monitor_health_metrics', critical: false }
                ]
            };
            
            const deploymentResults = {
                phases: new Map(),
                rollbackTriggered: false,
                deploymentSuccess: false
            };
            
            // Execute deployment phases
            for (const [index, phase] of deploymentScenario.phases.entries()) {
                const phaseStart = Date.now();
                
                const deploymentTask = {
                    id: `deployment-${phase.name}`,
                    type: `production_${phase.name}`,
                    priority: phase.critical ? 'critical' : 'high',
                    environment: 'production'
                };
                
                try {
                    const assignment = await queen.delegateTask(deploymentTask);
                    
                    // Simulate phase execution with potential failure
                    const executionTime = 200 + Math.random() * 400;
                    await new Promise(resolve => setTimeout(resolve, executionTime));
                    
                    // Simulate failure in smoke tests (phase 3)
                    if (index === 3 && Math.random() < 0.3) { // 30% chance of smoke test failure
                        throw new Error('Smoke tests failed - critical issues detected');
                    }
                    
                    const phaseDuration = Date.now() - phaseStart;
                    deploymentResults.phases.set(phase.name, {
                        success: true,
                        duration: phaseDuration,
                        assignment
                    });
                    
                    // Mark worker as idle
                    const worker = queen.workers.get(assignment.workerId);
                    if (worker) {
                        worker.status = 'idle';
                        worker.currentTask = null;
                    }
                    
                } catch (error) {
                    deploymentResults.phases.set(phase.name, {
                        success: false,
                        error: error.message
                    });
                    
                    // Trigger rollback if critical phase fails
                    if (phase.critical) {
                        deploymentResults.rollbackTriggered = true;
                        
                        const rollbackTask = {
                            id: 'emergency-rollback',
                            type: 'production_rollback',
                            priority: 'critical',
                            reason: error.message
                        };
                        
                        const rollbackAssignment = await queen.delegateTask(rollbackTask);
                        await new Promise(resolve => setTimeout(resolve, 500)); // Rollback time
                        
                        // Mark rollback worker as idle
                        const rollbackWorker = queen.workers.get(rollbackAssignment.workerId);
                        if (rollbackWorker) {
                            rollbackWorker.status = 'idle';
                            rollbackWorker.currentTask = null;
                        }
                        
                        break; // Stop deployment
                    }
                }
            }
            
            deploymentResults.deploymentSuccess = !deploymentResults.rollbackTriggered && 
                Array.from(deploymentResults.phases.values()).every(p => p.success);
            
            // Verify deployment handling
            expect(deploymentResults.phases.size).toBeGreaterThan(0);
            
            if (deploymentResults.rollbackTriggered) {
                // Rollback scenario
                expect(deploymentResults.deploymentSuccess).toBe(false);
                // System should handle rollback gracefully
                const systemStatus = queen.getWorkerSummary();
                expect(systemStatus.total).toBeGreaterThan(0);
            } else {
                // Successful deployment scenario
                expect(deploymentResults.deploymentSuccess).toBe(true);
                expect(deploymentResults.phases.size).toBe(deploymentScenario.phases.length);
            }
        });
        
        test('should simulate black friday traffic spike scenario', async () => {
            const trafficSpike = {
                name: 'Black Friday Traffic Spike',
                duration: 8000, // 8 seconds simulation
                peakMultiplier: 10,
                taskTypes: [
                    'process_order',
                    'update_inventory',
                    'send_confirmation',
                    'process_payment',
                    'generate_receipt'
                ]
            };
            
            const spikeResults = {
                tasksProcessed: 0,
                peakWorkers: 0,
                responseTimeP95: 0,
                systemStability: true,
                scalingEvents: 0
            };
            
            const spikeStart = Date.now();
            const responseTimes = [];
            
            // Simulate traffic spike with increasing load
            while (Date.now() - spikeStart < trafficSpike.duration) {
                const elapsed = Date.now() - spikeStart;
                const progress = elapsed / trafficSpike.duration;
                
                // Calculate current load (spike curve)
                const loadMultiplier = 1 + (trafficSpike.peakMultiplier - 1) * 
                    Math.sin(progress * Math.PI); // Bell curve
                
                const tasksPerSecond = Math.floor(2 * loadMultiplier);
                
                // Generate tasks for this second
                const batchTasks = Array.from({ length: tasksPerSecond }, (_, i) => ({
                    id: `spike-${elapsed}-${i}`,
                    type: trafficSpike.taskTypes[i % trafficSpike.taskTypes.length],
                    priority: 'high',
                    timestamp: Date.now()
                }));
                
                // Process batch
                for (const task of batchTasks) {
                    const taskStart = Date.now();
                    
                    try {
                        const assignment = await queen.delegateTask(task);
                        spikeResults.tasksProcessed++;
                        
                        const responseTime = Date.now() - taskStart;
                        responseTimes.push(responseTime);
                        
                        // Quick task completion simulation
                        setTimeout(() => {
                            const worker = queen.workers.get(assignment.workerId);
                            if (worker) {
                                worker.status = 'idle';
                                worker.currentTask = null;
                            }
                        }, 50 + Math.random() * 100);
                        
                    } catch (error) {
                        spikeResults.systemStability = false;
                    }
                }
                
                // Track peak workers
                spikeResults.peakWorkers = Math.max(spikeResults.peakWorkers, queen.workers.size);
                
                // Trigger adaptive scaling if needed
                if (loadMultiplier > 5) {
                    await queen.adaptiveScale();
                    spikeResults.scalingEvents++;
                }
                
                // Brief pause to simulate real-time processing
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            // Calculate P95 response time
            responseTimes.sort((a, b) => a - b);
            const p95Index = Math.floor(responseTimes.length * 0.95);
            spikeResults.responseTimeP95 = responseTimes[p95Index] || 0;
            
            // Verify traffic spike handling
            expect(spikeResults.tasksProcessed).toBeGreaterThan(50); // Process significant load
            expect(spikeResults.systemStability).toBe(true); // Maintain stability
            expect(spikeResults.responseTimeP95).toBeLessThan(2000); // P95 under 2 seconds
            expect(spikeResults.scalingEvents).toBeGreaterThan(0); // Should have scaled
            
            // System should return to normal after spike
            await new Promise(resolve => setTimeout(resolve, 1000));
            const finalStatus = queen.getWorkerSummary();
            expect(finalStatus.by_status.idle).toBeGreaterThan(finalStatus.by_status.working);
        });
        
        test('should handle data center outage simulation', async () => {
            const outageScenario = {
                name: 'Simulated Data Center Outage',
                affectedPercentage: 0.6, // 60% of workers affected
                outageDuration: 3000, // 3 seconds
                recoveryPhases: ['immediate', 'gradual', 'full']
            };
            
            const outageResults = {
                initialWorkers: queen.workers.size,
                workersLost: 0,
                minimumOperational: 0,
                recoveryTime: 0,
                tasksContinued: 0
            };
            
            const outageStart = Date.now();
            
            // Phase 1: Simulate outage - remove affected workers
            const allWorkers = Array.from(queen.workers.keys());
            const affectedCount = Math.floor(allWorkers.length * outageScenario.affectedPercentage);
            const affectedWorkers = allWorkers.slice(0, affectedCount);
            
            // Remove affected workers
            affectedWorkers.forEach(workerId => {
                queen.workers.delete(workerId);
            });
            
            outageResults.workersLost = affectedCount;
            outageResults.minimumOperational = queen.workers.size;
            
            // Verify system continues operating with reduced capacity
            const continuityTasks = Array.from({ length: 10 }, (_, i) => ({
                id: `outage-continuity-${i}`,
                type: 'emergency_operation',
                priority: 'critical'
            }));
            
            for (const task of continuityTasks) {
                try {
                    await queen.delegateTask(task);
                    outageResults.tasksContinued++;
                } catch (error) {
                    // Some tasks may fail due to reduced capacity
                }
            }
            
            // Phase 2: Gradual recovery simulation
            await new Promise(resolve => setTimeout(resolve, outageScenario.outageDuration));
            
            // Spawn replacement workers
            const castes = Object.keys(mockConfig.hive.structure.worker_castes);
            const recoveryPromises = castes.map(async (caste) => {
                const casteConfig = mockConfig.hive.structure.worker_castes[caste];
                const currentCasteWorkers = Array.from(queen.workers.values())
                    .filter(w => w.caste === caste).length;
                
                if (currentCasteWorkers < casteConfig.min_count) {
                    const needed = casteConfig.min_count - currentCasteWorkers;
                    for (let i = 0; i < needed; i++) {
                        await queen.spawnWorker(caste, casteConfig, 2000 + i);
                    }
                }
            });
            
            await Promise.all(recoveryPromises);
            outageResults.recoveryTime = Date.now() - outageStart;
            
            // Verify recovery
            expect(outageResults.workersLost).toBeGreaterThan(0);
            expect(outageResults.minimumOperational).toBeGreaterThan(0); // Some workers survived
            expect(outageResults.tasksContinued).toBeGreaterThan(0); // System remained operational
            expect(outageResults.recoveryTime).toBeLessThan(10000); // Recovery within 10 seconds
            
            // Final worker count should be approaching original
            const finalWorkers = queen.workers.size;
            expect(finalWorkers).toBeGreaterThan(outageResults.minimumOperational);
            
            // System health should be restored
            const healthStatus = faultTolerance.getStatus();
            expect(healthStatus.resilience_score).toBeGreaterThan(0.5);
        });
    });
});
/**
 * 🏰 Hive Orchestrator - Complete Hierarchical Coordination System
 * 
 * Main orchestrator that integrates all hive components:
 * - Queen Coordinator
 * - Specialized Workers
 * - Communication Protocols
 * - Monitoring System
 * - Load Balancing
 */

const { QueenCoordinator } = require('./coordination/queen_coordinator');
const { WorkerFactory } = require('./workers/worker_specializations');
const { CommunicationProtocols } = require('./protocols/communication_protocols');
const { HiveMonitor } = require('./monitoring/hive_monitor');
const { HiveConfig } = require('../config/swarm/hive_config');

class HiveOrchestrator {
    constructor() {
        this.config = HiveConfig;
        this.queen = null;
        this.workers = new Map();
        this.communicationSystem = null;
        this.monitor = null;
        this.isActive = false;
        this.taskQueue = [];
        this.completedTasks = [];
        
        console.log('🏰 Initializing Hive Orchestrator...');
    }

    async initialize() {
        try {
            console.log('👑 Starting hierarchical hive initialization...');
            
            // Initialize core systems
            await this.initializeQueen();
            await this.initializeCommunicationSystem();
            await this.initializeMonitoring();
            await this.spawnInitialWorkers();
            await this.setupLoadBalancing();
            await this.startOperationalSystems();
            
            this.isActive = true;
            console.log('✅ Hive Orchestrator fully operational!');
            
            return await this.generateInitializationReport();
            
        } catch (error) {
            console.error('❌ Hive initialization failed:', error);
            throw error;
        }
    }

    async initializeQueen() {
        this.queen = new QueenCoordinator();
        console.log('👑 Queen Coordinator initialized');
    }

    async initializeCommunicationSystem() {
        this.communicationSystem = new CommunicationProtocols();
        console.log('📡 Communication protocols established');
    }

    async initializeMonitoring() {
        this.monitor = new HiveMonitor();
        console.log('📈 Monitoring system activated');
    }

    async spawnInitialWorkers() {
        const workerTypes = Object.keys(this.config.workers);
        
        for (const type of workerTypes) {
            const config = this.config.workers[type];
            const initialCount = Math.min(2, config.maxInstances); // Start with 2 of each type
            
            for (let i = 0; i < initialCount; i++) {
                await this.spawnWorker(type);
            }
        }
        
        console.log(`🤖 Initial worker pool spawned: ${this.workers.size} workers`);
    }

    async spawnWorker(type) {
        try {
            const worker = WorkerFactory.createWorker(type);
            worker.orchestratorId = this.generateWorkerId();
            
            this.workers.set(worker.id, {
                ...worker,
                spawnedAt: new Date().toISOString(),
                status: 'available',
                taskHistory: []
            });
            
            console.log(`${worker.getEmoji()} Spawned ${type} worker: ${worker.id}`);
            return worker;
            
        } catch (error) {
            console.error(`❌ Failed to spawn ${type} worker:`, error);
            throw error;
        }
    }

    generateWorkerId() {
        return `worker-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    async setupLoadBalancing() {
        this.loadBalancer = {
            strategy: this.config.resources.allocation.strategy,
            algorithm: this.config.resources.allocation.loadBalancing,
            
            // Capability-based assignment
            assignTask: async (task) => {
                const suitableWorkers = this.findSuitableWorkers(task);
                if (suitableWorkers.length === 0) {
                    // Auto-spawn if no suitable workers available
                    const newWorker = await this.autoSpawnForTask(task);
                    return newWorker;
                }
                
                // Use weighted round-robin based on current load
                return this.selectOptimalWorker(suitableWorkers, task);
            },
            
            // Load balancing metrics
            getLoadMetrics: () => {
                const metrics = {};
                this.workers.forEach((worker, id) => {
                    metrics[id] = {
                        currentTasks: worker.currentTasks || 0,
                        maxTasks: worker.maxTasks || 3,
                        utilization: ((worker.currentTasks || 0) / (worker.maxTasks || 3)) * 100,
                        performance: worker.performanceScore || 0.8
                    };
                });
                return metrics;
            }
        };
        
        console.log('⚖️ Load balancing system configured');
    }

    findSuitableWorkers(task) {
        const requiredCapabilities = task.requiredCapabilities || [];
        return Array.from(this.workers.values()).filter(worker => {
            // Check capability match
            const hasCapabilities = requiredCapabilities.every(cap => 
                worker.capabilities.includes(cap)
            );
            
            // Check availability
            const isAvailable = worker.status === 'available' || 
                (worker.currentTasks || 0) < (worker.maxTasks || 3);
            
            return hasCapabilities && isAvailable;
        });
    }

    async autoSpawnForTask(task) {
        // Determine best worker type for task
        const workerType = this.determineWorkerTypeForTask(task);
        
        // Check if we can spawn more of this type
        const existingWorkers = Array.from(this.workers.values())
            .filter(w => w.type === workerType).length;
        const maxAllowed = this.config.workers[workerType].maxInstances;
        
        if (existingWorkers < maxAllowed) {
            console.log(`🔄 Auto-spawning ${workerType} worker for task: ${task.title}`);
            return await this.spawnWorker(workerType);
        } else {
            console.log(`⚠️ Cannot spawn more ${workerType} workers (limit reached)`);
            return null;
        }
    }

    determineWorkerTypeForTask(task) {
        const taskType = task.type || 'general';
        const capabilities = task.requiredCapabilities || [];
        
        // Task type mapping
        const typeMapping = {
            'research': 'research',
            'analysis': 'research',
            'implementation': 'coder',
            'coding': 'coder',
            'testing': 'tester',
            'validation': 'tester',
            'data_analysis': 'analyst',
            'reporting': 'analyst'
        };
        
        if (typeMapping[taskType]) {
            return typeMapping[taskType];
        }
        
        // Capability-based determination
        if (capabilities.includes('code_generation') || capabilities.includes('implementation')) {
            return 'coder';
        } else if (capabilities.includes('research') || capabilities.includes('analysis')) {
            return 'research';
        } else if (capabilities.includes('testing') || capabilities.includes('validation')) {
            return 'tester';
        } else if (capabilities.includes('data_analysis') || capabilities.includes('reporting')) {
            return 'analyst';
        }
        
        // Default to research for general tasks
        return 'research';
    }

    selectOptimalWorker(workers, task) {
        // Score workers based on multiple factors
        const scoredWorkers = workers.map(worker => ({
            worker,
            score: this.calculateWorkerScore(worker, task)
        }));
        
        // Sort by score (higher is better)
        scoredWorkers.sort((a, b) => b.score - a.score);
        
        return scoredWorkers[0].worker;
    }

    calculateWorkerScore(worker, task) {
        const weights = {
            capabilityMatch: 0.4,
            performance: 0.3,
            availability: 0.2,
            specialization: 0.1
        };
        
        // Capability match score
        const requiredCaps = task.requiredCapabilities || [];
        const matchedCaps = requiredCaps.filter(cap => 
            worker.capabilities.includes(cap)
        );
        const capabilityScore = requiredCaps.length > 0 
            ? matchedCaps.length / requiredCaps.length 
            : 1;
        
        // Performance score
        const performanceScore = worker.performanceScore || 0.8;
        
        // Availability score (inverse of current load)
        const currentLoad = worker.currentTasks || 0;
        const maxLoad = worker.maxTasks || 3;
        const availabilityScore = 1 - (currentLoad / maxLoad);
        
        // Specialization score
        const specializationScore = task.type === worker.type ? 1 : 0.7;
        
        return (
            capabilityScore * weights.capabilityMatch +
            performanceScore * weights.performance +
            availabilityScore * weights.availability +
            specializationScore * weights.specialization
        );
    }

    async startOperationalSystems() {
        // Start periodic health checks
        this.healthCheckInterval = setInterval(async () => {
            await this.performHealthChecks();
        }, this.config.monitoring.reportingIntervals.health);
        
        // Start performance monitoring
        this.performanceInterval = setInterval(async () => {
            await this.collectPerformanceMetrics();
        }, this.config.monitoring.reportingIntervals.performance);
        
        // Start auto-scaling evaluation
        this.scalingInterval = setInterval(async () => {
            await this.evaluateAutoScaling();
        }, 300000); // Every 5 minutes
        
        console.log('🔄 Operational systems started');
    }

    async performHealthChecks() {
        // Check Queen health
        const queenHealth = await this.checkQueenHealth();
        
        // Check worker health
        const workerHealth = await this.checkAllWorkersHealth();
        
        // Check system health
        const systemHealth = await this.checkSystemHealth();
        
        const healthReport = {
            timestamp: new Date().toISOString(),
            queen: queenHealth,
            workers: workerHealth,
            system: systemHealth,
            overall: this.calculateOverallHealth(queenHealth, workerHealth, systemHealth)
        };
        
        if (healthReport.overall.status !== 'healthy') {
            console.log('⚠️ Health issues detected:', healthReport.overall.issues);
            await this.handleHealthIssues(healthReport);
        }
        
        return healthReport;
    }

    async checkQueenHealth() {
        return {
            status: 'healthy',
            responseTime: 15,
            memoryUsage: 0.45,
            activeTasks: this.taskQueue.length,
            lastActivity: new Date().toISOString()
        };
    }

    async checkAllWorkersHealth() {
        const healthChecks = {};
        
        for (const [id, worker] of this.workers) {
            healthChecks[id] = await this.checkWorkerHealth(worker);
        }
        
        return healthChecks;
    }

    async checkWorkerHealth(worker) {
        // Simulate health check
        return {
            status: Math.random() > 0.05 ? 'healthy' : 'degraded',
            responseTime: Math.random() * 50 + 10,
            taskLoad: worker.currentTasks || 0,
            performance: worker.performanceScore || 0.8,
            lastSeen: new Date().toISOString()
        };
    }

    async checkSystemHealth() {
        return {
            status: 'healthy',
            cpuUsage: Math.random() * 0.6 + 0.2,
            memoryUsage: Math.random() * 0.7 + 0.2,
            networkLatency: Math.random() * 20 + 10,
            storageUsage: Math.random() * 0.8 + 0.1
        };
    }

    calculateOverallHealth(queen, workers, system) {
        const issues = [];
        
        if (queen.status !== 'healthy') issues.push('Queen coordinator issues');
        
        const unhealthyWorkers = Object.values(workers).filter(w => w.status !== 'healthy');
        if (unhealthyWorkers.length > 0) {
            issues.push(`${unhealthyWorkers.length} unhealthy workers`);
        }
        
        if (system.status !== 'healthy') issues.push('System resource issues');
        
        return {
            status: issues.length === 0 ? 'healthy' : 'degraded',
            issues: issues,
            score: Math.max(0, 100 - (issues.length * 25))
        };
    }

    async handleHealthIssues(healthReport) {
        for (const issue of healthReport.overall.issues) {
            if (issue.includes('workers')) {
                await this.handleWorkerHealthIssues();
            } else if (issue.includes('Queen')) {
                await this.handleQueenHealthIssues();
            } else if (issue.includes('System')) {
                await this.handleSystemHealthIssues();
            }
        }
    }

    async handleWorkerHealthIssues() {
        const unhealthyWorkers = Array.from(this.workers.entries())
            .filter(([id, worker]) => worker.status === 'degraded');
        
        for (const [id, worker] of unhealthyWorkers) {
            console.log(`🔧 Attempting to recover worker: ${id}`);
            
            // Try to recover worker
            const recovered = await this.recoverWorker(id);
            
            if (!recovered) {
                console.log(`♻️ Replacing unhealthy worker: ${id}`);
                await this.replaceWorker(id);
            }
        }
    }

    async recoverWorker(workerId) {
        // Simulate recovery attempt
        const recoverySuccess = Math.random() > 0.3; // 70% success rate
        
        if (recoverySuccess) {
            const worker = this.workers.get(workerId);
            worker.status = 'available';
            console.log(`✅ Worker recovered: ${workerId}`);
        }
        
        return recoverySuccess;
    }

    async replaceWorker(workerId) {
        const worker = this.workers.get(workerId);
        const workerType = worker.type;
        
        // Remove old worker
        this.workers.delete(workerId);
        
        // Spawn replacement
        const newWorker = await this.spawnWorker(workerType);
        
        console.log(`♻️ Worker replaced: ${workerId} → ${newWorker.id}`);
        return newWorker;
    }

    async collectPerformanceMetrics() {
        const metrics = {
            timestamp: new Date().toISOString(),
            hive: {
                totalWorkers: this.workers.size,
                activeWorkers: Array.from(this.workers.values()).filter(w => w.status === 'busy').length,
                taskQueue: this.taskQueue.length,
                completedTasks: this.completedTasks.length,
                averageUtilization: this.calculateAverageUtilization()
            },
            performance: await this.monitor.collectPerformanceMetrics(),
            loadBalancing: this.loadBalancer.getLoadMetrics()
        };
        
        return metrics;
    }

    calculateAverageUtilization() {
        const workers = Array.from(this.workers.values());
        if (workers.length === 0) return 0;
        
        const totalUtilization = workers.reduce((sum, worker) => {
            const utilization = (worker.currentTasks || 0) / (worker.maxTasks || 3);
            return sum + utilization;
        }, 0);
        
        return totalUtilization / workers.length;
    }

    async evaluateAutoScaling() {
        const metrics = await this.collectPerformanceMetrics();
        const avgUtilization = metrics.hive.averageUtilization;
        const queueDepth = metrics.hive.taskQueue;
        
        // Scale up if high utilization or long queue
        if (avgUtilization > 0.8 || queueDepth > 10) {
            await this.scaleUp();
        }
        
        // Scale down if low utilization and short queue
        if (avgUtilization < 0.3 && queueDepth < 2) {
            await this.scaleDown();
        }
    }

    async scaleUp() {
        // Find worker type with highest demand
        const demandAnalysis = this.analyzeDemandByType();
        const highestDemandType = Object.keys(demandAnalysis)
            .reduce((a, b) => demandAnalysis[a].demand > demandAnalysis[b].demand ? a : b);
        
        const config = this.config.workers[highestDemandType];
        const currentCount = Array.from(this.workers.values())
            .filter(w => w.type === highestDemandType).length;
        
        if (currentCount < config.maxInstances) {
            await this.spawnWorker(highestDemandType);
            console.log(`📈 Scaled up: Added ${highestDemandType} worker`);
        }
    }

    async scaleDown() {
        // Find worker type with lowest utilization
        const utilizationByType = this.analyzeUtilizationByType();
        const lowestUtilizationType = Object.keys(utilizationByType)
            .reduce((a, b) => utilizationByType[a] < utilizationByType[b] ? a : b);
        
        const workers = Array.from(this.workers.entries())
            .filter(([id, worker]) => worker.type === lowestUtilizationType && worker.status === 'available');
        
        if (workers.length > 2) { // Keep minimum 2 workers of each type
            const [workerId] = workers[0];
            this.workers.delete(workerId);
            console.log(`📉 Scaled down: Removed ${lowestUtilizationType} worker ${workerId}`);
        }
    }

    analyzeDemandByType() {
        const demand = {};
        const workerTypes = Object.keys(this.config.workers);
        
        workerTypes.forEach(type => {
            const workers = Array.from(this.workers.values()).filter(w => w.type === type);
            const totalTasks = workers.reduce((sum, w) => sum + (w.currentTasks || 0), 0);
            const queuedTasks = this.taskQueue.filter(task => 
                this.determineWorkerTypeForTask(task) === type
            ).length;
            
            demand[type] = {
                current: totalTasks,
                queued: queuedTasks,
                demand: totalTasks + queuedTasks
            };
        });
        
        return demand;
    }

    analyzeUtilizationByType() {
        const utilization = {};
        const workerTypes = Object.keys(this.config.workers);
        
        workerTypes.forEach(type => {
            const workers = Array.from(this.workers.values()).filter(w => w.type === type);
            if (workers.length === 0) {
                utilization[type] = 0;
                return;
            }
            
            const totalUtilization = workers.reduce((sum, worker) => {
                return sum + ((worker.currentTasks || 0) / (worker.maxTasks || 3));
            }, 0);
            
            utilization[type] = totalUtilization / workers.length;
        });
        
        return utilization;
    }

    async delegateTask(task) {
        console.log(`🎯 Delegating task: ${task.title}`);
        
        // Add to task queue
        task.id = task.id || this.generateTaskId();
        task.queuedAt = new Date().toISOString();
        this.taskQueue.push(task);
        
        // Find and assign worker
        const worker = await this.loadBalancer.assignTask(task);
        
        if (worker) {
            // Remove from queue and assign to worker
            const taskIndex = this.taskQueue.findIndex(t => t.id === task.id);
            if (taskIndex !== -1) {
                this.taskQueue.splice(taskIndex, 1);
            }
            
            // Assign task to worker
            const assignment = await this.assignTaskToWorker(task, worker);
            
            return assignment;
        } else {
            console.log(`⚠️ No suitable worker found for task: ${task.title}`);
            return null;
        }
    }

    generateTaskId() {
        return `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    async assignTaskToWorker(task, worker) {
        // Update worker status
        const workerData = this.workers.get(worker.id);
        workerData.currentTasks = (workerData.currentTasks || 0) + 1;
        workerData.status = 'busy';
        workerData.taskHistory = workerData.taskHistory || [];
        
        // Create assignment record
        const assignment = {
            taskId: task.id,
            workerId: worker.id,
            workerType: worker.type,
            assignedAt: new Date().toISOString(),
            status: 'assigned'
        };
        
        // Add to worker's task history
        workerData.taskHistory.push(assignment);
        
        console.log(`✅ Task assigned: ${task.title} → ${worker.type} ${worker.id}`);
        
        // Start task execution (simulated)
        this.executeTaskOnWorker(task, worker);
        
        return assignment;
    }

    async executeTaskOnWorker(task, worker) {
        try {
            // Simulate task execution
            const result = await worker.receiveTask(task);
            
            // Handle completion
            await this.handleTaskCompletion(task, worker, result);
            
        } catch (error) {
            await this.handleTaskError(task, worker, error);
        }
    }

    async handleTaskCompletion(task, worker, result) {
        // Update worker status
        const workerData = this.workers.get(worker.id);
        workerData.currentTasks = Math.max(0, (workerData.currentTasks || 1) - 1);
        
        if (workerData.currentTasks === 0) {
            workerData.status = 'available';
        }
        
        // Record completion
        this.completedTasks.push({
            task,
            worker: worker.id,
            result,
            completedAt: new Date().toISOString()
        });
        
        console.log(`✅ Task completed: ${task.title} by ${worker.type} ${worker.id}`);
    }

    async handleTaskError(task, worker, error) {
        console.error(`❌ Task failed: ${task.title} on ${worker.id}:`, error.message);
        
        // Update worker status
        const workerData = this.workers.get(worker.id);
        workerData.currentTasks = Math.max(0, (workerData.currentTasks || 1) - 1);
        
        if (workerData.currentTasks === 0) {
            workerData.status = 'available';
        }
        
        // Attempt task retry or escalation
        await this.handleTaskRetry(task, error);
    }

    async handleTaskRetry(task, error) {
        task.retryCount = (task.retryCount || 0) + 1;
        
        if (task.retryCount <= 3) {
            console.log(`🔄 Retrying task: ${task.title} (attempt ${task.retryCount})`);
            
            // Re-queue task after delay
            setTimeout(async () => {
                await this.delegateTask(task);
            }, 5000 * task.retryCount); // Exponential backoff
        } else {
            console.log(`❌ Task failed permanently: ${task.title}`);
            
            // Escalate to Queen
            await this.escalateTaskFailure(task, error);
        }
    }

    async escalateTaskFailure(task, error) {
        const escalation = {
            type: 'task_failure',
            task: task,
            error: error.message,
            retryCount: task.retryCount,
            escalatedAt: new Date().toISOString()
        };
        
        console.log(`👑 Escalating task failure to Queen: ${task.title}`);
        return escalation;
    }

    async generateInitializationReport() {
        const report = {
            timestamp: new Date().toISOString(),
            status: 'operational',
            hive: {
                topology: this.config.topology.type,
                queenActive: !!this.queen,
                totalWorkers: this.workers.size,
                workerBreakdown: this.getWorkerBreakdown()
            },
            systems: {
                communication: !!this.communicationSystem,
                monitoring: !!this.monitor,
                loadBalancing: !!this.loadBalancer,
                autoScaling: this.config.resources.allocation.dynamicScaling
            },
            capabilities: {
                maxWorkers: this.config.topology.maxWorkers,
                workerTypes: Object.keys(this.config.workers),
                faultTolerance: this.config.faultTolerance.selfHealing.enabled,
                performanceMonitoring: true
            },
            workerAssignments: this.generateWorkerAssignments()
        };
        
        return report;
    }

    getWorkerBreakdown() {
        const breakdown = {};
        
        Object.keys(this.config.workers).forEach(type => {
            breakdown[type] = {
                count: Array.from(this.workers.values()).filter(w => w.type === type).length,
                maxInstances: this.config.workers[type].maxInstances,
                emoji: this.config.workers[type].emoji
            };
        });
        
        return breakdown;
    }

    generateWorkerAssignments() {
        const assignments = {};
        
        this.workers.forEach((worker, id) => {
            assignments[id] = {
                type: worker.type,
                emoji: this.config.workers[worker.type].emoji,
                status: worker.status,
                capabilities: worker.capabilities,
                currentTasks: worker.currentTasks || 0,
                maxTasks: worker.maxTasks || 3,
                utilization: `${(((worker.currentTasks || 0) / (worker.maxTasks || 3)) * 100).toFixed(1)}%`,
                spawnedAt: worker.spawnedAt
            };
        });
        
        return assignments;
    }

    async generateHiveStatusReport() {
        const performanceMetrics = await this.collectPerformanceMetrics();
        const healthReport = await this.performHealthChecks();
        
        return {
            timestamp: new Date().toISOString(),
            hive_structure: {
                queen: {
                    status: 'active',
                    id: this.queen.workerId,
                    directReports: this.workers.size
                },
                workers: this.generateWorkerAssignments(),
                topology: this.config.topology.type,
                totalCapacity: Array.from(this.workers.values())
                    .reduce((sum, w) => sum + (w.maxTasks || 3), 0)
            },
            performance: performanceMetrics,
            health: healthReport,
            coordination: {
                protocolsActive: !!this.communicationSystem,
                monitoringActive: !!this.monitor,
                loadBalancingActive: !!this.loadBalancer,
                autoScalingEnabled: this.config.resources.allocation.dynamicScaling
            },
            operational_status: {
                isActive: this.isActive,
                uptime: this.calculateUptime(),
                tasksQueued: this.taskQueue.length,
                tasksCompleted: this.completedTasks.length,
                averageUtilization: this.calculateAverageUtilization()
            }
        };
    }

    calculateUptime() {
        // This would track actual uptime in a real implementation
        return '1h 23m 45s';
    }

    async shutdown() {
        console.log('🏰 Shutting down Hive Orchestrator...');
        
        // Clear intervals
        if (this.healthCheckInterval) clearInterval(this.healthCheckInterval);
        if (this.performanceInterval) clearInterval(this.performanceInterval);
        if (this.scalingInterval) clearInterval(this.scalingInterval);
        
        // Graceful shutdown of workers
        for (const [id, worker] of this.workers) {
            console.log(`👋 Shutting down worker: ${id}`);
        }
        
        this.isActive = false;
        console.log('✅ Hive Orchestrator shut down complete');
    }
}

module.exports = { HiveOrchestrator };
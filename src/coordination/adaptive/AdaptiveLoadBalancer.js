/**
 * Adaptive Load Balancer for Hive Coordination System
 * Implements intelligent load distribution with ML-based optimization
 */

class AdaptiveLoadBalancer {
    constructor(config = {}) {
        this.config = {
            rebalanceThreshold: 0.3, // 30% load imbalance triggers rebalancing
            rebalanceInterval: 60000, // 1 minute
            learningRate: 0.01,
            capabilityWeights: true,
            taskAffinityLearning: true,
            maxRebalanceAttempts: 3,
            ...config
        };
        
        this.agentCapabilities = new Map();
        this.taskAffinities = new Map();
        this.loadHistory = [];
        this.rebalanceHistory = [];
        this.performanceMetrics = new Map();
        
        // Load balancing strategies
        this.strategies = new Map([
            ['round_robin', new RoundRobinStrategy()],
            ['least_loaded', new LeastLoadedStrategy()],
            ['capability_based', new CapabilityBasedStrategy()],
            ['ml_optimized', new MLOptimizedStrategy()],
            ['hybrid', new HybridStrategy()]
        ]);
        
        this.currentStrategy = 'ml_optimized';
        this.rebalanceInProgress = false;
        
        this.initialize();
    }
    
    async initialize() {
        console.log('⚖️ Initializing Adaptive Load Balancer...');
        
        // Initialize agent profiler
        this.agentProfiler = new AgentProfiler(this.config);
        
        // Initialize task analyzer
        this.taskAnalyzer = new TaskAnalyzer(this.config);
        
        // Initialize ML models
        await this.initializeMLModels();
        
        // Start monitoring and rebalancing loops
        this.startMonitoring();
        this.startRebalancing();
        
        console.log('✅ Adaptive Load Balancer initialized');
    }
    
    async initializeMLModels() {
        // Initialize machine learning models for load balancing
        this.models = {
            agentPerformance: new AgentPerformanceModel(),
            taskComplexity: new TaskComplexityModel(),
            loadPrediction: new LoadPredictionModel(),
            affinityLearning: new AffinityLearningModel()
        };
        
        for (const [name, model] of Object.entries(this.models)) {
            try {
                await model.initialize();
                console.log(`🧠 Initialized ${name} model`);
            } catch (error) {
                console.error(`❌ Failed to initialize ${name} model:`, error);
            }
        }
    }
    
    startMonitoring() {
        // Monitor load distribution continuously
        this.monitoringInterval = setInterval(async () => {
            try {
                await this.monitorLoadDistribution();
            } catch (error) {
                console.error('❌ Error in load monitoring:', error);
            }
        }, 30000); // Every 30 seconds
    }
    
    startRebalancing() {
        // Periodic rebalancing evaluation
        this.rebalancingInterval = setInterval(async () => {
            try {
                await this.evaluateRebalanceNeed();
            } catch (error) {
                console.error('❌ Error in rebalancing evaluation:', error);
            }
        }, this.config.rebalanceInterval);
    }
    
    async monitorLoadDistribution() {
        const agents = await this.getActiveAgents();
        const loadDistribution = await this.calculateLoadDistribution(agents);
        
        // Store load history
        this.loadHistory.push({
            timestamp: Date.now(),
            distribution: loadDistribution,
            imbalance: this.calculateImbalanceIndex(loadDistribution),
            agents: agents.length
        });
        
        // Trim history
        if (this.loadHistory.length > 1000) {
            this.loadHistory = this.loadHistory.slice(-1000);
        }
        
        // Update agent capabilities
        await this.updateAgentCapabilities(agents);
        
        // Learn task affinities
        if (this.config.taskAffinityLearning) {
            await this.learnTaskAffinities();
        }
    }
    
    async calculateLoadDistribution(agents) {
        const distribution = {};
        
        for (const agent of agents) {
            const load = await this.getAgentLoad(agent);
            distribution[agent.id] = {
                currentLoad: load.current,
                capacity: load.capacity,
                utilization: load.current / load.capacity,
                taskCount: load.taskCount,
                taskTypes: load.taskTypes,
                performance: await this.getAgentPerformanceScore(agent.id)
            };
        }
        
        return distribution;
    }
    
    calculateImbalanceIndex(distribution) {
        const utilizations = Object.values(distribution).map(d => d.utilization);
        
        if (utilizations.length === 0) return 0;
        
        const mean = utilizations.reduce((a, b) => a + b) / utilizations.length;
        const variance = utilizations.reduce((sum, u) => sum + Math.pow(u - mean, 2), 0) / utilizations.length;
        
        // Coefficient of variation as imbalance index
        return mean > 0 ? Math.sqrt(variance) / mean : 0;
    }
    
    async updateAgentCapabilities(agents) {
        for (const agent of agents) {
            const profile = await this.agentProfiler.profileAgent(agent);
            this.agentCapabilities.set(agent.id, profile);
        }
    }
    
    async learnTaskAffinities() {
        // Learn which agents perform best on which types of tasks
        const recentTasks = await this.getRecentCompletedTasks();
        
        for (const task of recentTasks) {
            const agentId = task.assignedAgent;
            const taskType = task.type;
            const performance = task.performance || 0.5;
            
            if (!this.taskAffinities.has(agentId)) {
                this.taskAffinities.set(agentId, new Map());
            }
            
            const agentAffinities = this.taskAffinities.get(agentId);
            const currentAffinity = agentAffinities.get(taskType) || 0.5;
            
            // Update affinity with learning rate
            const newAffinity = currentAffinity + this.config.learningRate * (performance - currentAffinity);
            agentAffinities.set(taskType, Math.max(0, Math.min(1, newAffinity)));
        }
    }
    
    async evaluateRebalanceNeed() {
        if (this.rebalanceInProgress) {
            console.log('⏳ Rebalancing already in progress');
            return;
        }
        
        const latestLoad = this.loadHistory[this.loadHistory.length - 1];
        if (!latestLoad) return;
        
        const shouldRebalance = this.shouldTriggerRebalance(latestLoad);
        
        if (shouldRebalance.trigger) {
            console.log('🔄 Triggering load rebalancing:', shouldRebalance.reason);
            await this.executeRebalance(shouldRebalance.strategy);
        }
    }
    
    shouldTriggerRebalance(loadData) {
        const { imbalance, distribution } = loadData;
        
        // High imbalance threshold
        if (imbalance > this.config.rebalanceThreshold) {
            return {
                trigger: true,
                reason: `High load imbalance detected: ${(imbalance * 100).toFixed(1)}%`,
                strategy: 'imbalance_correction'
            };
        }
        
        // Overloaded agents
        const overloadedAgents = Object.values(distribution).filter(d => d.utilization > 0.9);
        if (overloadedAgents.length > 0) {
            return {
                trigger: true,
                reason: `${overloadedAgents.length} agents are overloaded`,
                strategy: 'overload_relief'
            };
        }
        
        // Underutilized agents
        const underutilizedAgents = Object.values(distribution).filter(d => d.utilization < 0.2);
        const totalAgents = Object.values(distribution).length;
        if (underutilizedAgents.length > totalAgents * 0.5) {
            return {
                trigger: true,
                reason: `${underutilizedAgents.length} agents are underutilized`,
                strategy: 'consolidation'
            };
        }
        
        // Performance-based rebalancing
        const lowPerformanceAgents = Object.values(distribution).filter(d => d.performance < 0.6);
        if (lowPerformanceAgents.length > 0 && this.hasAlternativeAgents(lowPerformanceAgents)) {
            return {
                trigger: true,
                reason: `Performance issues detected on ${lowPerformanceAgents.length} agents`,
                strategy: 'performance_optimization'
            };
        }
        
        return { trigger: false };
    }
    
    hasAlternativeAgents(problematicAgents) {
        // Check if there are alternative agents available for rebalancing
        const totalAgents = this.agentCapabilities.size;
        const problematicCount = problematicAgents.length;
        
        return totalAgents > problematicCount * 2; // Simple heuristic
    }
    
    async executeRebalance(strategy) {
        this.rebalanceInProgress = true;
        const startTime = Date.now();
        
        try {
            console.log(`⚖️ Executing ${strategy} rebalancing strategy...`);
            
            const currentDistribution = await this.getCurrentLoadDistribution();
            const rebalancePlan = await this.createRebalancePlan(currentDistribution, strategy);
            
            if (rebalancePlan.changes.length === 0) {
                console.log('✅ No rebalancing changes needed');
                return;
            }
            
            const success = await this.applyRebalancePlan(rebalancePlan);
            
            // Record rebalancing result
            this.recordRebalanceResult({
                strategy,
                startTime,
                endTime: Date.now(),
                success,
                changesApplied: rebalancePlan.changes.length,
                beforeDistribution: currentDistribution,
                plan: rebalancePlan
            });
            
            if (success) {
                console.log(`✅ Rebalancing completed successfully: ${rebalancePlan.changes.length} changes applied`);
            } else {
                console.log('❌ Rebalancing failed');
            }
            
        } catch (error) {
            console.error('❌ Error during rebalancing:', error);
        } finally {
            this.rebalanceInProgress = false;
        }
    }
    
    async createRebalancePlan(currentDistribution, strategy) {
        const plan = {
            strategy,
            timestamp: Date.now(),
            changes: [],
            expectedImprovement: 0
        };
        
        switch (strategy) {
            case 'imbalance_correction':
                plan.changes = await this.planImbalanceCorrection(currentDistribution);
                break;
            case 'overload_relief':
                plan.changes = await this.planOverloadRelief(currentDistribution);
                break;
            case 'consolidation':
                plan.changes = await this.planConsolidation(currentDistribution);
                break;
            case 'performance_optimization':
                plan.changes = await this.planPerformanceOptimization(currentDistribution);
                break;
            default:
                plan.changes = await this.planMLOptimizedRebalance(currentDistribution);
        }
        
        plan.expectedImprovement = this.calculateExpectedImprovement(currentDistribution, plan.changes);
        return plan;
    }
    
    async planImbalanceCorrection(distribution) {
        const changes = [];
        const agents = Object.entries(distribution);
        
        // Sort agents by utilization
        const sortedAgents = agents.sort((a, b) => b[1].utilization - a[1].utilization);
        
        const overloaded = sortedAgents.filter(([, data]) => data.utilization > 0.8);
        const underutilized = sortedAgents.filter(([, data]) => data.utilization < 0.4);
        
        // Move tasks from overloaded to underutilized agents
        for (const [overloadedId, overloadedData] of overloaded) {
            for (const [underutilizedId, underutilizedData] of underutilized) {
                if (overloadedData.utilization <= 0.8) break;
                
                const tasksToMove = await this.selectTasksToMove(
                    overloadedId,
                    underutilizedId,
                    Math.min(3, Math.floor(overloadedData.taskCount * 0.3))
                );
                
                for (const task of tasksToMove) {
                    changes.push({
                        type: 'task_reassignment',
                        taskId: task.id,
                        fromAgent: overloadedId,
                        toAgent: underutilizedId,
                        reason: 'load_balance'
                    });
                    
                    // Update utilization estimates
                    overloadedData.utilization -= task.estimatedLoad;
                    underutilizedData.utilization += task.estimatedLoad;
                }
            }
        }
        
        return changes;
    }
    
    async planOverloadRelief(distribution) {
        const changes = [];
        const overloadedAgents = Object.entries(distribution)
            .filter(([, data]) => data.utilization > 0.9)
            .sort((a, b) => b[1].utilization - a[1].utilization);
        
        for (const [agentId, agentData] of overloadedAgents) {
            const bestAlternatives = await this.findBestAlternativeAgents(agentId, agentData);
            
            const tasksToRedistribute = await this.selectTasksForRedistribution(agentId, 0.3); // 30% of tasks
            
            for (const task of tasksToRedistribute) {
                const bestAgent = this.selectBestAgentForTask(task, bestAlternatives);
                if (bestAgent) {
                    changes.push({
                        type: 'task_reassignment',
                        taskId: task.id,
                        fromAgent: agentId,
                        toAgent: bestAgent.id,
                        reason: 'overload_relief'
                    });
                }
            }
        }
        
        return changes;
    }
    
    async planConsolidation(distribution) {
        const changes = [];
        const underutilizedAgents = Object.entries(distribution)
            .filter(([, data]) => data.utilization < 0.2)
            .sort((a, b) => a[1].utilization - b[1].utilization);
        
        // Consolidate tasks from most underutilized agents
        const agentsToConsolidate = underutilizedAgents.slice(0, Math.floor(underutilizedAgents.length / 2));
        
        for (const [agentId, agentData] of agentsToConsolidate) {
            const tasksToMove = await this.getAllTasksFromAgent(agentId);
            const targetAgents = await this.findCapableAgents(tasksToMove);
            
            for (const task of tasksToMove) {
                const bestTarget = this.selectBestAgentForTask(task, targetAgents);
                if (bestTarget) {
                    changes.push({
                        type: 'task_reassignment',
                        taskId: task.id,
                        fromAgent: agentId,
                        toAgent: bestTarget.id,
                        reason: 'consolidation'
                    });
                }
            }
            
            // Mark agent for potential shutdown
            changes.push({
                type: 'agent_scaling',
                action: 'remove',
                agentId: agentId,
                reason: 'underutilization'
            });
        }
        
        return changes;
    }
    
    async planPerformanceOptimization(distribution) {
        const changes = [];
        const lowPerformanceAgents = Object.entries(distribution)
            .filter(([, data]) => data.performance < 0.6);
        
        for (const [agentId, agentData] of lowPerformanceAgents) {
            const tasks = await this.getAgentTasks(agentId);
            
            for (const task of tasks) {
                const betterAgents = await this.findBetterPerformingAgents(task, agentId);
                
                if (betterAgents.length > 0) {
                    const bestAgent = betterAgents[0];
                    changes.push({
                        type: 'task_reassignment',
                        taskId: task.id,
                        fromAgent: agentId,
                        toAgent: bestAgent.id,
                        reason: 'performance_optimization',
                        expectedImprovement: bestAgent.expectedPerformance - agentData.performance
                    });
                }
            }
        }
        
        return changes;
    }
    
    async planMLOptimizedRebalance(distribution) {
        // Use ML models to create optimal rebalancing plan
        const changes = [];
        
        try {
            const optimization = await this.models.loadPrediction.optimizeDistribution(distribution);
            
            for (const recommendation of optimization.recommendations) {
                changes.push({
                    type: recommendation.type,
                    ...recommendation.details,
                    reason: 'ml_optimization',
                    confidence: recommendation.confidence
                });
            }
        } catch (error) {
            console.warn('⚠️ ML optimization failed, using heuristic approach');
            return await this.planImbalanceCorrection(distribution);
        }
        
        return changes;
    }
    
    async applyRebalancePlan(plan) {
        let successCount = 0;
        let failureCount = 0;
        
        for (const change of plan.changes) {
            try {
                const success = await this.applyChange(change);
                if (success) {
                    successCount++;
                } else {
                    failureCount++;
                }
            } catch (error) {
                console.error(`❌ Failed to apply change:`, change, error);
                failureCount++;
            }
            
            // Small delay between changes to avoid overwhelming the system
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        const successRate = successCount / (successCount + failureCount);
        console.log(`📊 Rebalancing results: ${successCount} succeeded, ${failureCount} failed (${(successRate * 100).toFixed(1)}% success rate)`);
        
        return successRate > 0.7; // Consider successful if >70% of changes applied
    }
    
    async applyChange(change) {
        switch (change.type) {
            case 'task_reassignment':
                return await this.reassignTask(change.taskId, change.fromAgent, change.toAgent);
            case 'agent_scaling':
                return await this.scaleAgent(change.action, change.agentId);
            default:
                console.warn(`Unknown change type: ${change.type}`);
                return false;
        }
    }
    
    async reassignTask(taskId, fromAgent, toAgent) {
        // This would integrate with the actual task management system
        console.log(`🔄 Reassigning task ${taskId}: ${fromAgent} -> ${toAgent}`);
        
        try {
            // Simulate task reassignment
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Update internal tracking
            await this.updateTaskAssignment(taskId, toAgent);
            
            return true;
        } catch (error) {
            console.error(`❌ Task reassignment failed:`, error);
            return false;
        }
    }
    
    async scaleAgent(action, agentId) {
        // This would integrate with the actual agent management system
        console.log(`🎯 Agent scaling: ${action} ${agentId}`);
        
        try {
            if (action === 'remove') {
                // Gracefully remove agent
                await this.gracefullyRemoveAgent(agentId);
            } else if (action === 'add') {
                // Add new agent
                await this.addNewAgent(agentId);
            }
            
            return true;
        } catch (error) {
            console.error(`❌ Agent scaling failed:`, error);
            return false;
        }
    }
    
    recordRebalanceResult(result) {
        this.rebalanceHistory.push(result);
        
        // Keep only recent history
        if (this.rebalanceHistory.length > 100) {
            this.rebalanceHistory = this.rebalanceHistory.slice(-100);
        }
        
        // Learn from the result
        this.learnFromRebalanceResult(result);
    }
    
    learnFromRebalanceResult(result) {
        // Update strategy effectiveness
        if (result.success) {
            // Positive reinforcement for successful strategy
            console.log(`📈 Strategy ${result.strategy} was successful`);
        } else {
            // Learn from failure
            console.log(`📉 Strategy ${result.strategy} failed, analyzing causes...`);
        }
        
        // This could be expanded to feed back into ML models
    }
    
    calculateExpectedImprovement(currentDistribution, changes) {
        // Calculate expected improvement from planned changes
        let improvementScore = 0;
        
        for (const change of changes) {
            if (change.expectedImprovement) {
                improvementScore += change.expectedImprovement;
            } else {
                // Estimate improvement based on change type
                switch (change.reason) {
                    case 'load_balance':
                        improvementScore += 0.1;
                        break;
                    case 'overload_relief':
                        improvementScore += 0.2;
                        break;
                    case 'performance_optimization':
                        improvementScore += 0.15;
                        break;
                    default:
                        improvementScore += 0.05;
                }
            }
        }
        
        return improvementScore;
    }
    
    // Utility methods (stubs - would integrate with actual systems)
    async getActiveAgents() {
        // Return mock agent data
        return [
            { id: 'agent-1', type: 'scraper', capabilities: ['web_scraping', 'data_extraction'] },
            { id: 'agent-2', type: 'processor', capabilities: ['data_processing', 'validation'] },
            { id: 'agent-3', type: 'scraper', capabilities: ['web_scraping', 'content_analysis'] }
        ];
    }
    
    async getAgentLoad(agent) {
        return {
            current: Math.random() * 100,
            capacity: 100,
            taskCount: Math.floor(Math.random() * 10),
            taskTypes: ['scraping', 'processing']
        };
    }
    
    async getAgentPerformanceScore(agentId) {
        return Math.random() * 0.4 + 0.6; // 0.6-1.0 range
    }
    
    async getCurrentLoadDistribution() {
        const agents = await this.getActiveAgents();
        return await this.calculateLoadDistribution(agents);
    }
    
    async getRecentCompletedTasks() {
        return []; // Stub
    }
    
    async selectTasksToMove(fromAgent, toAgent, maxTasks) {
        return []; // Stub
    }
    
    async findBestAlternativeAgents(agentId, agentData) {
        return []; // Stub
    }
    
    async selectTasksForRedistribution(agentId, percentage) {
        return []; // Stub
    }
    
    selectBestAgentForTask(task, availableAgents) {
        return availableAgents[0] || null; // Stub
    }
    
    async getAllTasksFromAgent(agentId) {
        return []; // Stub
    }
    
    async findCapableAgents(tasks) {
        return []; // Stub
    }
    
    async getAgentTasks(agentId) {
        return []; // Stub
    }
    
    async findBetterPerformingAgents(task, currentAgentId) {
        return []; // Stub
    }
    
    async updateTaskAssignment(taskId, newAgentId) {
        // Stub
    }
    
    async gracefullyRemoveAgent(agentId) {
        // Stub
    }
    
    async addNewAgent(agentId) {
        // Stub
    }
    
    // Public API methods
    getLoadHistory() {
        return [...this.loadHistory];
    }
    
    getRebalanceHistory() {
        return [...this.rebalanceHistory];
    }
    
    getCurrentStrategy() {
        return this.currentStrategy;
    }
    
    setStrategy(strategy) {
        if (this.strategies.has(strategy)) {
            this.currentStrategy = strategy;
            console.log(`🎯 Load balancing strategy changed to: ${strategy}`);
            return true;
        }
        return false;
    }
    
    getAgentCapabilities() {
        return Object.fromEntries(this.agentCapabilities);
    }
    
    getTaskAffinities() {
        const affinities = {};
        for (const [agentId, taskAffinities] of this.taskAffinities) {
            affinities[agentId] = Object.fromEntries(taskAffinities);
        }
        return affinities;
    }
    
    async forceRebalance(strategy = null) {
        if (this.rebalanceInProgress) {
            throw new Error('Rebalancing already in progress');
        }
        
        const targetStrategy = strategy || this.currentStrategy;
        await this.executeRebalance(targetStrategy);
    }
    
    stop() {
        if (this.monitoringInterval) clearInterval(this.monitoringInterval);
        if (this.rebalancingInterval) clearInterval(this.rebalancingInterval);
        
        console.log('🛑 Adaptive Load Balancer stopped');
    }
}

// Supporting classes (simplified implementations)
class AgentProfiler {
    constructor(config) {
        this.config = config;
    }
    
    async profileAgent(agent) {
        return {
            id: agent.id,
            type: agent.type,
            capabilities: agent.capabilities || [],
            performance: Math.random() * 0.4 + 0.6,
            reliability: Math.random() * 0.3 + 0.7,
            efficiency: Math.random() * 0.4 + 0.6,
            specializations: this.identifySpecializations(agent)
        };
    }
    
    identifySpecializations(agent) {
        return agent.capabilities || [];
    }
}

class TaskAnalyzer {
    constructor(config) {
        this.config = config;
    }
    
    async analyzeTask(task) {
        return {
            complexity: Math.random(),
            resourceRequirements: Math.random(),
            estimatedDuration: Math.random() * 3600000, // Up to 1 hour
            skillRequirements: task.type ? [task.type] : []
        };
    }
}

// ML Model stubs
class AgentPerformanceModel {
    async initialize() {}
    async predict(agent, task) { return Math.random(); }
    async train(data) {}
}

class TaskComplexityModel {
    async initialize() {}
    async predict(task) { return Math.random(); }
    async train(data) {}
}

class LoadPredictionModel {
    async initialize() {}
    async predict(currentState) { return Math.random(); }
    async optimizeDistribution(distribution) {
        return { recommendations: [] };
    }
    async train(data) {}
}

class AffinityLearningModel {
    async initialize() {}
    async predict(agent, taskType) { return Math.random(); }
    async train(data) {}
}

// Strategy implementations (stubs)
class RoundRobinStrategy {}
class LeastLoadedStrategy {}
class CapabilityBasedStrategy {}
class MLOptimizedStrategy {}
class HybridStrategy {}

module.exports = { AdaptiveLoadBalancer };
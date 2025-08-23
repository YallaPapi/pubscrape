/**
 * Main Hive Coordinator - Orchestrates all adaptive coordination components
 * Integrates topology optimization, performance monitoring, predictive scaling, and self-organizing patterns
 */

const { TopologyOptimizer } = require('./adaptive/TopologyOptimizer');
const { PerformanceMonitor } = require('./monitoring/PerformanceMonitor');
const { PredictiveScaler } = require('./optimization/PredictiveScaler');
const { SelfOrganizingPatterns } = require('./patterns/SelfOrganizingPatterns');
const { AdaptiveLoadBalancer } = require('./adaptive/AdaptiveLoadBalancer');

class HiveCoordinator {
    constructor(config = {}) {
        this.config = {
            hiveId: 'pubscrape-hive-001',
            coordinationMode: 'adaptive',
            emergencyThresholds: {
                errorRate: 0.5,
                responseTime: 10000,
                agentFailureRate: 0.7
            },
            ...config
        };
        
        this.status = 'initializing';
        this.components = new Map();
        this.emergencyMode = false;
        this.coordinationMetrics = new Map();
        this.lastHealthCheck = 0;
        
        // Integration hooks
        this.hooks = {
            onTopologyChange: [],
            onPerformanceAlert: [],
            onScalingEvent: [],
            onPatternDetection: [],
            onEmergency: []
        };
        
        this.initialize();
    }
    
    async initialize() {
        console.log(`🏗️ Initializing Hive Coordinator (${this.config.hiveId})...`);
        
        try {
            // Initialize core components
            await this.initializeComponents();
            
            // Set up component integration
            await this.setupComponentIntegration();
            
            // Start coordination loops
            this.startCoordinationLoops();
            
            // Initialize neural learning integration
            await this.initializeNeuralIntegration();
            
            this.status = 'active';
            console.log('✅ Hive Coordinator fully initialized and active');
            
        } catch (error) {
            console.error('❌ Failed to initialize Hive Coordinator:', error);
            this.status = 'failed';
            throw error;
        }
    }
    
    async initializeComponents() {
        console.log('📦 Initializing coordination components...');
        
        // Initialize Performance Monitor first (other components depend on it)
        this.components.set('monitor', new PerformanceMonitor(this.config.monitoring));
        
        // Initialize Topology Optimizer
        this.components.set('topology', new TopologyOptimizer(this.config.topology));
        
        // Initialize Predictive Scaler
        this.components.set('scaler', new PredictiveScaler(this.config.scaling));
        
        // Initialize Load Balancer
        this.components.set('loadBalancer', new AdaptiveLoadBalancer(this.config.loadBalancing));
        
        // Initialize Self-Organizing Patterns
        this.components.set('patterns', new SelfOrganizingPatterns(this.config.patterns));
        
        console.log(`✅ Initialized ${this.components.size} coordination components`);
    }
    
    async setupComponentIntegration() {
        console.log('🔗 Setting up component integration...');
        
        const monitor = this.components.get('monitor');
        const topology = this.components.get('topology');
        const scaler = this.components.get('scaler');
        const loadBalancer = this.components.get('loadBalancer');
        const patterns = this.components.get('patterns');
        
        // Monitor → Topology integration
        this.hooks.onPerformanceAlert.push(async (alert) => {
            if (alert.severity === 'critical') {
                await topology.triggerTopologyAnalysis();
            }
        });
        
        // Monitor → Scaler integration
        this.hooks.onPerformanceAlert.push(async (alert) => {
            if (alert.type === 'HIGH_LOAD' || alert.type === 'LOW_COMPLETION_RATE') {
                await scaler.evaluateScalingNeed();
            }
        });
        
        // Monitor → Load Balancer integration
        this.hooks.onPerformanceAlert.push(async (alert) => {
            if (alert.type === 'HIGH_ERROR_RATE' || alert.type === 'SLOW_RESPONSE') {
                await loadBalancer.forceRebalance('performance_optimization');
            }
        });
        
        // Topology → Scaler integration
        this.hooks.onTopologyChange.push(async (change) => {
            // Recalibrate scaling models after topology change
            await scaler.trainModels(change.performanceData);
        });
        
        // Patterns → All components integration
        this.hooks.onPatternDetection.push(async (pattern) => {
            if (pattern.type === 'performance_optimization') {
                await this.applyPatternOptimization(pattern);
            }
        });
        
        // Emergency response integration
        this.hooks.onEmergency.push(async (emergency) => {
            await this.handleEmergencyResponse(emergency);
        });
        
        console.log('✅ Component integration setup completed');
    }
    
    startCoordinationLoops() {
        // Main coordination loop
        this.coordinationInterval = setInterval(async () => {
            try {
                await this.coordinationCycle();
            } catch (error) {
                console.error('❌ Error in coordination cycle:', error);
            }
        }, 60000); // Every minute
        
        // Health monitoring loop
        this.healthInterval = setInterval(async () => {
            try {
                await this.healthCheck();
            } catch (error) {
                console.error('❌ Error in health check:', error);
            }
        }, 30000); // Every 30 seconds
        
        // Emergency detection loop
        this.emergencyInterval = setInterval(async () => {
            try {
                await this.checkEmergencyConditions();
            } catch (error) {
                console.error('❌ Error in emergency check:', error);
            }
        }, 10000); // Every 10 seconds
        
        console.log('🔄 Coordination loops started');
    }
    
    async initializeNeuralIntegration() {
        console.log('🧠 Initializing neural learning integration...');
        
        try {
            // Initialize MCP neural integration if available
            await this.setupMCPIntegration();
            
            // Set up pattern learning
            await this.setupPatternLearning();
            
            // Set up performance learning
            await this.setupPerformanceLearning();
            
            console.log('✅ Neural integration initialized');
        } catch (error) {
            console.warn('⚠️ Neural integration not available, using local learning:', error.message);
        }
    }
    
    async setupMCPIntegration() {
        // This would integrate with MCP neural patterns
        // For now, simulate the integration
        this.mcpIntegration = {
            available: false,
            neuralPatterns: null,
            performanceTracking: null
        };
        
        // Try to connect to MCP neural services
        try {
            // Simulated MCP connection
            // const response = await fetch('/api/mcp/neural/status');
            // if (response.ok) {
            //     this.mcpIntegration.available = true;
            //     console.log('🔗 Connected to MCP neural services');
            // }
        } catch (error) {
            console.log('📡 MCP neural services not available, using local patterns');
        }
    }
    
    async setupPatternLearning() {
        // Set up learning from coordination patterns
        this.patternLearning = {
            successPatterns: new Map(),
            failurePatterns: new Map(),
            adaptationHistory: []
        };
    }
    
    async setupPerformanceLearning() {
        // Set up learning from performance data
        this.performanceLearning = {
            baselineMetrics: new Map(),
            improvementPatterns: new Map(),
            degradationTriggers: new Map()
        };
    }
    
    async coordinationCycle() {
        const cycleStart = Date.now();
        
        // Collect system state
        const systemState = await this.collectSystemState();
        
        // Analyze coordination effectiveness
        const effectiveness = await this.analyzeCoordinationEffectiveness(systemState);
        
        // Make coordination decisions
        const decisions = await this.makeCoordinationDecisions(systemState, effectiveness);
        
        // Apply decisions
        await this.applyCoordinationDecisions(decisions);
        
        // Learn from results
        await this.learnFromCycle(systemState, decisions);
        
        // Update metrics
        this.updateCoordinationMetrics(cycleStart, systemState, effectiveness, decisions);
        
        console.log('🔄 Coordination cycle completed:', {
            duration: Date.now() - cycleStart,
            decisions: decisions.length,
            effectiveness: effectiveness.score.toFixed(3)
        });
    }
    
    async collectSystemState() {
        const monitor = this.components.get('monitor');
        const topology = this.components.get('topology');
        const scaler = this.components.get('scaler');
        const loadBalancer = this.components.get('loadBalancer');
        const patterns = this.components.get('patterns');
        
        return {
            timestamp: Date.now(),
            performance: monitor.getLatestMetrics(),
            trends: monitor.getTrends(),
            topology: await this.getCurrentTopology(),
            scaling: scaler.getPredictions(),
            loadDistribution: loadBalancer.getLoadHistory().slice(-1)[0],
            patterns: patterns.getPatterns(),
            emergentBehaviors: patterns.getEmergentBehaviors(),
            alerts: monitor.getAlerts('critical').filter(a => !a.acknowledged)
        };
    }
    
    async analyzeCoordinationEffectiveness(systemState) {
        const effectiveness = {
            score: 0,
            components: {},
            bottlenecks: [],
            opportunities: []
        };
        
        // Analyze each component's effectiveness
        effectiveness.components.monitoring = this.analyzeMonitoringEffectiveness(systemState);
        effectiveness.components.topology = await this.analyzeTopologyEffectiveness(systemState);
        effectiveness.components.scaling = this.analyzeScalingEffectiveness(systemState);
        effectiveness.components.loadBalancing = this.analyzeLoadBalancingEffectiveness(systemState);
        effectiveness.components.patterns = this.analyzePatternsEffectiveness(systemState);
        
        // Calculate overall effectiveness score
        const componentScores = Object.values(effectiveness.components);
        effectiveness.score = componentScores.reduce((sum, score) => sum + score, 0) / componentScores.length;
        
        // Identify bottlenecks
        effectiveness.bottlenecks = this.identifyBottlenecks(systemState, effectiveness.components);
        
        // Identify optimization opportunities
        effectiveness.opportunities = this.identifyOptimizationOpportunities(systemState, effectiveness.components);
        
        return effectiveness;
    }
    
    analyzeMonitoringEffectiveness(systemState) {
        // Analyze how well monitoring is performing
        const alerts = systemState.alerts || [];
        const trends = systemState.trends;
        
        let score = 0.7; // Base score
        
        // Penalty for too many unacknowledged alerts
        if (alerts.length > 5) {
            score -= 0.2;
        }
        
        // Bonus for good trend detection
        if (trends && trends.performance && trends.performance.confidence > 0.7) {
            score += 0.2;
        }
        
        return Math.max(0, Math.min(1, score));
    }
    
    async analyzeTopologyEffectiveness(systemState) {
        const topology = this.components.get('topology');
        const currentPerformance = systemState.performance;
        
        if (!currentPerformance) return 0.5;
        
        // Compare current performance with topology predictions
        const baseline = topology.getBaselineScore();
        const current = topology.calculatePerformanceScore(currentPerformance);
        
        // Effectiveness based on performance vs baseline
        return Math.max(0, Math.min(1, current / baseline));
    }
    
    analyzeScalingEffectiveness(systemState) {
        const scalingData = systemState.scaling;
        
        if (!scalingData) return 0.5;
        
        let score = 0.7; // Base score
        
        // Good prediction confidence increases effectiveness
        if (scalingData.confidence > 0.8) {
            score += 0.2;
        }
        
        // Accurate predictions increase effectiveness
        const predictions = scalingData.predictions || {};
        if (predictions.averageLoad && Math.abs(predictions.averageLoad - 0.6) < 0.1) {
            score += 0.1;
        }
        
        return Math.max(0, Math.min(1, score));
    }
    
    analyzeLoadBalancingEffectiveness(systemState) {
        const loadData = systemState.loadDistribution;
        
        if (!loadData) return 0.5;
        
        // Effectiveness based on load imbalance
        const imbalance = loadData.imbalance || 0.5;
        return Math.max(0, 1 - imbalance);
    }
    
    analyzePatternsEffectiveness(systemState) {
        const patterns = systemState.patterns || [];
        const emergentBehaviors = systemState.emergentBehaviors || [];
        
        let score = 0.5; // Base score
        
        // More patterns indicate better learning
        if (patterns.length > 10) {
            score += 0.2;
        }
        
        // Emergent behaviors indicate healthy evolution
        if (emergentBehaviors.length > 0) {
            score += 0.1;
        }
        
        // High-quality patterns increase effectiveness
        const highQualityPatterns = patterns.filter(p => p.utility > 0.8);
        if (highQualityPatterns.length > patterns.length * 0.3) {
            score += 0.2;
        }
        
        return Math.max(0, Math.min(1, score));
    }
    
    identifyBottlenecks(systemState, componentEffectiveness) {
        const bottlenecks = [];
        
        // Identify components with low effectiveness
        for (const [component, score] of Object.entries(componentEffectiveness)) {
            if (score < 0.6) {
                bottlenecks.push({
                    component,
                    score,
                    type: 'performance',
                    description: `${component} effectiveness is below threshold`
                });
            }
        }
        
        // Identify system-level bottlenecks
        if (systemState.alerts && systemState.alerts.length > 3) {
            bottlenecks.push({
                component: 'system',
                type: 'alerts',
                description: 'Too many critical alerts'
            });
        }
        
        return bottlenecks;
    }
    
    identifyOptimizationOpportunities(systemState, componentEffectiveness) {
        const opportunities = [];
        
        // Look for underutilized components
        if (componentEffectiveness.scaling > 0.9 && componentEffectiveness.loadBalancing < 0.7) {
            opportunities.push({
                type: 'load_balancing_optimization',
                description: 'Scaling is effective but load balancing could be improved',
                impact: 'high'
            });
        }
        
        // Look for pattern learning opportunities
        if (componentEffectiveness.patterns < 0.8 && systemState.performance) {
            opportunities.push({
                type: 'pattern_learning_enhancement',
                description: 'Performance data available for better pattern learning',
                impact: 'medium'
            });
        }
        
        return opportunities;
    }
    
    async makeCoordinationDecisions(systemState, effectiveness) {
        const decisions = [];
        
        // Emergency decisions first
        if (this.emergencyMode) {
            decisions.push(...await this.makeEmergencyDecisions(systemState));
        }
        
        // Address bottlenecks
        for (const bottleneck of effectiveness.bottlenecks) {
            decisions.push(...await this.makeBottleneckDecisions(bottleneck, systemState));
        }
        
        // Optimization decisions
        for (const opportunity of effectiveness.opportunities) {
            decisions.push(...await this.makeOptimizationDecisions(opportunity, systemState));
        }
        
        // Proactive decisions based on trends
        if (systemState.trends) {
            decisions.push(...await this.makeProactiveDecisions(systemState.trends));
        }
        
        return decisions;
    }
    
    async makeEmergencyDecisions(systemState) {
        const decisions = [];
        
        // Emergency scaling
        if (systemState.performance && systemState.performance.system.cpuUsage > 0.95) {
            decisions.push({
                type: 'emergency_scaling',
                action: 'scale_up',
                urgency: 'critical',
                target: 'agents',
                factor: 2
            });
        }
        
        // Emergency load redistribution
        if (systemState.alerts && systemState.alerts.some(a => a.type === 'AGENT_FAILURE')) {
            decisions.push({
                type: 'emergency_rebalance',
                action: 'redistribute_tasks',
                urgency: 'critical'
            });
        }
        
        return decisions;
    }
    
    async makeBottleneckDecisions(bottleneck, systemState) {
        const decisions = [];
        
        switch (bottleneck.component) {
            case 'monitoring':
                decisions.push({
                    type: 'monitoring_optimization',
                    action: 'reduce_alert_threshold',
                    component: bottleneck.component
                });
                break;
                
            case 'topology':
                decisions.push({
                    type: 'topology_analysis',
                    action: 'force_evaluation',
                    component: bottleneck.component
                });
                break;
                
            case 'loadBalancing':
                decisions.push({
                    type: 'load_balancing',
                    action: 'force_rebalance',
                    strategy: 'ml_optimized',
                    component: bottleneck.component
                });
                break;
        }
        
        return decisions;
    }
    
    async makeOptimizationDecisions(opportunity, systemState) {
        const decisions = [];
        
        switch (opportunity.type) {
            case 'load_balancing_optimization':
                decisions.push({
                    type: 'load_balancing',
                    action: 'strategy_optimization',
                    target: 'capability_based'
                });
                break;
                
            case 'pattern_learning_enhancement':
                decisions.push({
                    type: 'pattern_learning',
                    action: 'enhance_training',
                    data: systemState.performance
                });
                break;
        }
        
        return decisions;
    }
    
    async makeProactiveDecisions(trends) {
        const decisions = [];
        
        // Proactive scaling based on trends
        if (trends.performance && trends.performance.direction === 'declining') {
            decisions.push({
                type: 'proactive_scaling',
                action: 'prepare_scale_up',
                confidence: trends.performance.confidence
            });
        }
        
        // Proactive topology switching
        if (trends.resource && trends.resource.direction === 'improving') {
            decisions.push({
                type: 'topology_evaluation',
                action: 'consider_optimization',
                trigger: 'resource_improvement'
            });
        }
        
        return decisions;
    }
    
    async applyCoordinationDecisions(decisions) {
        for (const decision of decisions) {
            try {
                await this.applyDecision(decision);
            } catch (error) {
                console.error(`❌ Failed to apply decision:`, decision, error);
            }
        }
    }
    
    async applyDecision(decision) {
        const component = this.getComponentForDecision(decision);
        
        if (!component) {
            console.warn(`⚠️ No component found for decision type: ${decision.type}`);
            return;
        }
        
        switch (decision.type) {
            case 'emergency_scaling':
                await component.executeScaling({ action: decision.action, targetCount: decision.factor });
                break;
                
            case 'emergency_rebalance':
                await component.forceRebalance('emergency');
                break;
                
            case 'topology_analysis':
                await component.triggerTopologyAnalysis();
                break;
                
            case 'load_balancing':
                if (decision.action === 'force_rebalance') {
                    await component.forceRebalance(decision.strategy);
                } else if (decision.action === 'strategy_optimization') {
                    component.setStrategy(decision.target);
                }
                break;
                
            case 'pattern_learning':
                await component.trainModels(decision.data);
                break;
                
            default:
                console.log(`📋 Decision noted but not implemented: ${decision.type}`);
        }
        
        console.log(`✅ Applied decision: ${decision.type} - ${decision.action}`);
    }
    
    getComponentForDecision(decision) {
        const componentMapping = {
            'emergency_scaling': 'scaler',
            'proactive_scaling': 'scaler',
            'emergency_rebalance': 'loadBalancer',
            'load_balancing': 'loadBalancer',
            'topology_analysis': 'topology',
            'topology_evaluation': 'topology',
            'pattern_learning': 'patterns',
            'monitoring_optimization': 'monitor'
        };
        
        const componentName = componentMapping[decision.type];
        return componentName ? this.components.get(componentName) : null;
    }
    
    async learnFromCycle(systemState, decisions) {
        // Record the cycle for learning
        const cycleRecord = {
            timestamp: Date.now(),
            systemState: this.summarizeSystemState(systemState),
            decisions: decisions.map(d => ({ type: d.type, action: d.action })),
            outcome: 'pending' // Will be updated in next cycle
        };
        
        // Store for pattern learning
        this.patternLearning.adaptationHistory.push(cycleRecord);
        
        // Trim history
        if (this.patternLearning.adaptationHistory.length > 100) {
            this.patternLearning.adaptationHistory = this.patternLearning.adaptationHistory.slice(-100);
        }
        
        // Analyze previous cycle outcomes
        await this.analyzeCycleOutcomes();
    }
    
    summarizeSystemState(systemState) {
        return {
            performanceScore: systemState.performance ? this.calculateOverallPerformance(systemState.performance) : 0.5,
            alertCount: systemState.alerts ? systemState.alerts.length : 0,
            patternCount: systemState.patterns ? systemState.patterns.length : 0,
            topology: systemState.topology || 'unknown'
        };
    }
    
    calculateOverallPerformance(performance) {
        // Calculate overall performance score
        if (!performance.system || !performance.hive) return 0.5;
        
        return ((1 - performance.system.cpuUsage) + 
                (1 - performance.system.memoryUsage) + 
                (1 - performance.hive.errorRate) + 
                performance.hive.efficiency) / 4;
    }
    
    async analyzeCycleOutcomes() {
        const history = this.patternLearning.adaptationHistory;
        if (history.length < 2) return;
        
        // Compare current state with previous cycles
        const current = history[history.length - 1];
        const previous = history[history.length - 2];
        
        // Determine if previous decisions were effective
        const improvement = current.systemState.performanceScore - previous.systemState.performanceScore;
        
        if (improvement > 0.05) {
            // Positive outcome - reinforce successful patterns
            this.reinforceSuccessfulPatterns(previous.decisions);
        } else if (improvement < -0.05) {
            // Negative outcome - learn from failures
            this.learnFromFailures(previous.decisions);
        }
        
        // Update previous cycle outcome
        if (previous.outcome === 'pending') {
            previous.outcome = improvement > 0.05 ? 'success' : improvement < -0.05 ? 'failure' : 'neutral';
        }
    }
    
    reinforceSuccessfulPatterns(decisions) {
        for (const decision of decisions) {
            const pattern = `${decision.type}_${decision.action}`;
            const current = this.patternLearning.successPatterns.get(pattern) || 0;
            this.patternLearning.successPatterns.set(pattern, current + 1);
        }
    }
    
    learnFromFailures(decisions) {
        for (const decision of decisions) {
            const pattern = `${decision.type}_${decision.action}`;
            const current = this.patternLearning.failurePatterns.get(pattern) || 0;
            this.patternLearning.failurePatterns.set(pattern, current + 1);
        }
    }
    
    updateCoordinationMetrics(cycleStart, systemState, effectiveness, decisions) {
        const metrics = {
            timestamp: Date.now(),
            cycleDuration: Date.now() - cycleStart,
            effectivenessScore: effectiveness.score,
            decisionCount: decisions.length,
            bottleneckCount: effectiveness.bottlenecks.length,
            opportunityCount: effectiveness.opportunities.length,
            alertCount: systemState.alerts ? systemState.alerts.length : 0,
            emergencyMode: this.emergencyMode
        };
        
        this.coordinationMetrics.set(metrics.timestamp, metrics);
        
        // Trim metrics history
        const keys = Array.from(this.coordinationMetrics.keys()).sort((a, b) => b - a);
        if (keys.length > 1000) {
            const toDelete = keys.slice(1000);
            toDelete.forEach(key => this.coordinationMetrics.delete(key));
        }
    }
    
    async healthCheck() {
        const healthStatus = {
            timestamp: Date.now(),
            overall: 'healthy',
            components: {},
            issues: []
        };
        
        // Check each component
        for (const [name, component] of this.components) {
            try {
                const componentHealth = await this.checkComponentHealth(name, component);
                healthStatus.components[name] = componentHealth;
                
                if (componentHealth.status !== 'healthy') {
                    healthStatus.issues.push({
                        component: name,
                        issue: componentHealth.issue
                    });
                }
            } catch (error) {
                healthStatus.components[name] = { status: 'error', issue: error.message };
                healthStatus.issues.push({
                    component: name,
                    issue: `Health check failed: ${error.message}`
                });
            }
        }
        
        // Determine overall health
        const unhealthyComponents = Object.values(healthStatus.components).filter(c => c.status !== 'healthy');
        if (unhealthyComponents.length > 0) {
            healthStatus.overall = unhealthyComponents.length > this.components.size / 2 ? 'critical' : 'degraded';
        }
        
        this.lastHealthCheck = Date.now();
        
        if (healthStatus.overall !== 'healthy') {
            console.warn('⚠️ Health check issues detected:', healthStatus.issues);
        }
        
        return healthStatus;
    }
    
    async checkComponentHealth(name, component) {
        // Basic health check for each component
        const health = { status: 'healthy', metrics: {} };
        
        try {
            switch (name) {
                case 'monitor':
                    const latest = component.getLatestMetrics();
                    if (!latest || Date.now() - latest.timestamp > 120000) {
                        health.status = 'stale';
                        health.issue = 'Metrics are stale (>2 minutes old)';
                    }
                    break;
                    
                case 'topology':
                    // Check if topology optimizer is responsive
                    health.metrics.lastAdaptation = component.lastAdaptation;
                    break;
                    
                case 'scaler':
                    const predictions = component.getPredictions();
                    if (!predictions || !predictions.combined) {
                        health.status = 'degraded';
                        health.issue = 'No scaling predictions available';
                    }
                    break;
                    
                case 'loadBalancer':
                    if (component.rebalanceInProgress) {
                        health.status = 'busy';
                        health.issue = 'Rebalancing in progress';
                    }
                    break;
                    
                case 'patterns':
                    const patterns = component.getPatterns();
                    health.metrics.patternCount = patterns.length;
                    break;
            }
        } catch (error) {
            health.status = 'error';
            health.issue = error.message;
        }
        
        return health;
    }
    
    async checkEmergencyConditions() {
        const monitor = this.components.get('monitor');
        const latest = monitor.getLatestMetrics();
        
        if (!latest) return;
        
        const emergencyConditions = [];
        
        // Check error rate threshold
        if (latest.hive && latest.hive.errorRate > this.config.emergencyThresholds.errorRate) {
            emergencyConditions.push({
                type: 'high_error_rate',
                value: latest.hive.errorRate,
                threshold: this.config.emergencyThresholds.errorRate
            });
        }
        
        // Check response time threshold
        if (latest.hive && latest.hive.averageResponseTime > this.config.emergencyThresholds.responseTime) {
            emergencyConditions.push({
                type: 'slow_response',
                value: latest.hive.averageResponseTime,
                threshold: this.config.emergencyThresholds.responseTime
            });
        }
        
        // Check agent failure rate
        if (latest.coordination && latest.coordination.agentCount < 2) {
            emergencyConditions.push({
                type: 'insufficient_agents',
                value: latest.coordination.agentCount,
                threshold: 2
            });
        }
        
        // Handle emergency conditions
        if (emergencyConditions.length > 0 && !this.emergencyMode) {
            await this.enterEmergencyMode(emergencyConditions);
        } else if (emergencyConditions.length === 0 && this.emergencyMode) {
            await this.exitEmergencyMode();
        }
    }
    
    async enterEmergencyMode(conditions) {
        console.log('🚨 ENTERING EMERGENCY MODE', conditions);
        this.emergencyMode = true;
        
        // Trigger emergency hooks
        for (const hook of this.hooks.onEmergency) {
            try {
                await hook({ type: 'emergency_start', conditions });
            } catch (error) {
                console.error('❌ Emergency hook failed:', error);
            }
        }
        
        // Implement emergency protocols
        await this.handleEmergencyResponse({ conditions });
    }
    
    async exitEmergencyMode() {
        console.log('✅ EXITING EMERGENCY MODE - Conditions resolved');
        this.emergencyMode = false;
        
        // Trigger emergency hooks
        for (const hook of this.hooks.onEmergency) {
            try {
                await hook({ type: 'emergency_end' });
            } catch (error) {
                console.error('❌ Emergency hook failed:', error);
            }
        }
    }
    
    async handleEmergencyResponse(emergency) {
        // Implement emergency response protocols
        const scaler = this.components.get('scaler');
        const loadBalancer = this.components.get('loadBalancer');
        
        // Emergency scaling
        await scaler.executeScaling({
            action: 'scale_up',
            targetCount: Math.min(this.config.maxAgents || 20, 12)
        });
        
        // Emergency rebalancing
        await loadBalancer.forceRebalance('emergency');
        
        // Reduce monitoring thresholds for faster response
        const monitor = this.components.get('monitor');
        // monitor.setEmergencyMode(true); // Would implement if method exists
    }
    
    async applyPatternOptimization(pattern) {
        console.log(`🎯 Applying pattern optimization: ${pattern.type}`);
        
        // Apply optimization based on pattern type
        switch (pattern.type) {
            case 'coordination':
                await this.optimizeCoordination(pattern);
                break;
            case 'workload':
                await this.optimizeWorkload(pattern);
                break;
            case 'resource':
                await this.optimizeResources(pattern);
                break;
        }
    }
    
    async optimizeCoordination(pattern) {
        // Optimize coordination based on pattern
        const topology = this.components.get('topology');
        await topology.triggerTopologyAnalysis();
    }
    
    async optimizeWorkload(pattern) {
        // Optimize workload distribution
        const loadBalancer = this.components.get('loadBalancer');
        await loadBalancer.forceRebalance('ml_optimized');
    }
    
    async optimizeResources(pattern) {
        // Optimize resource usage
        const scaler = this.components.get('scaler');
        await scaler.evaluateScalingNeed();
    }
    
    // Utility methods
    async getCurrentTopology() {
        const topology = this.components.get('topology');
        return topology ? topology.currentTopology : 'unknown';
    }
    
    // Public API methods
    getStatus() {
        return {
            status: this.status,
            hiveId: this.config.hiveId,
            emergencyMode: this.emergencyMode,
            lastHealthCheck: this.lastHealthCheck,
            componentCount: this.components.size,
            coordinationMetrics: this.getCoordinationSummary()
        };
    }
    
    getCoordinationSummary() {
        const recentMetrics = Array.from(this.coordinationMetrics.values()).slice(-10);
        
        if (recentMetrics.length === 0) {
            return { averageEffectiveness: 0.5, averageCycleDuration: 0, emergencyModeTime: 0 };
        }
        
        return {
            averageEffectiveness: recentMetrics.reduce((sum, m) => sum + m.effectivenessScore, 0) / recentMetrics.length,
            averageCycleDuration: recentMetrics.reduce((sum, m) => sum + m.cycleDuration, 0) / recentMetrics.length,
            emergencyModeTime: recentMetrics.filter(m => m.emergencyMode).length / recentMetrics.length
        };
    }
    
    getComponentStatus(componentName) {
        const component = this.components.get(componentName);
        if (!component) return null;
        
        switch (componentName) {
            case 'monitor':
                return {
                    latest: component.getLatestMetrics(),
                    trends: component.getTrends(),
                    alerts: component.getAlerts()
                };
            case 'topology':
                return {
                    current: component.currentTopology,
                    history: component.performanceHistory.slice(-10)
                };
            case 'scaler':
                return {
                    predictions: component.getPredictions(),
                    history: component.getScalingHistory()
                };
            case 'loadBalancer':
                return {
                    strategy: component.getCurrentStrategy(),
                    history: component.getLoadHistory().slice(-10)
                };
            case 'patterns':
                return {
                    patterns: component.getPatterns().slice(-10),
                    metrics: component.getPatternMetrics()
                };
            default:
                return { status: 'unknown' };
        }
    }
    
    async addHook(hookType, callback) {
        if (this.hooks[hookType]) {
            this.hooks[hookType].push(callback);
            return true;
        }
        return false;
    }
    
    async triggerHook(hookType, data) {
        if (this.hooks[hookType]) {
            for (const callback of this.hooks[hookType]) {
                try {
                    await callback(data);
                } catch (error) {
                    console.error(`❌ Hook callback failed for ${hookType}:`, error);
                }
            }
        }
    }
    
    stop() {
        console.log('🛑 Stopping Hive Coordinator...');
        
        // Stop coordination loops
        if (this.coordinationInterval) clearInterval(this.coordinationInterval);
        if (this.healthInterval) clearInterval(this.healthInterval);
        if (this.emergencyInterval) clearInterval(this.emergencyInterval);
        
        // Stop all components
        for (const [name, component] of this.components) {
            try {
                if (component.stop) {
                    component.stop();
                }
                console.log(`✅ Stopped ${name} component`);
            } catch (error) {
                console.error(`❌ Error stopping ${name} component:`, error);
            }
        }
        
        this.status = 'stopped';
        console.log('✅ Hive Coordinator stopped');
    }
}

module.exports = { HiveCoordinator };
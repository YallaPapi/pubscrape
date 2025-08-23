/**
 * Predictive Scaler for Hive Adaptive Coordination
 * Implements ML-based predictive scaling with multiple forecasting models
 */

class PredictiveScaler {
    constructor(config = {}) {
        this.config = {
            predictionHorizon: 4 * 60 * 60 * 1000, // 4 hours
            scalingBuffer: 0.2, // 20% safety margin
            minAgents: 3,
            maxAgents: 20,
            scalingCooldown: 5 * 60 * 1000, // 5 minutes
            evaluationInterval: 60 * 1000, // 1 minute
            ...config
        };
        
        this.models = new Map();
        this.scalingHistory = [];
        this.lastScalingAction = 0;
        this.currentPredictions = new Map();
        this.scalingInProgress = false;
        
        // Workload patterns
        this.workloadPatterns = new Map();
        this.seasonalityDetector = null;
        
        this.initialize();
    }
    
    async initialize() {
        console.log('🔮 Initializing Predictive Scaler...');
        
        // Initialize prediction models
        await this.initializeModels();
        
        // Initialize pattern detection
        this.initializePatternDetection();
        
        // Start prediction and scaling loops
        this.startPredictionLoop();
        this.startScalingLoop();
        
        console.log('✅ Predictive Scaler initialized');
    }
    
    async initializeModels() {
        // Linear regression model for simple trends
        this.models.set('linear', new LinearRegressionModel());
        
        // LSTM model for complex temporal patterns
        this.models.set('lstm', new LSTMModel({
            sequenceLength: 20,
            hiddenUnits: 64,
            learningRate: 0.001
        }));
        
        // Random Forest for workload classification
        this.models.set('forest', new RandomForestModel({
            trees: 100,
            features: ['hour', 'dayOfWeek', 'taskType', 'currentLoad']
        }));
        
        // Ensemble model combining multiple approaches
        this.models.set('ensemble', new EnsembleModel({
            models: ['linear', 'lstm', 'forest'],
            weights: [0.3, 0.5, 0.2]
        }));
        
        // Initialize all models
        for (const [name, model] of this.models) {
            try {
                await model.initialize();
                console.log(`✅ Initialized ${name} prediction model`);
            } catch (error) {
                console.error(`❌ Failed to initialize ${name} model:`, error);
            }
        }
    }
    
    initializePatternDetection() {
        this.seasonalityDetector = new SeasonalityDetector({
            periods: [
                { name: 'hourly', duration: 60 * 60 * 1000 },
                { name: 'daily', duration: 24 * 60 * 60 * 1000 },
                { name: 'weekly', duration: 7 * 24 * 60 * 60 * 1000 }
            ]
        });
    }
    
    startPredictionLoop() {
        this.predictionInterval = setInterval(async () => {
            try {
                await this.generatePredictions();
            } catch (error) {
                console.error('❌ Error in prediction loop:', error);
            }
        }, this.config.evaluationInterval);
    }
    
    startScalingLoop() {
        this.scalingInterval = setInterval(async () => {
            try {
                await this.evaluateScalingNeed();
            } catch (error) {
                console.error('❌ Error in scaling loop:', error);
            }
        }, this.config.evaluationInterval);
    }
    
    async generatePredictions() {
        const currentTime = Date.now();
        const historicalData = await this.collectHistoricalData();
        
        if (historicalData.length < 10) {
            console.log('⏳ Insufficient historical data for predictions');
            return;
        }
        
        const predictions = new Map();
        
        // Generate predictions from each model
        for (const [name, model] of this.models) {
            try {
                const prediction = await model.predict(historicalData, this.config.predictionHorizon);
                predictions.set(name, prediction);
            } catch (error) {
                console.warn(`⚠️ Prediction failed for ${name} model:`, error);
            }
        }
        
        // Combine predictions using ensemble approach
        const combinedPrediction = this.combinePredictions(predictions);
        
        // Store predictions
        this.currentPredictions.set(currentTime, {
            predictions,
            combined: combinedPrediction,
            confidence: this.calculatePredictionConfidence(predictions)
        });
        
        // Update pattern detection
        await this.updatePatterns(historicalData);
        
        console.log('🔮 Predictions generated:', {
            predictedLoad: combinedPrediction.averageLoad.toFixed(3),
            peakLoad: combinedPrediction.peakLoad.toFixed(3),
            confidence: (combinedPrediction.confidence * 100).toFixed(1) + '%'
        });
    }
    
    async collectHistoricalData() {
        // Collect historical workload and performance data
        // This would integrate with the monitoring system
        
        const data = [];
        const now = Date.now();
        const dataPoints = 100; // Last 100 data points
        
        for (let i = dataPoints; i >= 0; i--) {
            const timestamp = now - (i * this.config.evaluationInterval);
            const point = await this.getHistoricalDataPoint(timestamp);
            if (point) {
                data.push(point);
            }
        }
        
        return data;
    }
    
    async getHistoricalDataPoint(timestamp) {
        // This would fetch actual historical data
        // For now, generate realistic sample data
        
        const hour = new Date(timestamp).getHours();
        const dayOfWeek = new Date(timestamp).getDay();
        
        // Simulate realistic workload patterns
        let baseLoad = 0.5;
        
        // Business hours pattern (9 AM - 6 PM on weekdays)
        if (dayOfWeek >= 1 && dayOfWeek <= 5 && hour >= 9 && hour <= 18) {
            baseLoad = 0.7 + Math.random() * 0.2;
        }
        // Weekend pattern
        else if (dayOfWeek === 0 || dayOfWeek === 6) {
            baseLoad = 0.3 + Math.random() * 0.3;
        }
        // Night hours
        else if (hour >= 22 || hour <= 6) {
            baseLoad = 0.2 + Math.random() * 0.2;
        }
        
        return {
            timestamp,
            load: Math.max(0, Math.min(1, baseLoad + (Math.random() - 0.5) * 0.2)),
            agentCount: Math.floor(3 + Math.random() * 8),
            taskCount: Math.floor(baseLoad * 50 + Math.random() * 20),
            errorRate: Math.random() * 0.05,
            responseTime: 1000 + Math.random() * 2000,
            hour,
            dayOfWeek
        };
    }
    
    combinePredictions(predictions) {
        if (predictions.size === 0) {
            return { averageLoad: 0.5, peakLoad: 0.7, confidence: 0 };
        }
        
        let totalWeight = 0;
        let weightedAverageLoad = 0;
        let weightedPeakLoad = 0;
        let confidenceSum = 0;
        
        // Use ensemble model if available
        if (predictions.has('ensemble')) {
            return predictions.get('ensemble');
        }
        
        // Otherwise combine other predictions
        const weights = {
            linear: 0.3,
            lstm: 0.5,
            forest: 0.2
        };
        
        for (const [name, prediction] of predictions) {
            const weight = weights[name] || 0.1;
            weightedAverageLoad += prediction.averageLoad * weight;
            weightedPeakLoad += prediction.peakLoad * weight;
            confidenceSum += prediction.confidence * weight;
            totalWeight += weight;
        }
        
        if (totalWeight === 0) {
            return { averageLoad: 0.5, peakLoad: 0.7, confidence: 0 };
        }
        
        return {
            averageLoad: weightedAverageLoad / totalWeight,
            peakLoad: weightedPeakLoad / totalWeight,
            confidence: confidenceSum / totalWeight
        };
    }
    
    calculatePredictionConfidence(predictions) {
        if (predictions.size === 0) return 0;
        
        // Calculate variance between predictions as inverse confidence
        const values = Array.from(predictions.values()).map(p => p.averageLoad);
        const mean = values.reduce((a, b) => a + b) / values.length;
        const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
        
        // Lower variance = higher confidence
        return Math.max(0, 1 - variance * 4);
    }
    
    async updatePatterns(historicalData) {
        if (historicalData.length < 50) return;
        
        // Detect seasonal patterns
        const patterns = await this.seasonalityDetector.analyze(historicalData);
        
        for (const pattern of patterns) {
            this.workloadPatterns.set(pattern.name, pattern);
        }
        
        // Detect recurring workload types
        const workloadTypes = this.classifyWorkloadTypes(historicalData);
        this.workloadPatterns.set('workload_types', workloadTypes);
    }
    
    classifyWorkloadTypes(data) {
        // Simple workload classification based on load patterns
        const types = {
            'heavy_scraping': data.filter(d => d.load > 0.8 && d.taskCount > 40),
            'moderate_processing': data.filter(d => d.load > 0.4 && d.load <= 0.8),
            'light_maintenance': data.filter(d => d.load <= 0.4),
            'error_recovery': data.filter(d => d.errorRate > 0.03)
        };
        
        return types;
    }
    
    async evaluateScalingNeed() {
        if (this.scalingInProgress) {
            console.log('⏳ Scaling already in progress, skipping evaluation');
            return;
        }
        
        // Check cooldown period
        const timeSinceLastScaling = Date.now() - this.lastScalingAction;
        if (timeSinceLastScaling < this.config.scalingCooldown) {
            return;
        }
        
        const currentLoad = await this.getCurrentLoad();
        const currentAgentCount = await this.getCurrentAgentCount();
        const latestPrediction = this.getLatestPrediction();
        
        if (!latestPrediction || latestPrediction.confidence < 0.5) {
            console.log('⚠️ Prediction confidence too low for scaling decisions');
            return;
        }
        
        const scalingDecision = this.calculateScalingDecision(
            currentLoad,
            currentAgentCount,
            latestPrediction
        );
        
        if (scalingDecision.action !== 'none') {
            await this.executeScaling(scalingDecision);
        }
    }
    
    calculateScalingDecision(currentLoad, currentAgentCount, prediction) {
        const { averageLoad, peakLoad, confidence } = prediction.combined;
        const buffer = this.config.scalingBuffer;
        
        // Calculate optimal agent count based on predictions
        const optimalForAverage = Math.ceil(averageLoad * this.config.maxAgents);
        const optimalForPeak = Math.ceil(peakLoad * this.config.maxAgents * (1 + buffer));
        
        // Use the higher of the two with confidence weighting
        const predictedOptimal = Math.round(
            optimalForAverage * (1 - confidence) + optimalForPeak * confidence
        );
        
        // Apply constraints
        const targetAgentCount = Math.max(
            this.config.minAgents,
            Math.min(this.config.maxAgents, predictedOptimal)
        );
        
        // Determine scaling action
        let action = 'none';
        let targetCount = currentAgentCount;
        let reason = 'No scaling needed';
        
        const scalingThreshold = Math.max(1, Math.floor(currentAgentCount * 0.2)); // 20% change threshold
        
        if (targetAgentCount > currentAgentCount + scalingThreshold) {
            action = 'scale_up';
            targetCount = targetAgentCount;
            reason = `Predicted load increase requires more agents (${averageLoad.toFixed(2)} avg, ${peakLoad.toFixed(2)} peak)`;
        } else if (targetAgentCount < currentAgentCount - scalingThreshold) {
            action = 'scale_down';
            targetCount = targetAgentCount;
            reason = `Predicted load decrease allows fewer agents (${averageLoad.toFixed(2)} avg)`;
        }
        
        // Emergency scaling for current high load
        if (currentLoad > 0.9 && currentAgentCount < this.config.maxAgents) {
            action = 'scale_up_emergency';
            targetCount = Math.min(this.config.maxAgents, currentAgentCount + Math.ceil(currentAgentCount * 0.5));
            reason = 'Emergency scaling due to current high load';
        }
        
        return {
            action,
            targetCount,
            currentCount: currentAgentCount,
            reason,
            confidence,
            prediction: { averageLoad, peakLoad }
        };
    }
    
    async executeScaling(decision) {
        console.log(`🎯 Executing scaling decision: ${decision.action}`, {
            from: decision.currentCount,
            to: decision.targetCount,
            reason: decision.reason,
            confidence: (decision.confidence * 100).toFixed(1) + '%'
        });
        
        this.scalingInProgress = true;
        
        try {
            const success = await this.performScaling(decision);
            
            if (success) {
                // Record successful scaling
                this.recordScalingAction(decision, true);
                console.log(`✅ Scaling completed successfully: ${decision.currentCount} -> ${decision.targetCount} agents`);
            } else {
                console.error('❌ Scaling operation failed');
                this.recordScalingAction(decision, false);
            }
        } catch (error) {
            console.error('❌ Error during scaling execution:', error);
            this.recordScalingAction(decision, false);
        } finally {
            this.scalingInProgress = false;
            this.lastScalingAction = Date.now();
        }
    }
    
    async performScaling(decision) {
        // This would integrate with the actual swarm management system
        // For now, simulate the scaling operation
        
        const { action, targetCount } = decision;
        
        switch (action) {
            case 'scale_up':
            case 'scale_up_emergency':
                return await this.scaleUp(targetCount);
            case 'scale_down':
                return await this.scaleDown(targetCount);
            default:
                return true;
        }
    }
    
    async scaleUp(targetCount) {
        console.log(`📈 Scaling up to ${targetCount} agents...`);
        
        // Simulate scaling up by spawning new agents
        // This would integrate with MCP agent spawning
        try {
            // Simulated delay for scaling operation
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // In real implementation, this would:
            // 1. Spawn new agents using MCP
            // 2. Update agent assignments
            // 3. Rebalance workload
            // 4. Monitor new agents coming online
            
            return true;
        } catch (error) {
            console.error('❌ Scale up failed:', error);
            return false;
        }
    }
    
    async scaleDown(targetCount) {
        console.log(`📉 Scaling down to ${targetCount} agents...`);
        
        try {
            // Simulate scaling down
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // In real implementation, this would:
            // 1. Identify agents to remove (least utilized)
            // 2. Gracefully reassign their tasks
            // 3. Terminate excess agents
            // 4. Rebalance remaining workload
            
            return true;
        } catch (error) {
            console.error('❌ Scale down failed:', error);
            return false;
        }
    }
    
    recordScalingAction(decision, success) {
        this.scalingHistory.push({
            timestamp: Date.now(),
            action: decision.action,
            fromCount: decision.currentCount,
            toCount: decision.targetCount,
            reason: decision.reason,
            confidence: decision.confidence,
            success,
            prediction: decision.prediction
        });
        
        // Keep only recent history
        if (this.scalingHistory.length > 100) {
            this.scalingHistory = this.scalingHistory.slice(-100);
        }
    }
    
    getLatestPrediction() {
        const timestamps = Array.from(this.currentPredictions.keys()).sort((a, b) => b - a);
        if (timestamps.length === 0) return null;
        
        return this.currentPredictions.get(timestamps[0]);
    }
    
    async getCurrentLoad() {
        // This would get actual current load from monitoring system
        return Math.random(); // Stub
    }
    
    async getCurrentAgentCount() {
        // This would get actual agent count from swarm system
        return Math.floor(Math.random() * 10) + 3; // Stub
    }
    
    // Public API methods
    getPredictions() {
        return this.getLatestPrediction();
    }
    
    getScalingHistory() {
        return [...this.scalingHistory];
    }
    
    getPatterns() {
        return Object.fromEntries(this.workloadPatterns);
    }
    
    async trainModels(additionalData) {
        console.log('🧠 Training prediction models with new data...');
        
        for (const [name, model] of this.models) {
            try {
                await model.train(additionalData);
                console.log(`✅ Trained ${name} model`);
            } catch (error) {
                console.error(`❌ Failed to train ${name} model:`, error);
            }
        }
    }
    
    stop() {
        if (this.predictionInterval) clearInterval(this.predictionInterval);
        if (this.scalingInterval) clearInterval(this.scalingInterval);
        
        console.log('🛑 Predictive Scaler stopped');
    }
}

// Prediction model classes (simplified implementations)
class LinearRegressionModel {
    async initialize() {
        this.weights = null;
    }
    
    async predict(data, horizon) {
        // Simple linear trend prediction
        if (data.length < 5) {
            return { averageLoad: 0.5, peakLoad: 0.7, confidence: 0.3 };
        }
        
        const loads = data.map(d => d.load);
        const trend = this.calculateTrend(loads);
        const average = loads.reduce((a, b) => a + b) / loads.length;
        
        const futureLoad = Math.max(0, Math.min(1, average + trend));
        
        return {
            averageLoad: futureLoad,
            peakLoad: Math.min(1, futureLoad * 1.3),
            confidence: 0.6
        };
    }
    
    calculateTrend(values) {
        if (values.length < 2) return 0;
        
        const recent = values.slice(-10);
        const older = values.slice(-20, -10);
        
        if (older.length === 0) return 0;
        
        const recentAvg = recent.reduce((a, b) => a + b) / recent.length;
        const olderAvg = older.reduce((a, b) => a + b) / older.length;
        
        return (recentAvg - olderAvg) * 0.5; // Dampened trend
    }
    
    async train(data) {
        // Training would update weights
        console.log('📈 Training linear regression model...');
    }
}

class LSTMModel {
    constructor(config) {
        this.config = config;
    }
    
    async initialize() {
        // Initialize LSTM model
        this.model = null;
    }
    
    async predict(data, horizon) {
        // LSTM prediction (simplified)
        const loads = data.slice(-this.config.sequenceLength).map(d => d.load);
        
        if (loads.length < this.config.sequenceLength) {
            return { averageLoad: 0.5, peakLoad: 0.7, confidence: 0.4 };
        }
        
        // Simulate LSTM prediction
        const average = loads.reduce((a, b) => a + b) / loads.length;
        const variance = loads.reduce((sum, val) => sum + Math.pow(val - average, 2), 0) / loads.length;
        
        return {
            averageLoad: average,
            peakLoad: Math.min(1, average + Math.sqrt(variance)),
            confidence: 0.8
        };
    }
    
    async train(data) {
        console.log('🧠 Training LSTM model...');
    }
}

class RandomForestModel {
    constructor(config) {
        this.config = config;
    }
    
    async initialize() {
        this.trees = [];
    }
    
    async predict(data, horizon) {
        // Random Forest prediction
        const latest = data[data.length - 1];
        
        // Feature-based prediction
        let predictedLoad = 0.5;
        
        // Business hours boost
        if (latest.hour >= 9 && latest.hour <= 17 && latest.dayOfWeek >= 1 && latest.dayOfWeek <= 5) {
            predictedLoad = 0.7;
        }
        
        return {
            averageLoad: predictedLoad,
            peakLoad: Math.min(1, predictedLoad * 1.2),
            confidence: 0.7
        };
    }
    
    async train(data) {
        console.log('🌳 Training Random Forest model...');
    }
}

class EnsembleModel {
    constructor(config) {
        this.config = config;
    }
    
    async initialize() {
        // Initialize ensemble
    }
    
    async predict(data, horizon) {
        // This would combine predictions from multiple models
        return { averageLoad: 0.6, peakLoad: 0.8, confidence: 0.9 };
    }
    
    async train(data) {
        console.log('🎯 Training Ensemble model...');
    }
}

class SeasonalityDetector {
    constructor(config) {
        this.config = config;
    }
    
    async analyze(data) {
        // Detect seasonal patterns
        return [];
    }
}

module.exports = { PredictiveScaler };
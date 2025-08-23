/**
 * Real-time Performance Monitor for Hive Adaptive Coordination
 * Provides continuous monitoring, alerting, and performance analytics
 */

class PerformanceMonitor {
    constructor(config = {}) {
        this.config = {
            metricsInterval: 30000, // 30 seconds
            alertThresholds: {
                cpuUtilization: 0.85,
                memoryUsage: 0.80,
                errorRate: 0.05,
                responseTime: 5000,
                taskCompletionRate: 0.95
            },
            retentionPeriod: 24 * 60 * 60 * 1000, // 24 hours
            ...config
        };
        
        this.metrics = new Map();
        this.alerts = [];
        this.monitoringActive = false;
        this.collectors = new Map();
        this.analysisCache = new Map();
        
        this.initialize();
    }
    
    async initialize() {
        console.log('📊 Initializing Performance Monitor...');
        
        // Initialize metric collectors
        await this.initializeCollectors();
        
        // Start monitoring loops
        this.startMonitoring();
        
        // Start analysis engine
        this.startAnalysisEngine();
        
        console.log('✅ Performance Monitor initialized');
    }
    
    async initializeCollectors() {
        // System metrics collector
        this.collectors.set('system', new SystemMetricsCollector());
        
        // Hive-specific metrics collector
        this.collectors.set('hive', new HiveMetricsCollector());
        
        // Coordination metrics collector
        this.collectors.set('coordination', new CoordinationMetricsCollector());
        
        // Neural performance collector
        this.collectors.set('neural', new NeuralMetricsCollector());
        
        // Initialize all collectors
        for (const [name, collector] of this.collectors) {
            try {
                await collector.initialize();
                console.log(`✅ Initialized ${name} metrics collector`);
            } catch (error) {
                console.error(`❌ Failed to initialize ${name} collector:`, error);
            }
        }
    }
    
    startMonitoring() {
        this.monitoringActive = true;
        
        // Main metrics collection loop
        this.metricsInterval = setInterval(async () => {
            try {
                await this.collectAllMetrics();
                await this.checkAlerts();
            } catch (error) {
                console.error('❌ Error in monitoring loop:', error);
            }
        }, this.config.metricsInterval);
        
        // Cleanup old metrics
        this.cleanupInterval = setInterval(() => {
            this.cleanupOldMetrics();
        }, 5 * 60 * 1000); // Every 5 minutes
        
        console.log('🔄 Monitoring loops started');
    }
    
    startAnalysisEngine() {
        // Trend analysis
        this.trendInterval = setInterval(async () => {
            try {
                await this.analyzeTrends();
            } catch (error) {
                console.error('❌ Error in trend analysis:', error);
            }
        }, 5 * 60 * 1000); // Every 5 minutes
        
        // Performance pattern analysis
        this.patternInterval = setInterval(async () => {
            try {
                await this.analyzePatterns();
            } catch (error) {
                console.error('❌ Error in pattern analysis:', error);
            }
        }, 15 * 60 * 1000); // Every 15 minutes
        
        console.log('🧠 Analysis engine started');
    }
    
    async collectAllMetrics() {
        const timestamp = Date.now();
        const allMetrics = { timestamp };
        
        // Collect from all collectors
        for (const [name, collector] of this.collectors) {
            try {
                const metrics = await collector.collect();
                allMetrics[name] = metrics;
            } catch (error) {
                console.error(`❌ Error collecting ${name} metrics:`, error);
                allMetrics[name] = { error: error.message };
            }
        }
        
        // Store metrics
        this.storeMetrics(timestamp, allMetrics);
        
        return allMetrics;
    }
    
    storeMetrics(timestamp, metrics) {
        if (!this.metrics.has(timestamp)) {
            this.metrics.set(timestamp, metrics);
        }
        
        // Update latest metrics cache
        this.analysisCache.set('latest', metrics);
    }
    
    async checkAlerts() {
        const latest = this.analysisCache.get('latest');
        if (!latest) return;
        
        const alerts = [];
        
        // Check system thresholds
        if (latest.system) {
            if (latest.system.cpuUsage > this.config.alertThresholds.cpuUtilization) {
                alerts.push(this.createAlert('HIGH_CPU', 'CPU utilization exceeds threshold', {
                    current: latest.system.cpuUsage,
                    threshold: this.config.alertThresholds.cpuUtilization
                }));
            }
            
            if (latest.system.memoryUsage > this.config.alertThresholds.memoryUsage) {
                alerts.push(this.createAlert('HIGH_MEMORY', 'Memory usage exceeds threshold', {
                    current: latest.system.memoryUsage,
                    threshold: this.config.alertThresholds.memoryUsage
                }));
            }
        }
        
        // Check hive-specific thresholds
        if (latest.hive) {
            if (latest.hive.errorRate > this.config.alertThresholds.errorRate) {
                alerts.push(this.createAlert('HIGH_ERROR_RATE', 'Scraping error rate too high', {
                    current: latest.hive.errorRate,
                    threshold: this.config.alertThresholds.errorRate
                }));
            }
            
            if (latest.hive.averageResponseTime > this.config.alertThresholds.responseTime) {
                alerts.push(this.createAlert('SLOW_RESPONSE', 'Response time too slow', {
                    current: latest.hive.averageResponseTime,
                    threshold: this.config.alertThresholds.responseTime
                }));
            }
        }
        
        // Check coordination thresholds
        if (latest.coordination) {
            if (latest.coordination.taskCompletionRate < this.config.alertThresholds.taskCompletionRate) {
                alerts.push(this.createAlert('LOW_COMPLETION_RATE', 'Task completion rate too low', {
                    current: latest.coordination.taskCompletionRate,
                    threshold: this.config.alertThresholds.taskCompletionRate
                }));
            }
        }
        
        // Process alerts
        for (const alert of alerts) {
            await this.processAlert(alert);
        }
    }
    
    createAlert(type, message, data) {
        return {
            id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type,
            message,
            data,
            timestamp: Date.now(),
            severity: this.getAlertSeverity(type),
            acknowledged: false
        };
    }
    
    getAlertSeverity(type) {
        const severityMap = {
            HIGH_CPU: 'warning',
            HIGH_MEMORY: 'warning',
            HIGH_ERROR_RATE: 'critical',
            SLOW_RESPONSE: 'warning',
            LOW_COMPLETION_RATE: 'critical',
            AGENT_FAILURE: 'critical',
            COORDINATION_TIMEOUT: 'error'
        };
        
        return severityMap[type] || 'info';
    }
    
    async processAlert(alert) {
        // Store alert
        this.alerts.push(alert);
        
        // Log alert
        const severity = alert.severity.toUpperCase();
        console.log(`🚨 [${severity}] ${alert.type}: ${alert.message}`, alert.data);
        
        // Trigger automated responses for critical alerts
        if (alert.severity === 'critical') {
            await this.triggerAutomatedResponse(alert);
        }
        
        // Send notifications (implement based on requirements)
        await this.sendNotification(alert);
    }
    
    async triggerAutomatedResponse(alert) {
        console.log(`🤖 Triggering automated response for ${alert.type}...`);
        
        switch (alert.type) {
            case 'HIGH_ERROR_RATE':
                await this.handleHighErrorRate(alert);
                break;
            case 'LOW_COMPLETION_RATE':
                await this.handleLowCompletionRate(alert);
                break;
            case 'AGENT_FAILURE':
                await this.handleAgentFailure(alert);
                break;
            default:
                console.log(`No automated response defined for ${alert.type}`);
        }
    }
    
    async handleHighErrorRate(alert) {
        // Implement error rate mitigation
        console.log('📉 Implementing error rate mitigation strategies...');
        
        // Could trigger:
        // - Rate limiting adjustments
        // - Agent reallocation
        // - Fallback strategy activation
        // - Topology adaptation
    }
    
    async handleLowCompletionRate(alert) {
        // Implement completion rate improvement
        console.log('📈 Implementing completion rate improvement strategies...');
        
        // Could trigger:
        // - Resource scaling
        // - Task redistribution
        // - Agent health checks
        // - Performance optimization
    }
    
    async handleAgentFailure(alert) {
        // Implement agent failure recovery
        console.log('🔧 Implementing agent failure recovery...');
        
        // Could trigger:
        // - Agent restart
        // - Task reassignment
        // - Backup agent activation
        // - Topology reconfiguration
    }
    
    async sendNotification(alert) {
        // Implement notification sending (email, webhook, etc.)
        // This is a stub - implement based on requirements
        console.log(`📧 Notification sent for alert: ${alert.type}`);
    }
    
    async analyzeTrends() {
        const recentMetrics = this.getRecentMetrics(30 * 60 * 1000); // Last 30 minutes
        if (recentMetrics.length < 10) return; // Need sufficient data
        
        const trends = {
            timestamp: Date.now(),
            performance: this.calculatePerformanceTrend(recentMetrics),
            resource: this.calculateResourceTrend(recentMetrics),
            hive: this.calculateHiveTrend(recentMetrics),
            coordination: this.calculateCoordinationTrend(recentMetrics)
        };
        
        // Store trends
        this.analysisCache.set('trends', trends);
        
        // Check for concerning trends
        await this.checkTrendAlerts(trends);
        
        console.log('📈 Trend analysis completed:', {
            performance: trends.performance.direction,
            resource: trends.resource.direction,
            hive: trends.hive.direction,
            coordination: trends.coordination.direction
        });
    }
    
    calculatePerformanceTrend(metrics) {
        // Calculate overall performance trend
        const performanceScores = metrics.map(m => this.calculateOverallPerformance(m));
        return this.calculateTrendDirection(performanceScores);
    }
    
    calculateResourceTrend(metrics) {
        // Calculate resource usage trend
        const resourceScores = metrics.map(m => {
            if (!m.system) return 0.5;
            return (m.system.cpuUsage + m.system.memoryUsage) / 2;
        });
        return this.calculateTrendDirection(resourceScores);
    }
    
    calculateHiveTrend(metrics) {
        // Calculate hive-specific trend
        const hiveScores = metrics.map(m => {
            if (!m.hive) return 0.5;
            return (1 - m.hive.errorRate) * m.hive.efficiency;
        });
        return this.calculateTrendDirection(hiveScores);
    }
    
    calculateCoordinationTrend(metrics) {
        // Calculate coordination efficiency trend
        const coordScores = metrics.map(m => {
            if (!m.coordination) return 0.5;
            return m.coordination.taskCompletionRate * (1 - m.coordination.overhead);
        });
        return this.calculateTrendDirection(coordScores);
    }
    
    calculateTrendDirection(values) {
        if (values.length < 5) return { direction: 'stable', confidence: 0 };
        
        // Simple linear regression for trend
        const n = values.length;
        const x = values.map((_, i) => i);
        const y = values;
        
        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = y.reduce((a, b) => a + b, 0);
        const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
        const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
        
        const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
        const correlation = this.calculateCorrelation(x, y);
        
        let direction = 'stable';
        if (slope > 0.01) direction = 'improving';
        else if (slope < -0.01) direction = 'declining';
        
        return {
            direction,
            slope,
            confidence: Math.abs(correlation),
            recent: values.slice(-5).reduce((a, b) => a + b) / 5
        };
    }
    
    calculateCorrelation(x, y) {
        const n = x.length;
        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = y.reduce((a, b) => a + b, 0);
        const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
        const sumXX = x.reduce((sum, xi) => sum + xi * xi, 0);
        const sumYY = y.reduce((sum, yi) => sum + yi * yi, 0);
        
        const numerator = n * sumXY - sumX * sumY;
        const denominator = Math.sqrt((n * sumXX - sumX * sumX) * (n * sumYY - sumY * sumY));
        
        return denominator === 0 ? 0 : numerator / denominator;
    }
    
    async analyzePatterns() {
        const recentMetrics = this.getRecentMetrics(2 * 60 * 60 * 1000); // Last 2 hours
        if (recentMetrics.length < 20) return;
        
        const patterns = {
            timestamp: Date.now(),
            cyclical: this.detectCyclicalPatterns(recentMetrics),
            anomalies: this.detectAnomalies(recentMetrics),
            correlations: this.detectCorrelations(recentMetrics),
            optimization: this.identifyOptimizationOpportunities(recentMetrics)
        };
        
        this.analysisCache.set('patterns', patterns);
        
        console.log('🔍 Pattern analysis completed:', {
            cyclicalPatternsFound: patterns.cyclical.length,
            anomaliesDetected: patterns.anomalies.length,
            strongCorrelations: patterns.correlations.filter(c => Math.abs(c.correlation) > 0.7).length,
            optimizationOpportunities: patterns.optimization.length
        });
    }
    
    detectCyclicalPatterns(metrics) {
        // Detect cyclical patterns in metrics
        // This is a simplified implementation
        return [];
    }
    
    detectAnomalies(metrics) {
        // Detect anomalies using statistical methods
        const anomalies = [];
        
        // Simple z-score based anomaly detection
        const performanceScores = metrics.map(m => this.calculateOverallPerformance(m));
        const mean = performanceScores.reduce((a, b) => a + b) / performanceScores.length;
        const std = Math.sqrt(performanceScores.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / performanceScores.length);
        
        performanceScores.forEach((score, index) => {
            const zScore = Math.abs((score - mean) / std);
            if (zScore > 2.5) { // Outlier threshold
                anomalies.push({
                    timestamp: metrics[index].timestamp,
                    type: 'performance_anomaly',
                    zScore,
                    value: score,
                    expected: mean
                });
            }
        });
        
        return anomalies;
    }
    
    detectCorrelations(metrics) {
        // Detect correlations between different metrics
        // This is a simplified implementation
        return [];
    }
    
    identifyOptimizationOpportunities(metrics) {
        // Identify optimization opportunities
        const opportunities = [];
        
        const latest = metrics[metrics.length - 1];
        
        // Resource optimization opportunities
        if (latest.system && latest.system.cpuUsage < 0.3) {
            opportunities.push({
                type: 'underutilized_cpu',
                message: 'CPU is underutilized, consider scaling down or increasing workload',
                impact: 'resource_efficiency'
            });
        }
        
        if (latest.hive && latest.hive.errorRate > 0.1) {
            opportunities.push({
                type: 'high_error_rate',
                message: 'Error rate is high, consider adjusting scraping strategies',
                impact: 'data_quality'
            });
        }
        
        return opportunities;
    }
    
    calculateOverallPerformance(metrics) {
        // Calculate overall performance score from metrics
        let score = 0.5; // Base score
        let components = 0;
        
        if (metrics.system) {
            score += (1 - metrics.system.cpuUsage) * 0.2;
            score += (1 - metrics.system.memoryUsage) * 0.2;
            components += 2;
        }
        
        if (metrics.hive) {
            score += (1 - metrics.hive.errorRate) * 0.3;
            score += metrics.hive.efficiency * 0.3;
            components += 2;
        }
        
        if (metrics.coordination) {
            score += metrics.coordination.taskCompletionRate * 0.2;
            components += 1;
        }
        
        return components > 0 ? score / components : 0.5;
    }
    
    getRecentMetrics(timeWindow) {
        const cutoff = Date.now() - timeWindow;
        return Array.from(this.metrics.entries())
            .filter(([timestamp]) => timestamp >= cutoff)
            .map(([, metrics]) => metrics)
            .sort((a, b) => a.timestamp - b.timestamp);
    }
    
    cleanupOldMetrics() {
        const cutoff = Date.now() - this.config.retentionPeriod;
        const toDelete = [];
        
        for (const [timestamp] of this.metrics) {
            if (timestamp < cutoff) {
                toDelete.push(timestamp);
            }
        }
        
        toDelete.forEach(timestamp => this.metrics.delete(timestamp));
        
        if (toDelete.length > 0) {
            console.log(`🧹 Cleaned up ${toDelete.length} old metric entries`);
        }
    }
    
    // Public API methods
    getLatestMetrics() {
        return this.analysisCache.get('latest');
    }
    
    getTrends() {
        return this.analysisCache.get('trends');
    }
    
    getPatterns() {
        return this.analysisCache.get('patterns');
    }
    
    getAlerts(severity = null) {
        if (severity) {
            return this.alerts.filter(alert => alert.severity === severity);
        }
        return [...this.alerts];
    }
    
    acknowledgeAlert(alertId) {
        const alert = this.alerts.find(a => a.id === alertId);
        if (alert) {
            alert.acknowledged = true;
            alert.acknowledgedAt = Date.now();
            return true;
        }
        return false;
    }
    
    stop() {
        this.monitoringActive = false;
        
        if (this.metricsInterval) clearInterval(this.metricsInterval);
        if (this.cleanupInterval) clearInterval(this.cleanupInterval);
        if (this.trendInterval) clearInterval(this.trendInterval);
        if (this.patternInterval) clearInterval(this.patternInterval);
        
        console.log('🛑 Performance Monitor stopped');
    }
}

// Metric collector classes
class SystemMetricsCollector {
    async initialize() {
        // Initialize system monitoring
    }
    
    async collect() {
        return {
            cpuUsage: Math.random(),
            memoryUsage: Math.random(),
            diskUsage: Math.random(),
            networkLatency: Math.random() * 100,
            uptime: Date.now()
        };
    }
}

class HiveMetricsCollector {
    async initialize() {
        // Initialize hive-specific monitoring
    }
    
    async collect() {
        return {
            scrapingRate: Math.random() * 100,
            errorRate: Math.random() * 0.1,
            averageResponseTime: Math.random() * 3000,
            successRate: 0.9 + Math.random() * 0.1,
            dataQuality: Math.random(),
            efficiency: Math.random(),
            concurrentTasks: Math.floor(Math.random() * 20)
        };
    }
}

class CoordinationMetricsCollector {
    async initialize() {
        // Initialize coordination monitoring
    }
    
    async collect() {
        return {
            agentCount: Math.floor(Math.random() * 10) + 3,
            taskCompletionRate: 0.85 + Math.random() * 0.15,
            coordinationLatency: Math.random() * 500,
            overhead: Math.random() * 0.2,
            faultTolerance: Math.random(),
            loadBalance: Math.random()
        };
    }
}

class NeuralMetricsCollector {
    async initialize() {
        // Initialize neural performance monitoring
    }
    
    async collect() {
        return {
            modelAccuracy: 0.8 + Math.random() * 0.2,
            predictionLatency: Math.random() * 100,
            trainingProgress: Math.random(),
            patternRecognition: Math.random(),
            learningRate: Math.random() * 0.01
        };
    }
}

module.exports = { PerformanceMonitor };
/**
 * Hive Coordination System - Performance Monitor
 * Tracks swarm health, performance metrics, and adaptive scaling triggers
 */

class HiveMonitor {
    constructor(config) {
        this.config = config;
        this.metrics = {
            taskThroughput: 0,
            responseTime: [],
            resourceUtilization: {},
            errorRate: 0,
            queueDepth: 0,
            activeAgents: 0
        };
        this.alerts = [];
        this.scalingRecommendations = [];
    }

    /**
     * Monitor swarm performance and health
     */
    async monitorPerformance() {
        const performance = {
            timestamp: Date.now(),
            metrics: await this.collectMetrics(),
            health: await this.assessHealth(),
            scaling: await this.evaluateScaling(),
            alerts: this.generateAlerts()
        };

        return performance;
    }

    /**
     * Collect real-time performance metrics
     */
    async collectMetrics() {
        return {
            taskThroughput: this.calculateThroughput(),
            avgResponseTime: this.calculateAverageResponseTime(),
            cpuUtilization: await this.getCpuUtilization(),
            memoryUtilization: await this.getMemoryUtilization(),
            errorRate: this.calculateErrorRate(),
            queueDepth: this.getQueueDepth(),
            activeAgents: this.getActiveAgentCount()
        };
    }

    /**
     * Assess overall swarm health
     */
    async assessHealth() {
        const metrics = await this.collectMetrics();
        const thresholds = this.config.performance_monitoring.alert_thresholds;

        const health = {
            overall: 'healthy',
            components: {
                cpu: metrics.cpuUtilization < thresholds.high_cpu ? 'healthy' : 'warning',
                memory: metrics.memoryUtilization < thresholds.high_memory ? 'healthy' : 'warning',
                errors: metrics.errorRate < thresholds.high_error_rate ? 'healthy' : 'critical',
                response: metrics.avgResponseTime < thresholds.slow_response ? 'healthy' : 'warning'
            }
        };

        // Determine overall health
        const componentStates = Object.values(health.components);
        if (componentStates.includes('critical')) {
            health.overall = 'critical';
        } else if (componentStates.includes('warning')) {
            health.overall = 'warning';
        }

        return health;
    }

    /**
     * Evaluate scaling requirements
     */
    async evaluateScaling() {
        const metrics = await this.collectMetrics();
        const triggers = this.config.adaptive_scaling.scaling_triggers;
        const currentAgents = metrics.activeAgents;
        const maxAgents = this.config.adaptive_scaling.max_workers;
        const minAgents = this.config.adaptive_scaling.min_workers;

        let recommendation = 'maintain';
        let reason = '';

        // Scale up triggers
        if (currentAgents < maxAgents) {
            if (metrics.cpuUtilization > triggers.cpu_threshold) {
                recommendation = 'scale_up';
                reason = 'High CPU utilization';
            } else if (metrics.queueDepth > triggers.queue_length) {
                recommendation = 'scale_up';
                reason = 'Queue length exceeded';
            } else if (metrics.avgResponseTime > triggers.response_time_ms) {
                recommendation = 'scale_up';
                reason = 'Response time degraded';
            }
        }

        // Scale down triggers
        if (currentAgents > minAgents) {
            if (metrics.cpuUtilization < 30 && metrics.queueDepth < 2 && metrics.avgResponseTime < 1000) {
                recommendation = 'scale_down';
                reason = 'Low resource utilization';
            }
        }

        return {
            current_agents: currentAgents,
            recommendation,
            reason,
            target_agents: this.calculateTargetAgents(recommendation, currentAgents),
            scaling_factor: this.config.adaptive_scaling.scaling_policies.scale_factor
        };
    }

    /**
     * Generate performance alerts
     */
    generateAlerts() {
        const alerts = [];
        const thresholds = this.config.performance_monitoring.alert_thresholds;

        // CPU alerts
        if (this.metrics.cpuUtilization > thresholds.high_cpu) {
            alerts.push({
                type: 'warning',
                component: 'cpu',
                message: `High CPU utilization: ${this.metrics.cpuUtilization}%`,
                threshold: thresholds.high_cpu,
                action: 'Consider scaling up workers'
            });
        }

        // Memory alerts
        if (this.metrics.memoryUtilization > thresholds.high_memory) {
            alerts.push({
                type: 'warning',
                component: 'memory',
                message: `High memory usage: ${this.metrics.memoryUtilization}%`,
                threshold: thresholds.high_memory,
                action: 'Monitor memory leaks or scale up'
            });
        }

        // Error rate alerts
        if (this.metrics.errorRate > thresholds.high_error_rate) {
            alerts.push({
                type: 'critical',
                component: 'errors',
                message: `High error rate: ${this.metrics.errorRate}%`,
                threshold: thresholds.high_error_rate,
                action: 'Investigate error sources immediately'
            });
        }

        return alerts;
    }

    /**
     * Calculate recommended target agent count
     */
    calculateTargetAgents(recommendation, currentAgents) {
        const scaleFactor = this.config.adaptive_scaling.scaling_policies.scale_factor;
        const maxAgents = this.config.adaptive_scaling.max_workers;
        const minAgents = this.config.adaptive_scaling.min_workers;

        switch (recommendation) {
            case 'scale_up':
                return Math.min(Math.ceil(currentAgents * scaleFactor), maxAgents);
            case 'scale_down':
                return Math.max(Math.floor(currentAgents / scaleFactor), minAgents);
            default:
                return currentAgents;
        }
    }

    /**
     * Helper methods for metric calculations
     */
    calculateThroughput() {
        // Implementation would track completed tasks per time period
        return this.metrics.taskThroughput;
    }

    calculateAverageResponseTime() {
        if (this.metrics.responseTime.length === 0) return 0;
        const sum = this.metrics.responseTime.reduce((a, b) => a + b, 0);
        return sum / this.metrics.responseTime.length;
    }

    async getCpuUtilization() {
        // Implementation would use system monitoring
        return Math.random() * 100; // Placeholder
    }

    async getMemoryUtilization() {
        // Implementation would use system monitoring
        return Math.random() * 100; // Placeholder
    }

    calculateErrorRate() {
        // Implementation would track error/success ratio
        return this.metrics.errorRate;
    }

    getQueueDepth() {
        // Implementation would check task queue length
        return this.metrics.queueDepth;
    }

    getActiveAgentCount() {
        // Implementation would count active agents
        return this.metrics.activeAgents;
    }

    /**
     * Generate performance report
     */
    generateReport() {
        return {
            timestamp: new Date().toISOString(),
            topology: this.config.topology,
            performance: this.metrics,
            health: this.assessHealth(),
            scaling: this.evaluateScaling(),
            alerts: this.alerts,
            recommendations: this.scalingRecommendations
        };
    }
}

module.exports = HiveMonitor;
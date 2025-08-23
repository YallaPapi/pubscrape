/**
 * Hive Performance Monitoring and Metrics System
 * Tracks system performance, resource utilization, and optimization opportunities
 */

class HivePerformanceMonitor {
  constructor(queenCoordinator, taskDistributor) {
    this.queen = queenCoordinator;
    this.taskDistributor = taskDistributor;
    this.metrics = {
      system: new Map(),
      workers: new Map(),
      tasks: new Map(),
      resources: new Map()
    };
    this.performanceHistory = [];
    this.alertThresholds = {
      cpu_usage: 0.85,
      memory_usage: 0.80,
      task_queue_length: 15,
      response_time: 10000,
      error_rate: 0.1
    };
  }

  /**
   * Initialize performance monitoring
   */
  async initialize() {
    console.log('📊 Initializing Hive Performance Monitor...');
    
    // Start metrics collection
    await this.startMetricsCollection();
    
    // Set up performance analysis
    await this.setupPerformanceAnalysis();
    
    // Initialize alerting system
    await this.initializeAlerting();
    
    console.log('✅ Performance monitoring initialized');
  }

  /**
   * Start continuous metrics collection
   */
  async startMetricsCollection() {
    // Collect system metrics every 30 seconds
    setInterval(async () => {
      await this.collectSystemMetrics();
    }, 30000);
    
    // Collect worker metrics every 10 seconds
    setInterval(async () => {
      await this.collectWorkerMetrics();
    }, 10000);
    
    // Collect task metrics every 5 seconds
    setInterval(async () => {
      await this.collectTaskMetrics();
    }, 5000);
    
    console.log('📈 Metrics collection started');
  }

  /**
   * Collect system-wide performance metrics
   */
  async collectSystemMetrics() {
    const timestamp = Date.now();
    
    // Simulate system resource collection (in real implementation, use actual system APIs)
    const systemMetrics = {
      timestamp,
      cpu_usage: Math.random() * 0.7 + 0.2, // 20-90%
      memory_usage: Math.random() * 0.5 + 0.3, // 30-80%
      network_io: Math.random() * 1000000, // bytes/sec
      disk_io: Math.random() * 500000, // bytes/sec
      total_workers: this.queen.workers.size,
      active_workers: Array.from(this.queen.workers.values()).filter(w => w.status === 'working').length,
      task_queue_length: this.taskDistributor ? this.taskDistributor.taskQueue.length : 0,
      total_tasks_completed: this.taskDistributor ? this.taskDistributor.completedTasks.size : 0
    };
    
    this.metrics.system.set(timestamp, systemMetrics);
    
    // Keep only last hour of system metrics
    this.cleanupOldMetrics(this.metrics.system, 3600000); // 1 hour
    
    // Check for performance alerts
    await this.checkSystemAlerts(systemMetrics);
  }

  /**
   * Collect worker-level performance metrics
   */
  async collectWorkerMetrics() {
    const timestamp = Date.now();
    
    for (const [workerId, worker] of this.queen.workers.entries()) {
      const workerMetrics = {
        timestamp,
        worker_id: workerId,
        caste: worker.caste,
        agent_type: worker.agentType,
        status: worker.status,
        current_task: worker.currentTask?.id,
        tasks_completed: worker.performance.tasksCompleted,
        average_task_time: worker.performance.averageTime,
        success_rate: worker.performance.successRate,
        last_active: worker.performance.lastActive,
        idle_time: worker.status === 'idle' ? timestamp - worker.performance.lastActive : 0,
        specialization_match: this.calculateSpecializationMatch(worker)
      };
      
      // Store worker metrics by worker ID
      if (!this.metrics.workers.has(workerId)) {
        this.metrics.workers.set(workerId, []);
      }
      
      const workerHistory = this.metrics.workers.get(workerId);
      workerHistory.push(workerMetrics);
      
      // Keep only last 30 minutes of worker metrics
      const cutoff = timestamp - 1800000; // 30 minutes
      this.metrics.workers.set(workerId, 
        workerHistory.filter(m => m.timestamp > cutoff)
      );
    }
  }

  /**
   * Calculate how well a worker's assignments match their specialization
   */
  calculateSpecializationMatch(worker) {
    if (!worker.currentTask) return 1.0;
    
    const taskType = worker.currentTask.type;
    const specialization = worker.specialization;
    
    // Simple matching logic (in practice, this would be more sophisticated)
    const matchMap = {
      'data_collection': ['research', 'analysis', 'gathering'],
      'implementation': ['code', 'develop', 'build', 'implement'],
      'quality_assurance': ['test', 'review', 'validate', 'check'],
      'maintenance': ['deploy', 'monitor', 'maintain', 'optimize']
    };
    
    const specKeywords = matchMap[specialization] || [];
    const isMatch = specKeywords.some(keyword => taskType.toLowerCase().includes(keyword));
    
    return isMatch ? 1.0 : 0.5;
  }

  /**
   * Collect task-level performance metrics
   */
  async collectTaskMetrics() {
    if (!this.taskDistributor) return;
    
    const timestamp = Date.now();
    const analytics = this.taskDistributor.getDistributionAnalytics();
    
    const taskMetrics = {
      timestamp,
      total_tasks: analytics.total_tasks,
      queued_tasks: analytics.queued,
      executing_tasks: analytics.executing,
      completed_tasks: analytics.completed,
      average_duration: analytics.average_duration,
      success_rate: analytics.success_rate,
      task_types: analytics.task_types,
      worker_utilization: analytics.worker_utilization,
      queue_wait_time: this.calculateAverageQueueWaitTime(),
      throughput: this.calculateThroughput()
    };
    
    this.metrics.tasks.set(timestamp, taskMetrics);
    
    // Keep only last hour of task metrics
    this.cleanupOldMetrics(this.metrics.tasks, 3600000);
  }

  /**
   * Calculate average queue wait time
   */
  calculateAverageQueueWaitTime() {
    if (!this.taskDistributor || this.taskDistributor.taskQueue.length === 0) {
      return 0;
    }
    
    const now = Date.now();
    const waitTimes = this.taskDistributor.taskQueue.map(task => now - task.created);
    
    return waitTimes.reduce((sum, time) => sum + time, 0) / waitTimes.length;
  }

  /**
   * Calculate system throughput (tasks per minute)
   */
  calculateThroughput() {
    const oneMinuteAgo = Date.now() - 60000;
    const recentCompletions = this.taskDistributor ? 
      this.taskDistributor.taskHistory.filter(h => h.timestamp > oneMinuteAgo).length : 0;
    
    return recentCompletions;
  }

  /**
   * Setup performance analysis and optimization recommendations
   */
  async setupPerformanceAnalysis() {
    // Run performance analysis every 5 minutes
    setInterval(async () => {
      await this.analyzePerformance();
    }, 300000);
    
    console.log('🔍 Performance analysis scheduled');
  }

  /**
   * Analyze performance and generate optimization recommendations
   */
  async analyzePerformance() {
    console.log('🔍 Analyzing hive performance...');
    
    const analysis = {
      timestamp: Date.now(),
      overall_health: 'good',
      bottlenecks: [],
      recommendations: [],
      metrics_summary: this.getMetricsSummary()
    };
    
    // Analyze system bottlenecks
    const systemBottlenecks = this.identifySystemBottlenecks();
    analysis.bottlenecks.push(...systemBottlenecks);
    
    // Analyze worker utilization
    const workerBottlenecks = this.identifyWorkerBottlenecks();
    analysis.bottlenecks.push(...workerBottlenecks);
    
    // Generate recommendations
    analysis.recommendations = this.generateOptimizationRecommendations(analysis.bottlenecks);
    
    // Determine overall health
    analysis.overall_health = this.calculateOverallHealth(analysis);
    
    // Store analysis in performance history
    this.performanceHistory.push(analysis);
    
    // Keep only last 24 hours of performance history
    const dayAgo = Date.now() - 86400000; // 24 hours
    this.performanceHistory = this.performanceHistory.filter(h => h.timestamp > dayAgo);
    
    console.log(`📊 Performance analysis complete - Health: ${analysis.overall_health}`);
    
    // Log critical recommendations
    if (analysis.recommendations.length > 0) {
      console.log('💡 Performance recommendations:');
      analysis.recommendations.forEach(rec => console.log(`   • ${rec}`));
    }
    
    return analysis;
  }

  /**
   * Identify system-level bottlenecks
   */
  identifySystemBottlenecks() {
    const bottlenecks = [];
    const latestSystem = this.getLatestMetrics(this.metrics.system);
    
    if (!latestSystem) return bottlenecks;
    
    // Check CPU usage
    if (latestSystem.cpu_usage > this.alertThresholds.cpu_usage) {
      bottlenecks.push({
        type: 'cpu_overload',
        severity: 'high',
        value: latestSystem.cpu_usage,
        threshold: this.alertThresholds.cpu_usage
      });
    }
    
    // Check memory usage
    if (latestSystem.memory_usage > this.alertThresholds.memory_usage) {
      bottlenecks.push({
        type: 'memory_pressure',
        severity: 'medium',
        value: latestSystem.memory_usage,
        threshold: this.alertThresholds.memory_usage
      });
    }
    
    // Check task queue length
    if (latestSystem.task_queue_length > this.alertThresholds.task_queue_length) {
      bottlenecks.push({
        type: 'queue_backlog',
        severity: 'medium',
        value: latestSystem.task_queue_length,
        threshold: this.alertThresholds.task_queue_length
      });
    }
    
    return bottlenecks;
  }

  /**
   * Identify worker-level bottlenecks
   */
  identifyWorkerBottlenecks() {
    const bottlenecks = [];
    
    // Analyze worker utilization patterns
    const workerUtilization = this.calculateWorkerUtilization();
    
    // Identify underutilized workers
    const underutilized = workerUtilization.filter(w => w.utilization < 0.3);
    if (underutilized.length > 0) {
      bottlenecks.push({
        type: 'worker_underutilization',
        severity: 'low',
        affected_workers: underutilized.length,
        details: underutilized.map(w => ({ id: w.workerId, utilization: w.utilization }))
      });
    }
    
    // Identify overutilized workers
    const overutilized = workerUtilization.filter(w => w.utilization > 0.9);
    if (overutilized.length > 0) {
      bottlenecks.push({
        type: 'worker_overutilization',
        severity: 'medium',
        affected_workers: overutilized.length,
        details: overutilized.map(w => ({ id: w.workerId, utilization: w.utilization }))
      });
    }
    
    return bottlenecks;
  }

  /**
   * Generate optimization recommendations based on bottlenecks
   */
  generateOptimizationRecommendations(bottlenecks) {
    const recommendations = [];
    
    for (const bottleneck of bottlenecks) {
      switch (bottleneck.type) {
        case 'cpu_overload':
          recommendations.push('Consider reducing concurrent task execution or scaling horizontally');
          break;
        case 'memory_pressure':
          recommendations.push('Optimize memory usage or increase system memory allocation');
          break;
        case 'queue_backlog':
          recommendations.push('Scale up worker count in bottleneck castes');
          break;
        case 'worker_underutilization':
          recommendations.push('Consider scaling down or reassigning underutilized workers');
          break;
        case 'worker_overutilization':
          recommendations.push('Scale up workers in overloaded castes');
          break;
        default:
          recommendations.push(`Address ${bottleneck.type} issue`);
      }
    }
    
    return [...new Set(recommendations)]; // Remove duplicates
  }

  /**
   * Calculate worker utilization over recent period
   */
  calculateWorkerUtilization() {
    const utilization = [];
    const thirtyMinutesAgo = Date.now() - 1800000; // 30 minutes
    
    for (const [workerId, workerHistory] of this.metrics.workers.entries()) {
      const recentMetrics = workerHistory.filter(m => m.timestamp > thirtyMinutesAgo);
      
      if (recentMetrics.length === 0) continue;
      
      const workingTime = recentMetrics.filter(m => m.status === 'working').length;
      const utilizationRate = workingTime / recentMetrics.length;
      
      utilization.push({
        workerId,
        utilization: utilizationRate,
        recentActivity: recentMetrics.length
      });
    }
    
    return utilization;
  }

  /**
   * Get latest metrics from a metrics map
   */
  getLatestMetrics(metricsMap) {
    if (metricsMap.size === 0) return null;
    
    const latestTimestamp = Math.max(...metricsMap.keys());
    return metricsMap.get(latestTimestamp);
  }

  /**
   * Get comprehensive metrics summary
   */
  getMetricsSummary() {
    const latestSystem = this.getLatestMetrics(this.metrics.system);
    const latestTask = this.getLatestMetrics(this.metrics.tasks);
    
    return {
      system: latestSystem,
      tasks: latestTask,
      workers: {
        total: this.queen.workers.size,
        by_status: this.getWorkerStatusCounts(),
        by_caste: this.getWorkerCasteCounts(),
        average_utilization: this.calculateAverageUtilization()
      }
    };
  }

  /**
   * Get worker counts by status
   */
  getWorkerStatusCounts() {
    const counts = { idle: 0, working: 0, error: 0, standby: 0 };
    
    for (const worker of this.queen.workers.values()) {
      counts[worker.status] = (counts[worker.status] || 0) + 1;
    }
    
    return counts;
  }

  /**
   * Get worker counts by caste
   */
  getWorkerCasteCounts() {
    const counts = {};
    
    for (const worker of this.queen.workers.values()) {
      counts[worker.caste] = (counts[worker.caste] || 0) + 1;
    }
    
    return counts;
  }

  /**
   * Calculate average worker utilization
   */
  calculateAverageUtilization() {
    const utilization = this.calculateWorkerUtilization();
    
    if (utilization.length === 0) return 0;
    
    const totalUtilization = utilization.reduce((sum, w) => sum + w.utilization, 0);
    return totalUtilization / utilization.length;
  }

  /**
   * Check for system alerts
   */
  async checkSystemAlerts(systemMetrics) {
    const alerts = [];
    
    // CPU alert
    if (systemMetrics.cpu_usage > this.alertThresholds.cpu_usage) {
      alerts.push(`🚨 High CPU usage: ${(systemMetrics.cpu_usage * 100).toFixed(1)}%`);
    }
    
    // Memory alert
    if (systemMetrics.memory_usage > this.alertThresholds.memory_usage) {
      alerts.push(`🚨 High memory usage: ${(systemMetrics.memory_usage * 100).toFixed(1)}%`);
    }
    
    // Queue alert
    if (systemMetrics.task_queue_length > this.alertThresholds.task_queue_length) {
      alerts.push(`🚨 Task queue backlog: ${systemMetrics.task_queue_length} tasks`);
    }
    
    // Log alerts
    alerts.forEach(alert => console.log(alert));
  }

  /**
   * Calculate overall system health score
   */
  calculateOverallHealth(analysis) {
    const criticalBottlenecks = analysis.bottlenecks.filter(b => b.severity === 'high').length;
    const mediumBottlenecks = analysis.bottlenecks.filter(b => b.severity === 'medium').length;
    
    if (criticalBottlenecks > 0) return 'critical';
    if (mediumBottlenecks > 2) return 'degraded';
    if (analysis.bottlenecks.length > 3) return 'fair';
    
    return 'good';
  }

  /**
   * Clean up old metrics to prevent memory leaks
   */
  cleanupOldMetrics(metricsMap, maxAge) {
    const cutoff = Date.now() - maxAge;
    
    for (const [timestamp] of metricsMap.entries()) {
      if (timestamp < cutoff) {
        metricsMap.delete(timestamp);
      }
    }
  }

  /**
   * Get performance status for external monitoring
   */
  getPerformanceStatus() {
    const latest = this.performanceHistory[this.performanceHistory.length - 1];
    
    return {
      last_analysis: latest?.timestamp,
      overall_health: latest?.overall_health || 'unknown',
      active_bottlenecks: latest?.bottlenecks.length || 0,
      pending_recommendations: latest?.recommendations.length || 0,
      metrics_summary: this.getMetricsSummary()
    };
  }
}

module.exports = { HivePerformanceMonitor };
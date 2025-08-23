/**
 * Hive Queen Coordinator - Master orchestration system
 * Manages hierarchical hive topology with specialized worker castes
 */

class HiveQueenCoordinator {
  constructor(config) {
    this.config = config;
    this.workers = new Map();
    this.taskQueue = [];
    this.activeTasksMap = new Map();
    this.performanceMetrics = new Map();
    this.isInitialized = false;
  }

  /**
   * Initialize the hive coordination system
   */
  async initialize() {
    console.log('🐝 Initializing Hive Queen Coordinator...');
    
    // Set up worker castes based on configuration
    await this.initializeWorkerCastes();
    
    // Establish communication channels
    await this.setupCommunicationChannels();
    
    // Start monitoring and health checks
    await this.startMonitoring();
    
    this.isInitialized = true;
    console.log('👑 Hive Queen Coordinator initialized successfully');
    
    return {
      status: 'initialized',
      topology: 'hierarchical-hive',
      workers: this.getWorkerSummary(),
      capabilities: this.getCapabilities()
    };
  }

  /**
   * Initialize specialized worker castes
   */
  async initializeWorkerCastes() {
    const castes = this.config.hive.structure.worker_castes;
    
    for (const [casteName, casteConfig] of Object.entries(castes)) {
      console.log(`🔄 Initializing ${casteName} caste...`);
      
      // Start with minimum workers for each caste
      for (let i = 0; i < casteConfig.min_count; i++) {
        const workerId = await this.spawnWorker(casteName, casteConfig, i);
        console.log(`✅ Spawned ${casteName} worker: ${workerId}`);
      }
    }
  }

  /**
   * Spawn a specialized worker agent
   */
  async spawnWorker(casteName, casteConfig, index) {
    const workerId = `${casteName}-${index}-${Date.now()}`;
    const agentType = casteConfig.agents[index % casteConfig.agents.length];
    
    const worker = {
      id: workerId,
      caste: casteName,
      agentType: agentType,
      specialization: casteConfig.specialization,
      status: 'idle',
      currentTask: null,
      performance: {
        tasksCompleted: 0,
        averageTime: 0,
        successRate: 1.0,
        lastActive: Date.now()
      }
    };
    
    this.workers.set(workerId, worker);
    return workerId;
  }

  /**
   * Delegate task to optimal worker based on specialization
   */
  async delegateTask(task) {
    console.log(`👑 Queen delegating task: ${task.type}`);
    
    // Analyze task to determine optimal caste
    const optimalCaste = this.determineOptimalCaste(task);
    
    // Find available worker in optimal caste
    const worker = this.findAvailableWorker(optimalCaste);
    
    if (!worker) {
      // Scale up if needed
      await this.scaleUpCaste(optimalCaste, task);
      return this.delegateTask(task); // Retry after scaling
    }
    
    // Assign task to worker
    return this.assignTaskToWorker(worker, task);
  }

  /**
   * Determine optimal worker caste for task
   */
  determineOptimalCaste(task) {
    const decisionMatrix = this.config.coordination_protocol.patterns.task_delegation.decision_matrix;
    
    // Map task types to castes
    if (task.type.includes('research') || task.type.includes('data')) {
      return 'foragers';
    }
    if (task.type.includes('implement') || task.type.includes('code')) {
      return 'builders';
    }
    if (task.type.includes('test') || task.type.includes('review')) {
      return 'guardians';
    }
    if (task.type.includes('deploy') || task.type.includes('monitor')) {
      return 'nurses';
    }
    
    // Default to builders for general tasks
    return 'builders';
  }

  /**
   * Find available worker in specified caste
   */
  findAvailableWorker(casteName) {
    const workers = Array.from(this.workers.values())
      .filter(w => w.caste === casteName && w.status === 'idle')
      .sort((a, b) => b.performance.successRate - a.performance.successRate);
    
    return workers[0] || null;
  }

  /**
   * Assign task to specific worker
   */
  async assignTaskToWorker(worker, task) {
    worker.status = 'working';
    worker.currentTask = task;
    worker.performance.lastActive = Date.now();
    
    console.log(`🐝 Assigned task ${task.id} to ${worker.caste} worker ${worker.id}`);
    
    // Store active task mapping
    this.activeTasksMap.set(task.id, worker.id);
    
    // Return assignment details
    return {
      taskId: task.id,
      workerId: worker.id,
      workerCaste: worker.caste,
      agentType: worker.agentType,
      specialization: worker.specialization,
      estimatedCompletion: this.estimateCompletionTime(worker, task)
    };
  }

  /**
   * Adaptive scaling based on metrics
   */
  async adaptiveScale() {
    const metrics = await this.gatherMetrics();
    
    for (const [casteName, casteConfig] of Object.entries(this.config.hive.structure.worker_castes)) {
      const casteMetrics = metrics.castes[casteName];
      
      // Check scale-up conditions
      if (this.shouldScaleUp(casteMetrics, casteConfig)) {
        await this.scaleUpCaste(casteName);
      }
      
      // Check scale-down conditions
      if (this.shouldScaleDown(casteMetrics, casteConfig)) {
        await this.scaleDownCaste(casteName);
      }
    }
  }

  /**
   * Get worker summary for status reporting
   */
  getWorkerSummary() {
    const summary = {
      total: this.workers.size,
      by_caste: {},
      by_status: { idle: 0, working: 0, error: 0 }
    };
    
    for (const worker of this.workers.values()) {
      // Count by caste
      if (!summary.by_caste[worker.caste]) {
        summary.by_caste[worker.caste] = 0;
      }
      summary.by_caste[worker.caste]++;
      
      // Count by status
      summary.by_status[worker.status]++;
    }
    
    return summary;
  }

  /**
   * Get system capabilities
   */
  getCapabilities() {
    return {
      coordination: 'hierarchical-hive',
      specializations: Object.keys(this.config.hive.structure.worker_castes),
      adaptive_scaling: this.config.hive.adaptive_scaling.enabled,
      fault_tolerance: this.config.hive.fault_tolerance.redundancy.critical_roles.length > 0,
      max_workers: this.config.hive.structure.queen.max_workers,
      communication_channels: Object.keys(this.config.hive.communication.channels).length
    };
  }
}

module.exports = { HiveQueenCoordinator };
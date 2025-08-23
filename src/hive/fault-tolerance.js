/**
 * Hive Fault Tolerance and Recovery System
 * Handles worker failures, redundancy, and system resilience
 */

class HiveFaultTolerance {
  constructor(queenCoordinator, config) {
    this.queen = queenCoordinator;
    this.config = config.hive.fault_tolerance;
    this.healthChecks = new Map();
    this.backupWorkers = new Map();
    this.failureHistory = [];
    this.recoveryInProgress = new Set();
  }

  /**
   * Initialize fault tolerance system
   */
  async initialize() {
    console.log('🛡️ Initializing Hive Fault Tolerance System...');
    
    // Set up health monitoring
    await this.startHealthMonitoring();
    
    // Initialize backup workers for critical roles
    await this.initializeBackupWorkers();
    
    // Set up failure detection
    await this.setupFailureDetection();
    
    console.log('✅ Fault tolerance system initialized');
  }

  /**
   * Start continuous health monitoring
   */
  async startHealthMonitoring() {
    setInterval(async () => {
      await this.performHealthChecks();
    }, this.config.health_checks.interval);
    
    console.log(`💓 Health monitoring started (${this.config.health_checks.interval}ms interval)`);
  }

  /**
   * Perform health checks on all workers
   */
  async performHealthChecks() {
    const workers = Array.from(this.queen.workers.values());
    
    for (const worker of workers) {
      try {
        const health = await this.checkWorkerHealth(worker);
        this.updateHealthStatus(worker.id, health);
        
        // Trigger recovery if worker is unhealthy
        if (!health.healthy && !this.recoveryInProgress.has(worker.id)) {
          await this.initiateRecovery(worker);
        }
      } catch (error) {
        console.error(`❌ Health check failed for worker ${worker.id}:`, error.message);
        await this.handleWorkerFailure(worker, error);
      }
    }
  }

  /**
   * Check individual worker health
   */
  async checkWorkerHealth(worker) {
    const health = {
      workerId: worker.id,
      healthy: true,
      issues: [],
      lastSeen: worker.performance.lastActive,
      responseTime: 0,
      taskSuccess: worker.performance.successRate
    };
    
    // Check if worker is responsive
    const pingStart = Date.now();
    try {
      // Simulate ping to worker
      await this.pingWorker(worker);
      health.responseTime = Date.now() - pingStart;
    } catch (error) {
      health.healthy = false;
      health.issues.push('unresponsive');
    }
    
    // Check if worker has been inactive too long
    const inactiveTime = Date.now() - worker.performance.lastActive;
    if (inactiveTime > 300000) { // 5 minutes
      health.healthy = false;
      health.issues.push('inactive');
    }
    
    // Check success rate
    if (worker.performance.successRate < 0.7) {
      health.healthy = false;
      health.issues.push('low_success_rate');
    }
    
    // Check if response time is too high
    if (health.responseTime > this.config.health_checks.timeout) {
      health.healthy = false;
      health.issues.push('slow_response');
    }
    
    return health;
  }

  /**
   * Simulate ping to worker (in real implementation, this would be actual communication)
   */
  async pingWorker(worker) {
    // Simulate network delay and potential failure
    await new Promise(resolve => setTimeout(resolve, Math.random() * 100));
    
    // Simulate 5% failure rate for testing
    if (Math.random() < 0.05) {
      throw new Error('Worker not responding');
    }
    
    return true;
  }

  /**
   * Update health status tracking
   */
  updateHealthStatus(workerId, health) {
    this.healthChecks.set(workerId, {
      ...health,
      timestamp: Date.now()
    });
  }

  /**
   * Initiate recovery for unhealthy worker
   */
  async initiateRecovery(worker) {
    console.log(`🔧 Initiating recovery for worker ${worker.id} (${worker.caste})`);
    
    this.recoveryInProgress.add(worker.id);
    
    try {
      // Attempt to restart worker
      if (this.config.recovery.auto_restart) {
        await this.restartWorker(worker);
      }
      
      // If restart fails or not enabled, replace with backup
      if (!await this.verifyWorkerRecovery(worker)) {
        await this.activateBackupWorker(worker);
      }
      
    } catch (error) {
      console.error(`❌ Recovery failed for worker ${worker.id}:`, error.message);
      await this.escalateFailure(worker, error);
    } finally {
      this.recoveryInProgress.delete(worker.id);
    }
  }

  /**
   * Restart a worker
   */
  async restartWorker(worker) {
    console.log(`🔄 Restarting worker ${worker.id}...`);
    
    // Reset worker state
    worker.status = 'idle';
    worker.currentTask = null;
    worker.performance.lastActive = Date.now();
    
    // Simulate restart delay
    await new Promise(resolve => 
      setTimeout(resolve, this.config.recovery.failover_delay)
    );
    
    console.log(`✅ Worker ${worker.id} restarted`);
  }

  /**
   * Verify worker has recovered
   */
  async verifyWorkerRecovery(worker) {
    try {
      const health = await this.checkWorkerHealth(worker);
      return health.healthy;
    } catch (error) {
      return false;
    }
  }

  /**
   * Activate backup worker to replace failed one
   */
  async activateBackupWorker(failedWorker) {
    console.log(`🔄 Activating backup for failed worker ${failedWorker.id}`);
    
    // Check if backup exists for this caste
    const backupKey = `${failedWorker.caste}-backup`;
    let backup = this.backupWorkers.get(backupKey);
    
    if (!backup) {
      // Create new backup worker
      backup = await this.queen.spawnWorker(
        failedWorker.caste,
        this.getWorkerCasteConfig(failedWorker.caste),
        999 // Special index for backup
      );
      console.log(`➕ Created new backup worker: ${backup}`);
    }
    
    // Transfer any current task from failed worker to backup
    if (failedWorker.currentTask) {
      const backupWorker = this.queen.workers.get(backup);
      if (backupWorker) {
        backupWorker.currentTask = failedWorker.currentTask;
        backupWorker.status = 'working';
        console.log(`📋 Transferred task from ${failedWorker.id} to backup ${backup}`);
      }
    }
    
    // Remove failed worker
    this.queen.workers.delete(failedWorker.id);
    console.log(`🗑️ Removed failed worker ${failedWorker.id}`);
    
    // Update backup tracking
    this.backupWorkers.set(backupKey, null); // Mark backup as used
  }

  /**
   * Initialize backup workers for critical roles
   */
  async initializeBackupWorkers() {
    const criticalRoles = this.config.redundancy.critical_roles;
    const backupCount = this.config.redundancy.backup_count;
    
    for (const role of criticalRoles) {
      for (let i = 0; i < backupCount; i++) {
        const backupKey = `${role}-backup-${i}`;
        
        // Create backup worker but keep it in standby
        const casteConfig = this.getWorkerCasteConfig(role);
        if (casteConfig) {
          const backupId = await this.queen.spawnWorker(role, casteConfig, 900 + i);
          const backupWorker = this.queen.workers.get(backupId);
          if (backupWorker) {
            backupWorker.status = 'standby';
            this.backupWorkers.set(backupKey, backupId);
            console.log(`🛡️ Created backup worker for ${role}: ${backupId}`);
          }
        }
      }
    }
  }

  /**
   * Get worker caste configuration
   */
  getWorkerCasteConfig(casteName) {
    return this.queen.config.hive.structure.worker_castes[casteName];
  }

  /**
   * Handle worker failure
   */
  async handleWorkerFailure(worker, error) {
    console.error(`💥 Worker failure detected: ${worker.id}`, error.message);
    
    // Record failure in history
    this.failureHistory.push({
      workerId: worker.id,
      caste: worker.caste,
      error: error.message,
      timestamp: Date.now(),
      currentTask: worker.currentTask?.id
    });
    
    // Initiate recovery
    await this.initiateRecovery(worker);
  }

  /**
   * Escalate failure to queen coordinator
   */
  async escalateFailure(worker, error) {
    console.error(`🚨 Escalating failure for worker ${worker.id} to queen coordinator`);
    
    // Notify queen of critical failure
    // In real implementation, this would trigger broader recovery actions
    console.log(`👑 Queen notified of critical failure in ${worker.caste} caste`);
    
    // Consider scaling up the caste if multiple failures
    const recentFailures = this.failureHistory
      .filter(f => f.caste === worker.caste && Date.now() - f.timestamp < 300000)
      .length;
    
    if (recentFailures > 2) {
      console.log(`⚡ Multiple failures in ${worker.caste} caste - triggering scaling`);
      // This would trigger adaptive scaling
    }
  }

  /**
   * Get fault tolerance status
   */
  getStatus() {
    const recentFailures = this.failureHistory
      .filter(f => Date.now() - f.timestamp < 3600000) // Last hour
      .length;
    
    return {
      health_monitoring: {
        active: true,
        interval: this.config.health_checks.interval,
        last_check: Math.max(...Array.from(this.healthChecks.values()).map(h => h.timestamp))
      },
      backup_workers: {
        total: this.backupWorkers.size,
        active: Array.from(this.backupWorkers.values()).filter(id => id !== null).length,
        critical_roles_covered: this.config.redundancy.critical_roles.length
      },
      failure_stats: {
        recent_failures: recentFailures,
        total_failures: this.failureHistory.length,
        recovery_in_progress: this.recoveryInProgress.size
      },
      resilience_score: Math.max(0, 1 - (recentFailures / 10)) // Simple scoring
    };
  }
}

module.exports = { HiveFaultTolerance };
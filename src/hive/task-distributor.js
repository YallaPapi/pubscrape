/**
 * Distributed Task Management System for Hive Coordination
 * Handles task queuing, distribution, and dependency management
 */

class HiveTaskDistributor {
  constructor(queenCoordinator) {
    this.queen = queenCoordinator;
    this.taskQueue = [];
    this.dependencyGraph = new Map();
    this.completedTasks = new Set();
    this.taskHistory = [];
  }

  /**
   * Add task with dependency management
   */
  async addTask(task) {
    // Validate task structure
    const validatedTask = this.validateTask(task);
    
    // Add to dependency graph
    this.dependencyGraph.set(validatedTask.id, {
      task: validatedTask,
      dependencies: validatedTask.dependencies || [],
      dependents: [],
      status: 'queued',
      assignedWorker: null,
      startTime: null,
      completionTime: null
    });
    
    // Queue for execution if dependencies are met
    if (this.areDependenciesMet(validatedTask.id)) {
      await this.queueTask(validatedTask);
    }
    
    console.log(`📋 Task added to hive: ${validatedTask.id} (${validatedTask.type})`);
    return validatedTask.id;
  }

  /**
   * Validate and enrich task structure
   */
  validateTask(task) {
    const taskId = task.id || `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    return {
      id: taskId,
      type: task.type || 'general',
      priority: task.priority || 'medium',
      description: task.description || '',
      requirements: task.requirements || [],
      dependencies: task.dependencies || [],
      estimatedDuration: task.estimatedDuration || 300000, // 5 minutes default
      maxRetries: task.maxRetries || 3,
      timeout: task.timeout || 600000, // 10 minutes default
      metadata: task.metadata || {},
      created: Date.now()
    };
  }

  /**
   * Queue task for immediate execution
   */
  async queueTask(task) {
    // Insert task in priority order
    const insertIndex = this.findInsertionIndex(task);
    this.taskQueue.splice(insertIndex, 0, task);
    
    // Attempt immediate assignment if workers available
    await this.processQueue();
  }

  /**
   * Process task queue and assign to available workers
   */
  async processQueue() {
    while (this.taskQueue.length > 0) {
      const task = this.taskQueue[0];
      
      // Check if dependencies are still met
      if (!this.areDependenciesMet(task.id)) {
        break; // Wait for dependencies
      }
      
      // Delegate to queen for worker assignment
      const assignment = await this.queen.delegateTask(task);
      
      if (assignment) {
        // Remove from queue and update dependency graph
        this.taskQueue.shift();
        const graphNode = this.dependencyGraph.get(task.id);
        graphNode.status = 'executing';
        graphNode.assignedWorker = assignment.workerId;
        graphNode.startTime = Date.now();
        
        console.log(`🚀 Task ${task.id} executing on ${assignment.workerCaste} worker`);
      } else {
        // No workers available, wait for scaling or completion
        break;
      }
    }
  }

  /**
   * Mark task as completed and process dependents
   */
  async completeTask(taskId, result) {
    const graphNode = this.dependencyGraph.get(taskId);
    if (!graphNode) {
      throw new Error(`Task ${taskId} not found in dependency graph`);
    }
    
    // Update task status
    graphNode.status = 'completed';
    graphNode.completionTime = Date.now();
    graphNode.result = result;
    
    // Add to completed set
    this.completedTasks.add(taskId);
    
    // Add to history
    this.taskHistory.push({
      taskId,
      duration: graphNode.completionTime - graphNode.startTime,
      worker: graphNode.assignedWorker,
      success: true,
      timestamp: Date.now()
    });
    
    // Update worker performance
    await this.updateWorkerPerformance(graphNode.assignedWorker, true, graphNode.completionTime - graphNode.startTime);
    
    // Process dependent tasks
    await this.processDependents(taskId);
    
    console.log(`✅ Task ${taskId} completed successfully`);
  }

  /**
   * Process tasks that depend on the completed task
   */
  async processDependents(completedTaskId) {
    // Find all tasks that depend on this one
    const dependentTasks = [];
    
    for (const [taskId, node] of this.dependencyGraph.entries()) {
      if (node.dependencies.includes(completedTaskId) && node.status === 'waiting') {
        if (this.areDependenciesMet(taskId)) {
          dependentTasks.push(node.task);
        }
      }
    }
    
    // Queue dependent tasks
    for (const task of dependentTasks) {
      await this.queueTask(task);
    }
  }

  /**
   * Check if all dependencies are met for a task
   */
  areDependenciesMet(taskId) {
    const graphNode = this.dependencyGraph.get(taskId);
    if (!graphNode) return false;
    
    return graphNode.dependencies.every(depId => this.completedTasks.has(depId));
  }

  /**
   * Find optimal insertion index for priority queue
   */
  findInsertionIndex(task) {
    const priorities = { high: 3, medium: 2, low: 1 };
    const taskPriority = priorities[task.priority] || 2;
    
    for (let i = 0; i < this.taskQueue.length; i++) {
      const queuePriority = priorities[this.taskQueue[i].priority] || 2;
      if (taskPriority > queuePriority) {
        return i;
      }
    }
    
    return this.taskQueue.length;
  }

  /**
   * Get task distribution analytics
   */
  getDistributionAnalytics() {
    const analytics = {
      total_tasks: this.dependencyGraph.size,
      queued: this.taskQueue.length,
      executing: 0,
      completed: this.completedTasks.size,
      average_duration: 0,
      success_rate: 0,
      worker_utilization: {},
      task_types: {}
    };
    
    let totalDuration = 0;
    let successCount = 0;
    
    for (const node of this.dependencyGraph.values()) {
      // Count executing tasks
      if (node.status === 'executing') {
        analytics.executing++;
      }
      
      // Calculate averages for completed tasks
      if (node.status === 'completed') {
        totalDuration += (node.completionTime - node.startTime);
        successCount++;
      }
      
      // Count task types
      const type = node.task.type;
      analytics.task_types[type] = (analytics.task_types[type] || 0) + 1;
      
      // Track worker utilization
      if (node.assignedWorker) {
        analytics.worker_utilization[node.assignedWorker] = 
          (analytics.worker_utilization[node.assignedWorker] || 0) + 1;
      }
    }
    
    // Calculate averages
    if (successCount > 0) {
      analytics.average_duration = totalDuration / successCount;
      analytics.success_rate = successCount / this.completedTasks.size;
    }
    
    return analytics;
  }

  /**
   * Update worker performance metrics
   */
  async updateWorkerPerformance(workerId, success, duration) {
    const worker = this.queen.workers.get(workerId);
    if (!worker) return;
    
    const perf = worker.performance;
    
    // Update completion count
    if (success) {
      perf.tasksCompleted++;
    }
    
    // Update average time (moving average)
    if (perf.tasksCompleted === 1) {
      perf.averageTime = duration;
    } else {
      perf.averageTime = (perf.averageTime * (perf.tasksCompleted - 1) + duration) / perf.tasksCompleted;
    }
    
    // Update success rate (moving average)
    const totalAttempts = perf.tasksCompleted; // Simplified for now
    perf.successRate = success ? 
      (perf.successRate * (totalAttempts - 1) + 1) / totalAttempts :
      (perf.successRate * (totalAttempts - 1)) / totalAttempts;
    
    // Update last active time
    perf.lastActive = Date.now();
    
    // Mark worker as idle
    worker.status = 'idle';
    worker.currentTask = null;
  }
}

module.exports = { HiveTaskDistributor };
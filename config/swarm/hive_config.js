/**
 * ⚙️ Hive Configuration - Hierarchical Swarm Settings
 * 
 * Central configuration for the hierarchical hive coordination system.
 * Defines topology, worker specifications, and operational parameters.
 */

const HiveConfig = {
    // Core Hive Settings
    topology: {
        type: 'hierarchical',
        structure: 'tree',
        maxDepth: 3,
        maxWorkers: 15,
        queenCentric: true,
        autoScale: true
    },

    // Queen Coordinator Configuration
    queen: {
        id: 'queen-coordinator',
        maxDirectReports: 8,
        delegationStrategy: 'capability_based',
        escalationThreshold: 1.2, // 20% over estimate
        performanceReviewCycle: 300000, // 5 minutes
        decisionMakingMode: 'centralized'
    },

    // Worker Specifications
    workers: {
        research: {
            emoji: '🔬',
            maxInstances: 4,
            capabilities: [
                'research',
                'analysis', 
                'information_gathering',
                'market_research',
                'competitive_analysis',
                'requirements_analysis'
            ],
            specializations: ['technical', 'market', 'competitive', 'academic'],
            maxConcurrentTasks: 3,
            estimatedTaskDuration: '2-6 hours',
            qualityGates: ['fact_checking', 'source_validation']
        },
        
        coder: {
            emoji: '💻',
            maxInstances: 6,
            capabilities: [
                'code_generation',
                'testing',
                'optimization',
                'review',
                'debugging',
                'refactoring'
            ],
            specializations: ['frontend', 'backend', 'fullstack', 'devops'],
            languages: ['javascript', 'typescript', 'python', 'java', 'go'],
            frameworks: ['react', 'node', 'express', 'jest', 'docker'],
            maxConcurrentTasks: 2,
            estimatedTaskDuration: '1-8 hours',
            qualityGates: ['code_review', 'testing', 'security_scan']
        },

        analyst: {
            emoji: '📊',
            maxInstances: 3,
            capabilities: [
                'data_analysis',
                'performance_monitoring',
                'reporting',
                'metrics',
                'visualization',
                'insights'
            ],
            specializations: ['performance', 'business', 'technical', 'financial'],
            tools: ['charts', 'dashboards', 'reports', 'alerts'],
            maxConcurrentTasks: 4,
            estimatedTaskDuration: '1-4 hours',
            qualityGates: ['data_validation', 'statistical_significance']
        },

        tester: {
            emoji: '🧪',
            maxInstances: 4,
            capabilities: [
                'testing',
                'validation',
                'quality_assurance',
                'compliance',
                'security_testing',
                'performance_testing'
            ],
            specializations: ['unit', 'integration', 'e2e', 'performance', 'security'],
            testTypes: ['functional', 'non_functional', 'regression', 'acceptance'],
            maxConcurrentTasks: 3,
            estimatedTaskDuration: '2-6 hours',
            qualityGates: ['test_coverage', 'test_execution', 'defect_resolution']
        }
    },

    // Task Management
    tasks: {
        priorityLevels: ['critical', 'high', 'medium', 'low'],
        defaultPriority: 'medium',
        maxTaskDuration: '24 hours',
        optimalTaskSize: '2-8 hours',
        breakdownThreshold: '16 hours',
        escalationTriggers: {
            durationOverrun: 1.2, // 20% over estimate
            qualityIssues: 'failed_gates',
            resourceConstraints: 0.9 // 90% utilization
        },
        statusUpdateFrequency: 300000 // 5 minutes
    },

    // Communication Protocols
    communication: {
        statusReporting: {
            frequency: 300000, // 5 minutes
            format: 'structured_json',
            requiredFields: [
                'worker_id',
                'status', 
                'current_tasks',
                'performance_metrics',
                'estimated_completion'
            ],
            escalationThreshold: 1.2
        },

        coordination: {
            syncPoints: ['milestone_review', 'daily_standup', 'sprint_planning'],
            handoffValidation: true,
            dependencyTracking: true,
            progressCheckpoints: ['25%', '50%', '75%', '100%'],
            communicationChannels: ['direct', 'broadcast', 'escalation']
        },

        protocols: {
            heartbeatInterval: 60000, // 1 minute
            timeoutThreshold: 30000, // 30 seconds
            retryAttempts: 3,
            messagingFormat: 'json',
            compressionEnabled: true
        }
    },

    // Performance Monitoring
    monitoring: {
        metricsCollection: {
            systemMetrics: [
                'throughput',
                'latency', 
                'error_rate',
                'cpu_usage',
                'memory_usage',
                'network_io'
            ],
            workerMetrics: [
                'task_completion_rate',
                'average_task_duration',
                'worker_utilization',
                'queue_depth',
                'worker_efficiency'
            ],
            qualityMetrics: [
                'defect_rate',
                'rework_percentage',
                'compliance_score',
                'customer_satisfaction',
                'test_coverage'
            ]
        },

        alertThresholds: {
            completionRate: 0.95,
            defectRate: 0.05,
            utilizationMax: 0.90,
            latencyMax: 200, // milliseconds
            errorRateMax: 0.02,
            queueDepthMax: 25
        },

        reportingIntervals: {
            realtime: 10000, // 10 seconds
            performance: 60000, // 1 minute  
            health: 30000, // 30 seconds
            bottleneck: 300000, // 5 minutes
            comprehensive: 3600000 // 1 hour
        }
    },

    // Fault Tolerance & Recovery
    faultTolerance: {
        workerFailureHandling: {
            maxRetries: 3,
            retryDelay: 5000, // 5 seconds
            backoffMultiplier: 2,
            autoRespawn: true,
            taskRedistribution: true
        },

        selfHealing: {
            enabled: true,
            healthCheckInterval: 30000, // 30 seconds
            recoveryAttempts: 3,
            escalationDelay: 60000, // 1 minute
            automaticScaling: true
        },

        redundancy: {
            criticalTaskDuplication: true,
            workerBackups: 'cross_training',
            dataReplication: 'memory_sync',
            failoverTime: 10000 // 10 seconds
        },

        circuitBreaker: {
            failureThreshold: 5,
            recoveryTimeout: 30000, // 30 seconds
            halfOpenRetryDelay: 10000 // 10 seconds
        }
    },

    // Resource Management
    resources: {
        allocation: {
            strategy: 'capability_based',
            loadBalancing: 'round_robin_weighted',
            resourcePooling: true,
            dynamicScaling: true
        },

        limits: {
            maxMemoryPerWorker: '2GB',
            maxCPUPerWorker: '2 cores',
            maxNetworkBandwidth: '100Mbps',
            maxStoragePerWorker: '10GB'
        },

        optimization: {
            autoOptimization: true,
            optimizationInterval: 3600000, // 1 hour
            resourceRebalancing: true,
            performanceTuning: true
        }
    },

    // Security & Compliance
    security: {
        authentication: {
            required: true,
            method: 'token_based',
            tokenExpiration: 3600000, // 1 hour
            refreshTokens: true
        },

        authorization: {
            rbac: true, // Role-based access control
            permissions: ['read', 'write', 'execute', 'admin'],
            taskLevelSecurity: true
        },

        audit: {
            logging: true,
            logLevel: 'info',
            auditTrail: true,
            complianceReporting: true
        },

        dataProtection: {
            encryption: 'AES-256',
            dataClassification: true,
            sensitiveDataHandling: 'restricted',
            gdprCompliant: true
        }
    },

    // Integration & APIs
    integration: {
        apis: {
            restAPI: true,
            webhooks: true,
            graphQL: false,
            streaming: true
        },

        external: {
            github: true,
            slack: false,
            jira: false,
            monitoring: true
        },

        protocols: {
            http: true,
            websockets: true,
            grpc: false,
            mqtt: false
        }
    },

    // Development & Testing
    development: {
        environment: 'production',
        debugMode: false,
        verboseLogging: false,
        testMode: false,
        mockServices: false
    },

    // Operational Parameters
    operational: {
        startup: {
            autoStart: true,
            warmupTime: 30000, // 30 seconds
            healthCheckDelay: 10000, // 10 seconds
            initialWorkerCount: 4
        },

        runtime: {
            maxUptime: 86400000, // 24 hours (then restart)
            maintenanceWindow: '02:00-04:00 UTC',
            backupInterval: 3600000, // 1 hour
            logRotationInterval: 86400000 // 24 hours
        },

        shutdown: {
            gracefulShutdown: true,
            shutdownTimeout: 30000, // 30 seconds
            taskCompletionWait: true,
            statePreservation: true
        }
    }
};

// Configuration Validation
function validateConfig(config) {
    const errors = [];

    // Validate worker limits
    Object.entries(config.workers).forEach(([type, spec]) => {
        if (spec.maxInstances > config.topology.maxWorkers) {
            errors.push(`Worker type ${type} maxInstances exceeds topology maxWorkers`);
        }
    });

    // Validate monitoring thresholds
    if (config.monitoring.alertThresholds.completionRate > 1) {
        errors.push('Completion rate threshold cannot exceed 100%');
    }

    // Validate timeout values
    if (config.faultTolerance.selfHealing.healthCheckInterval < 10000) {
        errors.push('Health check interval too frequent (min 10 seconds)');
    }

    return {
        isValid: errors.length === 0,
        errors
    };
}

// Configuration Export
module.exports = {
    HiveConfig,
    validateConfig,
    
    // Helper functions
    getWorkerConfig: (type) => HiveConfig.workers[type],
    getMonitoringConfig: () => HiveConfig.monitoring,
    getCommunicationConfig: () => HiveConfig.communication,
    getFaultToleranceConfig: () => HiveConfig.faultTolerance,
    
    // Dynamic configuration updates
    updateWorkerLimit: (type, limit) => {
        if (HiveConfig.workers[type]) {
            HiveConfig.workers[type].maxInstances = limit;
        }
    },
    
    updateThreshold: (metric, value) => {
        if (HiveConfig.monitoring.alertThresholds[metric] !== undefined) {
            HiveConfig.monitoring.alertThresholds[metric] = value;
        }
    }
};
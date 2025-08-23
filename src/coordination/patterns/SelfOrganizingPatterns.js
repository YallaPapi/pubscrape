/**
 * Self-Organizing Patterns for Hive Adaptive Coordination
 * Implements emergent behavior patterns and autonomous optimization
 */

class SelfOrganizingPatterns {
    constructor(config = {}) {
        this.config = {
            emergenceThreshold: 0.7, // Threshold for pattern emergence
            adaptationRate: 0.1, // Rate of pattern adaptation
            stabilityWindow: 10, // Number of iterations to consider for stability
            maxPatterns: 50, // Maximum number of patterns to track
            pruningThreshold: 0.3, // Threshold for pattern pruning
            ...config
        };
        
        this.patterns = new Map();
        this.patternHistory = [];
        this.emergentBehaviors = new Map();
        this.adaptationMetrics = new Map();
        
        // Pattern types and their characteristics
        this.patternTypes = new Map([
            ['coordination', { weight: 0.8, complexity: 0.6 }],
            ['workload', { weight: 0.7, complexity: 0.5 }],
            ['communication', { weight: 0.6, complexity: 0.4 }],
            ['resource', { weight: 0.9, complexity: 0.7 }],
            ['failure_recovery', { weight: 0.9, complexity: 0.8 }]
        ]);
        
        this.initialize();
    }
    
    async initialize() {
        console.log('🌱 Initializing Self-Organizing Patterns...');
        
        // Initialize pattern recognition engine
        this.patternRecognizer = new PatternRecognizer(this.config);
        
        // Initialize emergence detector
        this.emergenceDetector = new EmergenceDetector(this.config);
        
        // Initialize adaptation engine
        this.adaptationEngine = new AdaptationEngine(this.config);
        
        // Start pattern evolution loop
        this.startPatternEvolution();
        
        console.log('✅ Self-Organizing Patterns initialized');
    }
    
    startPatternEvolution() {
        // Main pattern evolution loop
        this.evolutionInterval = setInterval(async () => {
            try {
                await this.evolvePatterns();
            } catch (error) {
                console.error('❌ Error in pattern evolution:', error);
            }
        }, 30000); // Every 30 seconds
        
        // Pattern pruning and optimization
        this.optimizationInterval = setInterval(async () => {
            try {
                await this.optimizePatterns();
            } catch (error) {
                console.error('❌ Error in pattern optimization:', error);
            }
        }, 5 * 60 * 1000); // Every 5 minutes
    }
    
    async evolvePatterns() {
        const currentState = await this.collectSystemState();
        
        // Detect new patterns
        const newPatterns = await this.patternRecognizer.detectPatterns(currentState);
        
        // Check for emergent behaviors
        const emergentBehaviors = await this.emergenceDetector.detectEmergence(currentState, this.patterns);
        
        // Adapt existing patterns
        await this.adaptExistingPatterns(currentState);
        
        // Integrate new patterns
        await this.integratePatterns(newPatterns, emergentBehaviors);
        
        // Update pattern stability metrics
        this.updateStabilityMetrics();
        
        console.log('🔄 Pattern evolution cycle completed:', {
            totalPatterns: this.patterns.size,
            newPatterns: newPatterns.length,
            emergentBehaviors: emergentBehaviors.length,
            averageStability: this.calculateAverageStability()
        });
    }
    
    async collectSystemState() {
        // Collect comprehensive system state for pattern analysis
        return {
            timestamp: Date.now(),
            
            // Agent states
            agents: await this.getAgentStates(),
            
            // Task states
            tasks: await this.getTaskStates(),
            
            // Communication patterns
            communications: await this.getCommunicationPatterns(),
            
            // Resource utilization
            resources: await this.getResourceUtilization(),
            
            // Performance metrics
            performance: await this.getPerformanceMetrics(),
            
            // Network topology
            topology: await this.getCurrentTopology(),
            
            // Environmental factors
            environment: await this.getEnvironmentalFactors()
        };
    }
    
    async adaptExistingPatterns(currentState) {
        for (const [patternId, pattern] of this.patterns) {
            try {
                const adaptedPattern = await this.adaptationEngine.adaptPattern(pattern, currentState);
                
                if (adaptedPattern && this.isPatternImproved(pattern, adaptedPattern)) {
                    this.patterns.set(patternId, adaptedPattern);
                    this.recordPatternAdaptation(patternId, pattern, adaptedPattern);
                }
            } catch (error) {
                console.warn(`⚠️ Failed to adapt pattern ${patternId}:`, error);
            }
        }
    }
    
    async integratePatterns(newPatterns, emergentBehaviors) {
        // Integrate new patterns
        for (const pattern of newPatterns) {
            if (this.shouldIntegratePattern(pattern)) {
                const patternId = this.generatePatternId(pattern);
                this.patterns.set(patternId, pattern);
                console.log(`✨ New pattern integrated: ${pattern.type} - ${pattern.description}`);
            }
        }
        
        // Integrate emergent behaviors
        for (const behavior of emergentBehaviors) {
            if (this.shouldIntegrateEmergentBehavior(behavior)) {
                const behaviorId = this.generateBehaviorId(behavior);
                this.emergentBehaviors.set(behaviorId, behavior);
                console.log(`🌟 Emergent behavior detected: ${behavior.type} - ${behavior.description}`);
                
                // Convert stable emergent behaviors to patterns
                if (behavior.stability > this.config.emergenceThreshold) {
                    const pattern = this.convertBehaviorToPattern(behavior);
                    const patternId = this.generatePatternId(pattern);
                    this.patterns.set(patternId, pattern);
                }
            }
        }
    }
    
    shouldIntegratePattern(pattern) {
        // Check if pattern meets integration criteria
        return (
            pattern.confidence > 0.6 &&
            pattern.utility > 0.5 &&
            !this.isDuplicatePattern(pattern) &&
            this.patterns.size < this.config.maxPatterns
        );
    }
    
    shouldIntegrateEmergentBehavior(behavior) {
        return (
            behavior.strength > 0.5 &&
            behavior.novelty > 0.4 &&
            !this.isDuplicateBehavior(behavior)
        );
    }
    
    isDuplicatePattern(newPattern) {
        for (const existingPattern of this.patterns.values()) {
            if (this.calculatePatternSimilarity(newPattern, existingPattern) > 0.8) {
                return true;
            }
        }
        return false;
    }
    
    isDuplicateBehavior(newBehavior) {
        for (const existingBehavior of this.emergentBehaviors.values()) {
            if (this.calculateBehaviorSimilarity(newBehavior, existingBehavior) > 0.8) {
                return true;
            }
        }
        return false;
    }
    
    calculatePatternSimilarity(pattern1, pattern2) {
        // Calculate similarity between patterns
        if (pattern1.type !== pattern2.type) return 0;
        
        let similarity = 0;
        let factors = 0;
        
        // Compare features
        if (pattern1.features && pattern2.features) {
            const commonFeatures = pattern1.features.filter(f => 
                pattern2.features.some(f2 => f2.name === f.name)
            );
            similarity += (commonFeatures.length / Math.max(pattern1.features.length, pattern2.features.length)) * 0.4;
            factors += 0.4;
        }
        
        // Compare triggers
        if (pattern1.triggers && pattern2.triggers) {
            const commonTriggers = pattern1.triggers.filter(t => 
                pattern2.triggers.includes(t)
            );
            similarity += (commonTriggers.length / Math.max(pattern1.triggers.length, pattern2.triggers.length)) * 0.3;
            factors += 0.3;
        }
        
        // Compare outcomes
        if (pattern1.outcomes && pattern2.outcomes) {
            const outcomesSimilarity = this.compareOutcomes(pattern1.outcomes, pattern2.outcomes);
            similarity += outcomesSimilarity * 0.3;
            factors += 0.3;
        }
        
        return factors > 0 ? similarity / factors : 0;
    }
    
    calculateBehaviorSimilarity(behavior1, behavior2) {
        // Simple behavior similarity calculation
        if (behavior1.type !== behavior2.type) return 0;
        
        const contextSimilarity = this.compareContexts(behavior1.context, behavior2.context);
        const effectSimilarity = this.compareEffects(behavior1.effects, behavior2.effects);
        
        return (contextSimilarity + effectSimilarity) / 2;
    }
    
    compareOutcomes(outcomes1, outcomes2) {
        // Compare pattern outcomes
        const keys = new Set([...Object.keys(outcomes1), ...Object.keys(outcomes2)]);
        let similarity = 0;
        
        for (const key of keys) {
            const val1 = outcomes1[key] || 0;
            const val2 = outcomes2[key] || 0;
            similarity += 1 - Math.abs(val1 - val2);
        }
        
        return keys.size > 0 ? similarity / keys.size : 0;
    }
    
    compareContexts(context1, context2) {
        // Compare behavior contexts
        return Math.random() * 0.5 + 0.25; // Stub implementation
    }
    
    compareEffects(effects1, effects2) {
        // Compare behavior effects
        return Math.random() * 0.5 + 0.25; // Stub implementation
    }
    
    isPatternImproved(original, adapted) {
        // Check if adapted pattern is better than original
        return (
            adapted.confidence > original.confidence ||
            adapted.utility > original.utility ||
            adapted.stability > original.stability
        );
    }
    
    recordPatternAdaptation(patternId, original, adapted) {
        if (!this.adaptationMetrics.has(patternId)) {
            this.adaptationMetrics.set(patternId, []);
        }
        
        this.adaptationMetrics.get(patternId).push({
            timestamp: Date.now(),
            originalUtility: original.utility,
            adaptedUtility: adapted.utility,
            improvementRatio: adapted.utility / original.utility,
            adaptationType: this.classifyAdaptationType(original, adapted)
        });
    }
    
    classifyAdaptationType(original, adapted) {
        // Classify the type of adaptation that occurred
        if (adapted.confidence > original.confidence + 0.1) return 'confidence_boost';
        if (adapted.stability > original.stability + 0.1) return 'stability_improvement';
        if (adapted.utility > original.utility + 0.1) return 'utility_enhancement';
        return 'minor_refinement';
    }
    
    convertBehaviorToPattern(behavior) {
        // Convert emergent behavior to formal pattern
        return {
            id: this.generatePatternId(),
            type: behavior.type,
            description: `Pattern derived from emergent behavior: ${behavior.description}`,
            features: behavior.features || [],
            triggers: behavior.triggers || [],
            outcomes: behavior.effects || {},
            confidence: behavior.strength,
            utility: behavior.benefit || 0.5,
            stability: behavior.stability,
            origin: 'emergent_behavior',
            timestamp: Date.now()
        };
    }
    
    async optimizePatterns() {
        console.log('🔧 Optimizing patterns...');
        
        // Prune ineffective patterns
        await this.prunePatterns();
        
        // Merge similar patterns
        await this.mergePatterns();
        
        // Enhance successful patterns
        await this.enhancePatterns();
        
        // Update pattern rankings
        this.updatePatternRankings();
        
        console.log('✅ Pattern optimization completed');
    }
    
    async prunePatterns() {
        const patternsToPrune = [];
        
        for (const [patternId, pattern] of this.patterns) {
            if (this.shouldPrunePattern(pattern)) {
                patternsToPrune.push(patternId);
            }
        }
        
        for (const patternId of patternsToPrune) {
            this.patterns.delete(patternId);
            console.log(`🗑️ Pruned ineffective pattern: ${patternId}`);
        }
    }
    
    shouldPrunePattern(pattern) {
        const age = Date.now() - pattern.timestamp;
        const maxAge = 24 * 60 * 60 * 1000; // 24 hours
        
        return (
            pattern.utility < this.config.pruningThreshold ||
            pattern.confidence < 0.3 ||
            (age > maxAge && pattern.stability < 0.4)
        );
    }
    
    async mergePatterns() {
        const patternArray = Array.from(this.patterns.entries());
        const toMerge = [];
        
        for (let i = 0; i < patternArray.length; i++) {
            for (let j = i + 1; j < patternArray.length; j++) {
                const [id1, pattern1] = patternArray[i];
                const [id2, pattern2] = patternArray[j];
                
                const similarity = this.calculatePatternSimilarity(pattern1, pattern2);
                if (similarity > 0.7) {
                    toMerge.push([id1, id2, pattern1, pattern2]);
                }
            }
        }
        
        for (const [id1, id2, pattern1, pattern2] of toMerge) {
            const mergedPattern = this.mergePatternPair(pattern1, pattern2);
            const newId = this.generatePatternId(mergedPattern);
            
            this.patterns.delete(id1);
            this.patterns.delete(id2);
            this.patterns.set(newId, mergedPattern);
            
            console.log(`🔗 Merged similar patterns: ${id1} + ${id2} -> ${newId}`);
        }
    }
    
    mergePatternPair(pattern1, pattern2) {
        // Merge two similar patterns into one improved pattern
        return {
            id: this.generatePatternId(),
            type: pattern1.type,
            description: `Merged pattern: ${pattern1.description} + ${pattern2.description}`,
            features: [...new Set([...(pattern1.features || []), ...(pattern2.features || [])])],
            triggers: [...new Set([...(pattern1.triggers || []), ...(pattern2.triggers || [])])],
            outcomes: this.mergeOutcomes(pattern1.outcomes, pattern2.outcomes),
            confidence: Math.max(pattern1.confidence, pattern2.confidence),
            utility: (pattern1.utility + pattern2.utility) / 2,
            stability: (pattern1.stability + pattern2.stability) / 2,
            origin: 'pattern_merge',
            timestamp: Date.now()
        };
    }
    
    mergeOutcomes(outcomes1, outcomes2) {
        const merged = { ...outcomes1 };
        
        for (const [key, value] of Object.entries(outcomes2)) {
            if (merged[key] !== undefined) {
                merged[key] = (merged[key] + value) / 2;
            } else {
                merged[key] = value;
            }
        }
        
        return merged;
    }
    
    async enhancePatterns() {
        // Enhance patterns that show good performance
        for (const [patternId, pattern] of this.patterns) {
            if (pattern.utility > 0.8 && pattern.stability > 0.7) {
                const enhancedPattern = await this.enhancePattern(pattern);
                if (enhancedPattern) {
                    this.patterns.set(patternId, enhancedPattern);
                    console.log(`⚡ Enhanced high-performing pattern: ${patternId}`);
                }
            }
        }
    }
    
    async enhancePattern(pattern) {
        // Apply enhancements to successful patterns
        const enhanced = { ...pattern };
        
        // Boost confidence for stable patterns
        if (pattern.stability > 0.8) {
            enhanced.confidence = Math.min(1, enhanced.confidence * 1.1);
        }
        
        // Improve utility through learning
        const adaptationHistory = this.adaptationMetrics.get(pattern.id) || [];
        if (adaptationHistory.length > 0) {
            const avgImprovement = adaptationHistory.reduce((sum, a) => sum + a.improvementRatio, 0) / adaptationHistory.length;
            if (avgImprovement > 1.1) {
                enhanced.utility = Math.min(1, enhanced.utility * 1.05);
            }
        }
        
        enhanced.timestamp = Date.now();
        return enhanced;
    }
    
    updatePatternRankings() {
        // Update pattern rankings based on performance
        const rankedPatterns = Array.from(this.patterns.entries())
            .map(([id, pattern]) => ({
                id,
                pattern,
                score: this.calculatePatternScore(pattern)
            }))
            .sort((a, b) => b.score - a.score);
        
        console.log('📊 Top performing patterns:', rankedPatterns.slice(0, 5).map(p => ({
            type: p.pattern.type,
            utility: p.pattern.utility.toFixed(3),
            confidence: p.pattern.confidence.toFixed(3),
            score: p.score.toFixed(3)
        })));
    }
    
    calculatePatternScore(pattern) {
        // Calculate overall pattern score
        const weights = {
            utility: 0.4,
            confidence: 0.3,
            stability: 0.2,
            age: 0.1
        };
        
        const age = Date.now() - pattern.timestamp;
        const ageScore = Math.max(0, 1 - (age / (7 * 24 * 60 * 60 * 1000))); // Decay over 7 days
        
        return (
            pattern.utility * weights.utility +
            pattern.confidence * weights.confidence +
            pattern.stability * weights.stability +
            ageScore * weights.age
        );
    }
    
    updateStabilityMetrics() {
        // Update stability metrics for all patterns
        for (const [patternId, pattern] of this.patterns) {
            const history = this.getPatternHistory(patternId);
            if (history.length >= this.config.stabilityWindow) {
                const stability = this.calculatePatternStability(history);
                pattern.stability = stability;
            }
        }
    }
    
    getPatternHistory(patternId) {
        // Get pattern performance history
        return this.patternHistory.filter(entry => entry.patternId === patternId);
    }
    
    calculatePatternStability(history) {
        // Calculate pattern stability from history
        if (history.length < 2) return 0.5;
        
        const utilities = history.map(h => h.utility);
        const mean = utilities.reduce((a, b) => a + b) / utilities.length;
        const variance = utilities.reduce((sum, u) => sum + Math.pow(u - mean, 2), 0) / utilities.length;
        
        // Lower variance = higher stability
        return Math.max(0, 1 - variance * 2);
    }
    
    calculateAverageStability() {
        const stabilities = Array.from(this.patterns.values()).map(p => p.stability || 0.5);
        return stabilities.length > 0 ? stabilities.reduce((a, b) => a + b) / stabilities.length : 0.5;
    }
    
    generatePatternId(pattern) {
        const timestamp = Date.now();
        const type = pattern?.type || 'unknown';
        const random = Math.random().toString(36).substr(2, 6);
        return `pattern-${type}-${timestamp}-${random}`;
    }
    
    generateBehaviorId(behavior) {
        const timestamp = Date.now();
        const type = behavior?.type || 'unknown';
        const random = Math.random().toString(36).substr(2, 6);
        return `behavior-${type}-${timestamp}-${random}`;
    }
    
    // Stub methods for data collection (would integrate with actual systems)
    async getAgentStates() { return []; }
    async getTaskStates() { return []; }
    async getCommunicationPatterns() { return []; }
    async getResourceUtilization() { return {}; }
    async getPerformanceMetrics() { return {}; }
    async getCurrentTopology() { return 'mesh'; }
    async getEnvironmentalFactors() { return {}; }
    
    // Public API methods
    getPatterns(type = null) {
        if (type) {
            return Array.from(this.patterns.values()).filter(p => p.type === type);
        }
        return Array.from(this.patterns.values());
    }
    
    getEmergentBehaviors() {
        return Array.from(this.emergentBehaviors.values());
    }
    
    getPatternMetrics() {
        return {
            totalPatterns: this.patterns.size,
            emergentBehaviors: this.emergentBehaviors.size,
            averageStability: this.calculateAverageStability(),
            patternTypes: this.getPatternTypeDistribution(),
            adaptationRate: this.calculateAdaptationRate()
        };
    }
    
    getPatternTypeDistribution() {
        const distribution = {};
        for (const pattern of this.patterns.values()) {
            distribution[pattern.type] = (distribution[pattern.type] || 0) + 1;
        }
        return distribution;
    }
    
    calculateAdaptationRate() {
        const recentAdaptations = Array.from(this.adaptationMetrics.values())
            .flat()
            .filter(a => Date.now() - a.timestamp < 60 * 60 * 1000); // Last hour
        
        return recentAdaptations.length;
    }
    
    stop() {
        if (this.evolutionInterval) clearInterval(this.evolutionInterval);
        if (this.optimizationInterval) clearInterval(this.optimizationInterval);
        
        console.log('🛑 Self-Organizing Patterns stopped');
    }
}

// Supporting classes (simplified implementations)
class PatternRecognizer {
    constructor(config) {
        this.config = config;
    }
    
    async detectPatterns(systemState) {
        // Detect patterns in system state
        const patterns = [];
        
        // Simple pattern detection examples
        if (systemState.agents && systemState.agents.length > 0) {
            patterns.push(this.detectCoordinationPattern(systemState));
            patterns.push(this.detectWorkloadPattern(systemState));
        }
        
        return patterns.filter(p => p !== null);
    }
    
    detectCoordinationPattern(state) {
        // Detect coordination patterns
        return {
            type: 'coordination',
            description: 'Agent coordination pattern detected',
            features: ['high_collaboration', 'efficient_communication'],
            triggers: ['task_complexity_increase'],
            outcomes: { efficiency: 0.8, latency: 0.3 },
            confidence: Math.random() * 0.4 + 0.6,
            utility: Math.random() * 0.4 + 0.5,
            stability: Math.random() * 0.3 + 0.4,
            timestamp: Date.now()
        };
    }
    
    detectWorkloadPattern(state) {
        // Detect workload patterns
        return {
            type: 'workload',
            description: 'Workload distribution pattern detected',
            features: ['load_balancing', 'dynamic_allocation'],
            triggers: ['resource_constraint'],
            outcomes: { throughput: 0.7, utilization: 0.8 },
            confidence: Math.random() * 0.4 + 0.6,
            utility: Math.random() * 0.4 + 0.5,
            stability: Math.random() * 0.3 + 0.4,
            timestamp: Date.now()
        };
    }
}

class EmergenceDetector {
    constructor(config) {
        this.config = config;
    }
    
    async detectEmergence(currentState, existingPatterns) {
        // Detect emergent behaviors
        const behaviors = [];
        
        // Simple emergence detection
        if (Math.random() > 0.8) { // 20% chance of detecting emergence
            behaviors.push({
                type: 'adaptive_coordination',
                description: 'Emergent adaptive coordination behavior',
                strength: Math.random() * 0.5 + 0.5,
                novelty: Math.random() * 0.6 + 0.4,
                stability: Math.random() * 0.4 + 0.3,
                context: currentState,
                effects: { coordination_improvement: 0.3 },
                timestamp: Date.now()
            });
        }
        
        return behaviors;
    }
}

class AdaptationEngine {
    constructor(config) {
        this.config = config;
    }
    
    async adaptPattern(pattern, currentState) {
        // Adapt pattern based on current state
        const adapted = { ...pattern };
        
        // Simple adaptation logic
        const performanceChange = (Math.random() - 0.5) * 0.2;
        adapted.utility = Math.max(0, Math.min(1, adapted.utility + performanceChange));
        
        if (performanceChange > 0) {
            adapted.confidence = Math.min(1, adapted.confidence + 0.05);
        }
        
        adapted.timestamp = Date.now();
        
        return adapted;
    }
}

module.exports = { SelfOrganizingPatterns };
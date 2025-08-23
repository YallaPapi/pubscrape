# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

## 📋 Agent Coordination Protocol

### ONLY USE MCP TOOLS - NO HOOKS

**Available MCP Tools:**
- `mcp__claude-flow__swarm_init` - Initialize swarm topology
- `mcp__claude-flow__agent_spawn` - Spawn specialized agents
- `mcp__claude-flow__task_orchestrate` - Coordinate task execution
- `mcp__claude-flow__swarm_status` - Check swarm health
- `mcp__claude-flow__agent_list` - List active agents
- `mcp__claude-flow__memory_usage` - Memory operations

**IMPORTANT:** Hook commands (npx claude-flow@alpha hooks) DO NOT EXIST and will cause errors. Only use the MCP tools listed above via the Task tool system.

## Research Protocol

**CRITICAL:** Always use TaskMaster research instead of WebSearch for information gathering:
- TaskMaster research is faster and more efficient
- WebSearch is too slow for coordination systems
- Use Task tool with `researcher` subagent_type for all research needs

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `swarm-init`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### Testing & Validation
`tdd-london-swarm`, `production-validator`, `code-verification-auditor`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

## 🎯 Concurrent Execution Examples

### ✅ CORRECT (Single Message):
```javascript
// Initialize swarm AND spawn agents AND create todos ALL AT ONCE
Task("swarm-init", "Initialize hive topology...")
Task("hierarchical-coordinator", "Setup queen-led structure...")  
Task("researcher", "Analyze project requirements...")
TodoWrite([5-10 todos batched together])
```

### ❌ WRONG (Multiple Messages):
```javascript
Message 1: Task("swarm-init")
Message 2: Task("researcher") 
Message 3: TodoWrite(single todo)
// This breaks parallel coordination!
```

---

Remember: **Claude Flow coordinates, Claude Code creates!**
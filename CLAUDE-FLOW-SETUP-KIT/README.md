# 🚀 Claude Flow Setup Kit

Everything you need to get Claude Flow working on any new project.

## 📦 What's in this kit:

1. **`CLAUDE.md`** - Copy to your project root (REQUIRED)
2. **`CLAUDE-FLOW-SETUP-GUIDE.md`** - Complete setup instructions
3. **`claude-flow-config.yaml`** - Configuration template
4. **`claude-flow-quick-test.js`** - Test script to verify it works

## ⚡ Quick Setup (5 minutes):

1. **Copy `CLAUDE.md` to your new project root**
2. **Install MCP server:**
   ```bash
   claude mcp add claude-flow npx claude-flow@alpha mcp start
   ```
3. **Test it works:**
   ```
   Initialize a simple swarm with one researcher agent to test Claude Flow functionality.
   ```

## ✅ Success = No hook errors, Task tool calls work

## 🆘 If it fails:
- Read the full setup guide
- Check MCP server status: `claude mcp list`
- Never use hook commands - they don't exist

---

Based on successful implementation achieving:
- 84.8% task success rate
- 2.8-4.4x speed improvements
- Full hive coordination
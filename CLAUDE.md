## **CLAUDE OPERATIONS MANUAL — YouTuber Contact Discovery Agent**

### **Scope**

This manual details operational processes, error recovery cycles, AI tool usage, and research methodology for developing, maintaining, and extending the **YouTuber Contact Discovery Agent**.

***

### **System Overview**

The Agent is a fully automated pipeline:

1. Accepts a **podcast topic/niche query**
2. Fetches public YouTube channel data via YouTube Data API
3. Scores candidates with LLM per guest scoring rules
4. Generates personalized outreach email per guest
5. Compiles results into CSV matching the outreach schema
6. Uploads CSV to Google Drive and returns share link

***

### **Mandatory Problem-Solving Methodology**

**Never create stripped-down or “test-only” builds except for isolated component debugging.**  
- Always start from the current main codebase.
- If error occurs:
  1. Begin **Error Cycle**:
      - Research via TaskMaster
      - Retrieve docs/usages via Context7 (includes YouTube API, Google Drive, AI SDKs, CSV)
      - Apply fix and retest
  2. Repeat until fixed or max **20 cycles**
- Each unique error gets a 20-cycle budget; escalate as "Blocked" if unresolved

***

### **Session Startup Checklist**

1. Confirm codebase is up-to-date
2. Load all required environment variables:
   - `YOUTUBE_API_KEY`
   - `OPENAI_API_KEY` or equivalent
   - `GOOGLE_DRIVE_CREDENTIALS`
3. Test:
   - YouTube API connectivity
   - Guest scoring output format
   - CSV generation (sample data)
   - Drive upload flow
4. Open TaskMaster and load project task list
5. Review previous session’s Blocked tasks

***

### **TaskMaster Integration**

**Core Commands:**
```bash
task-master init
task-master parse-prd docs/prd.txt --research
task-master list
task-master next
task-master show 
task-master set-status --id= --status=done
task-master research "YouTube Data API quota error"
task-master research "CSV schema field order mismatch"
```
_All technical fixes must be researched via TaskMaster—no direct searching for solutions._

***

### **Context7 Integration**

Use Context7 for:

- YouTube Data API endpoint docs
- Google Drive API reference and examples
- AI SDK function signatures & prompt patterns
- CSV library usage/recipes

***

### **Development Rules**

1. Preserve **exact CSV field order** as per project schema.
2. Keep AI prompts identical to standard unless explicitly updating.
3. Output must be valid CSV—no JSON or text substitution.
4. Never hardcode API keys/secrets—always use environment variables.
5. Always test smallest viable data sample before scaling.

***

### **Error Recovery Workflow**

1. Identify the failing step (Channel fetch, Normalization, Scoring, Email, CSV, Drive).
2. Begin fix cycle:
   - TaskMaster research
   - Context7 documentation/examples
   - Apply fix, retest
   - Log cycle count per error
3. After 20 cycles, escalate

***

### **Escalation Triggers**

- Persistent API failure after 20 cycles
- LLM prompt ignored after repeated adjustments
- CSV generation repeatedly broken
- Google Drive upload repeatedly fails

***

**This manual must be followed exactly for all work on the YouTuber Contact Discovery Agent.**

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md

- The project is not production ready until it works E2E with no errors
- ALWAYS ALWAYS ALWAYS use taskmaster research instead of websearch, NEVER USE WEBSEARCH
- Any time you finish doing something and are waiting for my input, give me a list of all the remaining tasks/subtasks and what % of the project has been completed so far
- ALWAYS ALWAYS ALWAYS use taskmaster research, never use web search. There are custom agents that can help you with this
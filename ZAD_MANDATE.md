
## **ZAD MANDATE — YouTuber Contact Discovery Agent**

### **Purpose**

This mandate defines the principles, rules, and constraints for all work on the **YouTuber Contact Discovery Agent** — a system automating:

1. YouTube channel data extraction using Google API (YouTube Data API)
2. AI-driven podcast guest scoring
3. Personalized outreach email generation
4. CSV compilation & Google Drive upload

The Agent executes a code-first pipeline, keeping all schema, prompts, and logic compatible with its original outreach workflow.

***

### **Core-First Mandate**

- **No minimal builds, no reduced scope.**
  Work only on the core Agent codebase unless isolated component tests are explicitly necessary.
- The system must run **end-to-end**:  
  `Query → Channel Fetch → Guest Score → Email Draft → CSV → Drive upload`
- The CSV output must match exactly:
  ```
  ChannelName, ChannelID, ChannelDescription, Website, SocialLinks, SubscriberCount, GuestScore, ScoreReason, DraftEmail
  ```

***

### **Error Handling Protocol**

- Every error gets up to **20 fix cycles** before escalation.
- **Cycle Definition:**
  1. Identify error
  2. Research via TaskMaster
  3. Pull relevant references via Context7
  4. Apply fix
  5. Retest
- Escalate as “Blocked” after 20 unsuccessful cycles.

***

### **Core System Components**

- **Channel Data Fetcher** — Uses YouTube Data API for public channel info
- **Data Normalizer** — Replaces nulls with `"NA"`, sanitizes fields, preserves schema order
- **Guest Scorer (AI)** — Scores each channel with defined podcast suitability rules
- **Email Drafter (AI)** — Generates personalized outreach emails based on score reasoning
- **CSV Compiler** — Builds CSV output in defined schema
- **Drive Uploader** — Uploads CSV to configured Google Drive folder

***

### **Development Rules**

1. No unrelated features—only those supporting the defined podcast outreach workflow.
2. No breaking schema—all CSVs must remain compatible and correctly ordered.
3. Credentials isolation—API keys/OAuth tokens set ONLY via environment variables.
4. Prompt integrity—AI scoring and email prompts must follow original standards.
5. Testing discipline—test components in isolation before full end-to-end runs.

***

### **Escalation Criteria**

- Blocked YouTube API connection after 20 fix cycles
- AI model fails to follow prompt format
- Google Drive upload produces incorrect link or fails authentication

***

**This mandate is binding for all work on the YouTuber Contact Discovery Agent project.**

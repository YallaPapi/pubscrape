# Available Podcast Data for Enrichment

## From iTunes API
- **Podcast name & artist/host name**
- **Description** (short and long form)
- **Release date** (when podcast started)
- **Track count** (total episodes)
- **Country & language**
- **Genre categories** (e.g., Technology, Science)
- **Content rating** (explicit/clean)
- **Artwork URLs** (multiple sizes)
- **RSS feed URL**
- **Apple Podcasts URL**

## From RSS Feed Parsing

### Podcast-Level Data
- **Detailed description/about section** (often 500+ words)
- **Author/host full name and email**
- **Copyright information**
- **Language**
- **Website URL**
- **Publishing platform** (e.g., Blubrry, Libsyn)
- **iTunes categories and keywords**
- **Owner contact info**
- **Last updated date**

### Episode-Level Data (can analyze recent episodes)
- **Episode titles** (often contain guest names)
- **Episode descriptions** (detailed show notes, often 200-500 words)
- **Guest names** (extracted from titles/descriptions)
- **Publication dates**
- **Episode duration**
- **Season/episode numbers**
- **Links mentioned in episodes**
- **Topics discussed**

### Calculated Metrics
- **Total episode count**
- **Publishing frequency** (e.g., weekly, bi-weekly)
- **Latest episode date** (how active they are)
- **Average episode length**
- **Episode release patterns**
- **Guest frequency** (how often they have guests)

## Example Data from Lex Fridman Podcast

**From iTunes:**
- 478 total episodes
- Started: 2018
- Genre: Technology/Science
- Country: USA

**From RSS:**
- Description: "Conversations about AI, science, technology, history, philosophy and the nature of intelligence, consciousness, love, and power"
- Email: lexfridman@gmail.com
- Website: https://lexfridman.com/
- Recent guests: Keyu Jin (China economist), Jack Weatherford (Mongol Empire historian)
- Publishing frequency: ~weekly
- Episode length: 1-3 hours typically

## What We Can Use for AI Email Personalization

1. **Recent guest analysis** - Reference their recent guests and topics
2. **Publishing schedule** - Know when they typically release episodes
3. **Show format** - Understand if it's interview-based, solo, panel, etc.
4. **Topic expertise** - Use their description and recent episodes to understand their focus
5. **Tone/style** - Analyze descriptions to match their communication style
6. **Engagement metrics** - Use episode count and frequency to gauge their commitment level
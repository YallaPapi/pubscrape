# Rate Limit Analysis for 50,000 Podcasts

## iTunes API Constraint: 20 requests/minute

### Time Requirements

**For 50,000 podcasts:**
- Each request returns max 200 podcasts
- Need 250 requests minimum (50,000 ÷ 200)
- At 20 requests/minute = **12.5 minutes just for iTunes API**

**Actual needs (with genre/search diversity):**
- 20 genres × 200 results = 4,000 podcasts (20 requests)
- 30 search terms × 200 results = 6,000 podcasts (30 requests)
- Total: ~50 requests = **2.5 minutes for 10,000 podcasts**
- For 50,000 unique podcasts: ~250 requests = **12.5 minutes**

### RSS Feed Parsing (No API limit)
- Can run in parallel (10-20 threads)
- 50,000 feeds ÷ 10 threads = 5,000 per thread
- At 2 feeds/second per thread = ~40 minutes

### Total Time Estimate
- **iTunes API**: 12.5 minutes
- **RSS Parsing**: 40 minutes (parallel)
- **Total**: ~1 hour for 50,000 podcasts

## Optimization Strategies

### 1. Batch Processing
```python
# Process in chunks to avoid memory issues
CHUNK_SIZE = 5000  # Process 5k at a time
for chunk in chunks(podcasts, CHUNK_SIZE):
    process_chunk(chunk)
    save_intermediate_results()
```

### 2. Resume Capability
```python
# Save progress to resume if interrupted
checkpoint = {
    'last_search_term': 'technology',
    'podcasts_processed': 15000,
    'timestamp': '2024-01-20 10:30:00'
}
```

### 3. Caching
- Cache iTunes API responses (podcasts don't change often)
- Skip RSS feeds parsed in last 7 days
- Store email/website mappings for known podcasts

### 4. Priority Filtering
Focus on high-value podcasts:
- Episode count > 10 (active podcasts)
- Last episode < 30 days (currently active)
- High rankings in their category

## Recommended Approach for Production

1. **Start with top 5,000-10,000 podcasts** (most valuable)
   - Time: ~30 minutes
   - Covers most popular shows
   
2. **Incremental expansion**
   - Add 10,000 more each day
   - Build cache over time
   
3. **Smart filtering**
   - Skip podcasts with no episodes in 6+ months
   - Skip podcasts with < 5 episodes
   - Focus on English-language first

4. **Database instead of CSV**
   - Use SQLite for better performance
   - Track last_scraped timestamp
   - Avoid re-processing
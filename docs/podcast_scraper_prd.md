# Podcast Host Contact Scraper - PRD

## **Product Overview**

Build a **100% free, open-source** scraper that finds contact information for popular podcast hosts who would be interested in AI services and cross-promotion opportunities.

## **Business Objectives**

1. **Cross-Promotion**: Get podcast hosts with large audiences on your show
2. **AI Service Sales**: Target hosts interested in AI tools/services  
3. **SEO/Traffic**: Leverage search volume around popular podcast hosts
4. **Network Growth**: Build relationships with influential podcasters

## **Target Users**

- **Primary**: Podcast creators seeking high-profile guests
- **Secondary**: AI service providers targeting influential podcasters
- **Tertiary**: Marketing agencies booking podcast appearances

## **Success Metrics**

- **Contact Success Rate**: 85%+ of scraped hosts have valid contact info
- **Response Rate**: 10%+ response rate to outreach emails
- **Data Quality**: 95%+ accuracy on podcast metadata
- **Scale**: Ability to process 1,000+ podcasts per search

## **Technical Requirements**

### **Core Features**

1. **Multi-Platform Podcast Discovery**
   - Apple Podcasts directory scraping
   - Spotify podcast discovery
   - Google Podcasts search results
   - PodcastAddict/Stitcher directories

2. **Host Contact Extraction**
   - Scrape podcast website contact pages
   - Extract emails from show notes/descriptions
   - Find social media profiles (Twitter, LinkedIn)
   - Identify booking agents/management companies

3. **Podcast Intelligence Gathering**
   - Download numbers/popularity metrics
   - Episode frequency and consistency
   - Guest types and interview style
   - AI/tech topic relevance scoring

4. **Contact Enrichment**
   - Cross-reference multiple sources
   - Validate email addresses (format checking)
   - Find alternative contact methods
   - Rate contact quality/confidence

### **Data Schema**

```json
{
  "podcast_name": "The AI Podcast",
  "host_name": "John Smith", 
  "host_email": "john@aipodcast.com",
  "podcast_website": "https://aipodcast.com",
  "contact_page_url": "https://aipodcast.com/contact",
  "booking_email": "booking@aipodcast.com",
  "social_links": {
    "twitter": "@johnsmith_ai",
    "linkedin": "linkedin.com/in/johnsmith",
    "instagram": "@johnsmith"
  },
  "podcast_metrics": {
    "estimated_downloads": "50000",
    "episode_count": "150",
    "frequency": "Weekly",
    "rating": "4.8"
  },
  "ai_relevance_score": 85,
  "contact_confidence": "High",
  "last_updated": "2025-08-19"
}
```

### **Free/Open Source Technology Stack**

1. **Web Scraping**: Botasaurus (anti-detection, free)
2. **Podcast APIs**: 
   - Apple Podcasts RSS feeds (free)
   - Spotify Web API (free tier: 100 requests/hour)
   - Google Podcasts search (free via web scraping)
3. **Email Validation**: Python `email-validator` library (free)
4. **Data Storage**: CSV output (free)
5. **AI Scoring**: Use existing OpenAI API from main project

### **Scraping Strategy**

**Phase 1: Podcast Discovery**
```python
# Free sources for podcast discovery:
- Apple Podcasts charts (top podcasts by category)
- Spotify podcast search results  
- Google search: "AI podcast" + "business podcast" etc.
- PodcastAddict directory (web scraping)
- Stitcher browse pages
```

**Phase 2: Website Discovery**
```python
# From podcast metadata, find websites:
- RSS feed <link> tags
- Podcast description URLs
- Host social media bios
- Apple/Spotify "More Info" links
```

**Phase 3: Contact Extraction**
```python
# Scrape websites for contact info:
- /contact pages
- /about pages  
- /booking pages
- Footer email addresses
- Contact forms (capture form action URLs)
```

**Phase 4: Social Media Enrichment**
```python
# Find additional contact methods:
- Twitter bio links and DMs
- LinkedIn messaging
- Instagram business contact buttons
- YouTube channel about pages
```

## **Implementation Plan**

### **Phase 1: Core Scraper (Week 1)**
- Build Apple Podcasts scraper
- Build basic website contact extraction
- Create CSV output format
- Basic error handling

### **Phase 2: Multi-Platform (Week 2)**  
- Add Spotify podcast scraping
- Add Google Podcasts search
- Implement social media discovery
- Add contact confidence scoring

### **Phase 3: Intelligence & Enrichment (Week 3)**
- Add AI relevance scoring
- Implement download estimation
- Add guest type analysis
- Build contact validation

### **Phase 4: Scale & Polish (Week 4)**
- Optimize for bulk processing
- Add retry logic and error recovery
- Implement duplicate detection
- Build reporting dashboard

## **Free Resource Requirements**

### **APIs Needed**
1. **Spotify Web API** - FREE (100 requests/hour)
   - Sign up: https://developer.spotify.com/
   - No credit card required
   
2. **Apple Podcasts** - FREE (RSS feeds)
   - No API key needed, direct RSS access
   
3. **Google Custom Search** - FREE (100 searches/day)
   - Sign up: https://developers.google.com/custom-search
   - Used for podcast website discovery

### **No Setup Required**
- Botasaurus (already installed)
- Python email validation libraries
- CSV export functionality
- Web scraping capabilities

## **Legal & Ethical Considerations**

1. **Public Data Only**: Only scrape publicly available information
2. **Rate Limiting**: Respect website rate limits and robots.txt
3. **Contact Consent**: Target podcasters who want guest bookings
4. **Data Usage**: For legitimate business outreach only
5. **Compliance**: Follow GDPR/privacy best practices

## **Risk Mitigation**

### **Technical Risks**
- **Site Changes**: Multiple data sources reduce single point of failure
- **Rate Limits**: Built-in delays and retry logic
- **Anti-Bot Measures**: Botasaurus handles detection avoidance

### **Business Risks**  
- **Low Response Rates**: Target high-quality, relevant podcasters
- **Outdated Contacts**: Regular re-scraping and validation
- **Legal Issues**: Only use public data and legitimate outreach

## **Success Criteria**

### **MVP Success**
- [ ] Scrape 100+ podcasts from Apple Podcasts
- [ ] Extract contact info for 85%+ of podcasts
- [ ] Generate clean CSV output
- [ ] Process query in under 10 minutes

### **Full Success**
- [ ] Multi-platform scraping (Apple, Spotify, Google)
- [ ] 1,000+ podcasts per search query
- [ ] 90%+ contact extraction success rate
- [ ] AI relevance scoring functional
- [ ] Social media enrichment working

## **Future Enhancements**

1. **Advanced Filtering**
   - Download thresholds
   - Geography targeting
   - Guest history analysis

2. **CRM Integration**
   - Export to HubSpot/Salesforce
   - Email sequence automation
   - Response tracking

3. **AI Enhancement**
   - Personalized pitch generation
   - Optimal outreach timing
   - Success prediction modeling

## **Competitive Advantage**

1. **100% Free**: No subscription costs like PodcastGuests.com ($99/mo)
2. **Comprehensive**: Multiple platforms vs single sources
3. **AI-Enhanced**: Relevance scoring and pitch generation
4. **Fresh Data**: Real-time scraping vs stale databases
5. **Open Source**: Customizable for specific needs

---

**Ready to build! This will be the ultimate free podcast host contact finder.** 🎙️
# VRSEN Lead Generation System - Integration Guide

## Overview

This guide explains how to set up and use the integrated FastAPI backend that bridges the React frontend with the existing Python lead generation system.

## Architecture

```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────┐    Python API    ┌─────────────────┐
│   React         │ ◄─────────────────► │   FastAPI        │ ◄──────────────► │   Lead          │
│   Frontend      │                     │   Backend        │                  │   Generation    │
│                 │                     │                  │                  │   Engine        │
└─────────────────┘                     └──────────────────┘                  └─────────────────┘
                                                │                                        │
                                                ▼                                        ▼
                                        ┌──────────────────┐                  ┌─────────────────┐
                                        │   SQLite         │                  │   Botasaurus    │
                                        │   Database       │                  │   Scraping      │
                                        │                  │                  │                 │
                                        └──────────────────┘                  └─────────────────┘
```

## Features

- **Real-time Campaign Execution**: WebSocket-based progress updates
- **Persistent Storage**: SQLite database for campaigns and leads
- **Email Validation**: Mailtester Ninja API integration with fallback
- **File Management**: CSV export and download functionality
- **Campaign Management**: Full CRUD operations with status tracking
- **Lead Management**: Filtering, search, bulk operations
- **Analytics**: Campaign performance metrics and reporting

## Quick Start

### 1. Install Dependencies

```bash
pip install -r integrated_requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, set MAILTESTER_API_KEY if you have one
```

### 3. Start the Backend

```bash
python start_integrated_backend.py
```

The backend will start on `http://localhost:8000` by default.

### 4. Verify Installation

Visit the API documentation at: `http://localhost:8000/docs`

Test the health endpoint: `http://localhost:8000/api/health`

### 5. Configure Frontend

In your React frontend, set the API base URL:

```bash
# In frontend/.env
VITE_API_BASE_URL=http://localhost:8000/api
```

## API Endpoints

### Campaign Management

- `GET /api/campaigns` - List campaigns with pagination and filtering
- `POST /api/campaigns` - Create new campaign
- `GET /api/campaigns/{id}` - Get specific campaign
- `POST /api/campaigns/{id}/start` - Start campaign execution
- `POST /api/campaigns/{id}/pause` - Pause running campaign
- `POST /api/campaigns/{id}/stop` - Stop campaign
- `DELETE /api/campaigns/{id}` - Delete campaign

### Lead Management

- `GET /api/leads` - List leads with filtering and search
- `GET /api/leads/{id}` - Get specific lead
- `PATCH /api/leads/{id}` - Update lead
- `DELETE /api/leads/{id}` - Delete lead
- `PATCH /api/leads/bulk` - Bulk update leads
- `DELETE /api/leads/bulk` - Bulk delete leads

### Export and Analytics

- `POST /api/campaigns/{id}/export` - Export campaign leads
- `GET /api/download/{filename}` - Download exported files
- `GET /api/campaigns/{id}/analytics` - Get campaign analytics
- `GET /api/campaigns/{id}/logs` - Get campaign execution logs

### System

- `GET /api/health` - Health check
- `GET /api/metrics` - System metrics
- `GET /api/settings` - Get system settings
- `PATCH /api/settings` - Update system settings

### WebSocket

- `WS /ws` - Real-time updates and notifications

## Database Schema

### Campaigns Table
- `id` - UUID primary key
- `name` - Campaign name
- `description` - Campaign description  
- `business_types` - JSON array of target business types
- `location` - Target location
- `search_queries` - JSON array of search queries
- `status` - Campaign status (draft, running, paused, completed, error)
- `progress_data` - JSON object with progress information
- `settings` - JSON object with campaign settings
- `created_at`, `updated_at`, `started_at`, `completed_at` - Timestamps

### Leads Table
- `id` - UUID primary key
- `campaign_id` - Foreign key to campaigns table
- `name`, `email`, `phone`, `company`, `website` - Basic contact info
- `business_name`, `industry`, `specialty` - Business details
- `confidence`, `lead_score`, `email_confidence` - Quality metrics
- `status` - Lead status (pending, contacted, qualified, disqualified)
- `validation_details` - JSON object with email validation results
- `created_at`, `updated_at` - Timestamps

## WebSocket Messages

### Subscribing to Campaign Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to specific campaign
ws.send(JSON.stringify({
    type: "subscribe_campaign",
    campaign_id: "your-campaign-id"
}));

// Handle messages
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'campaign_progress':
            // Update progress UI
            updateProgress(message.progress);
            break;
        case 'campaign_completed':
            // Handle completion
            handleCompletion(message);
            break;
        case 'campaign_log':
            // Show log message
            showLog(message);
            break;
    }
};
```

## Email Validation

The system integrates with Mailtester Ninja for email validation:

### Configuration

```bash
# Set in .env file
MAILTESTER_API_KEY=your_api_key_here
```

### Fallback Mode

If no API key is provided, the system uses basic format validation as a fallback.

### Validation Results

Each lead gets the following validation fields:
- `email_confidence` - Confidence score (0.0 to 1.0)
- `email_validation_status` - Status (valid, invalid, risky, error)
- `validation_details` - Detailed validation information

## Campaign Execution Flow

1. **Create Campaign**: Use the frontend or API to create a campaign
2. **Start Campaign**: Triggers background execution
3. **Search Phase**: Scrapes search results using Botasaurus
4. **Extraction Phase**: Extracts contact information from URLs
5. **Validation Phase**: Validates emails using Mailtester Ninja
6. **Storage Phase**: Saves leads to database
7. **Export Phase**: Generates CSV file
8. **Completion**: Campaign marked as completed

## Error Handling

The system includes comprehensive error handling:

- **Database Errors**: Automatic retry and fallback
- **Scraping Errors**: Individual URL failures don't stop the campaign
- **API Errors**: Graceful fallback for email validation
- **WebSocket Errors**: Automatic reconnection in frontend

## Production Deployment

### Environment Variables

```bash
# Production settings
HOST=0.0.0.0
PORT=8000
RELOAD=false
LOG_LEVEL=warning
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=your_production_secret_key
```

### Database

For production, consider using PostgreSQL:

```bash
pip install psycopg2-binary
DATABASE_URL=postgresql://username:password@localhost/vrsen_leads
```

### Reverse Proxy

Use nginx or similar for production:

```nginx
server {
    listen 80;
    server_name your-api-domain.com;
    
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Ensure database exists and is accessible
   - Check file permissions for SQLite

2. **WebSocket Connection Issues**
   - Verify CORS settings
   - Check firewall/proxy configuration
   - Ensure WebSocket support in browser

3. **Campaign Execution Failures**
   - Check logs in `logs/` directory
   - Verify Botasaurus dependencies
   - Ensure internet connectivity

4. **Email Validation Issues**
   - Verify MAILTESTER_API_KEY
   - Check API quotas and limits
   - Fallback validation should work without API key

### Debugging

Enable debug logging:

```bash
LOG_LEVEL=debug python start_integrated_backend.py
```

Check logs:
```bash
tail -f logs/integrated_backend_*.log
```

## Frontend Integration

### React Hook Example

```typescript
import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api';

export function useCampaign(campaignId: string) {
  const [campaign, setCampaign] = useState(null);
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    // Fetch campaign details
    apiClient.getCampaign(campaignId)
      .then(response => setCampaign(response.data));

    // Setup WebSocket for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: "subscribe_campaign",
        campaign_id: campaignId
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'campaign_progress') {
        setProgress(message.progress);
      }
    };

    return () => ws.close();
  }, [campaignId]);

  return { campaign, progress };
}
```

## Testing

### Unit Tests

```bash
pytest tests/
```

### Integration Tests

```bash
# Test with real API calls
pytest tests/integration/ --api-key=your_test_key
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load_test.py --host=http://localhost:8000
```

## Support

For issues or questions:
1. Check the logs first
2. Review this documentation
3. Create an issue in the repository
4. Contact the development team

## License

This integration is part of the VRSEN Lead Generation System and follows the same license terms as the main project.
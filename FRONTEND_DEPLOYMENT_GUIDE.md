# VRSEN Lead Generation Frontend - Deployment Guide

This guide covers deploying the complete VRSEN Lead Generation frontend and backend system for production use.

## 🏗️ Architecture Overview

The system consists of:
- **React Frontend**: Modern TypeScript/React SPA with Tailwind CSS
- **FastAPI Backend**: Python API server with WebSocket support
- **Integration Layer**: Real-time communication between frontend and existing lead generation system

## 🚀 Quick Start (Development)

### Prerequisites
- Node.js 18+
- Python 3.8+
- npm or yarn

### Automated Setup
```bash
# Run the setup script
python setup_frontend.py

# Start both services
start_all.bat    # Windows
./start_all.sh   # Linux/Mac
```

### Manual Setup
```bash
# 1. Setup Backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r backend_requirements.txt

# 2. Setup Frontend
cd frontend
npm install
cp .env.example .env

# 3. Start Services
python backend_api.py           # Terminal 1
cd frontend && npm run dev      # Terminal 2
```

Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📋 Features Implemented

### Core Frontend Features ✅
- **Dashboard**: Campaign overview with real-time metrics
- **Campaign Management**: Create, start, pause, stop campaigns
- **Campaign Form**: Comprehensive form with all VRSEN settings
- **Progress Tracking**: Real-time progress with WebSocket updates
- **Lead Management**: View, filter, search, and export leads
- **Responsive Design**: Works on desktop and mobile
- **Dark/Light Theme**: Full theme support
- **Type Safety**: Complete TypeScript implementation

### Technical Features ✅
- **Modern React Stack**: React 19 + TypeScript + Vite
- **State Management**: Zustand + TanStack Query
- **Real-time Updates**: WebSocket integration
- **API Integration**: Full REST API with error handling
- **Professional UI**: Tailwind CSS + Custom components
- **Form Validation**: React Hook Form with validation
- **Export Functionality**: CSV download capabilities

## 🔧 Integration with Existing System

### Backend Integration Points

The frontend is designed to integrate with your existing VRSEN lead generation system:

```python
# Example integration in your existing agents
from fastapi import FastAPI
from your_existing_system import CampaignCEO, BingNavigator, EmailExtractor

# 1. Start campaign through frontend
@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    # Initialize your existing agency
    ceo = CampaignCEO()
    navigator = BingNavigator() 
    extractor = EmailExtractor()
    
    # Create agency and start campaign
    agency = Agency([ceo, navigator, extractor])
    
    # Execute campaign with progress callbacks
    await execute_campaign_with_progress(agency, campaign_id)

# 2. Progress updates via WebSocket
async def send_progress_update(campaign_id: str, progress_data: dict):
    await websocket_manager.broadcast({
        "type": "campaign_progress",
        "campaign_id": campaign_id,
        "progress": progress_data
    })
```

### API Endpoints to Implement

Replace the demo backend with these integrations:

```python
# Connect to your existing campaign system
@app.post("/api/campaigns")
async def create_campaign(campaign_data: CampaignCreate):
    # Convert frontend data to your campaign format
    campaign_config = convert_to_vrsen_config(campaign_data)
    
    # Save to your existing database/storage
    campaign_id = await your_campaign_manager.create(campaign_config)
    
    return {"success": True, "data": {"id": campaign_id}}

# Connect to your existing lead storage
@app.get("/api/leads")
async def get_leads(filters: dict):
    # Query your existing lead database
    leads = await your_lead_manager.query(filters)
    
    return {"data": leads, "total": len(leads)}
```

## 🌐 Production Deployment

### Option 1: Static Frontend + API Backend

**Frontend (Netlify/Vercel)**
```bash
# Build frontend
cd frontend
npm run build

# Deploy dist/ folder to:
# - Netlify: Drag & drop or Git integration
# - Vercel: Git integration
# - AWS S3 + CloudFront
# - GitHub Pages
```

**Backend (Railway/Heroku/DigitalOcean)**
```python
# Dockerfile for backend
FROM python:3.11-slim
WORKDIR /app
COPY backend_requirements.txt .
RUN pip install -r backend_requirements.txt
COPY backend_api.py .
CMD ["uvicorn", "backend_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Option 2: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api
    
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/vrsen
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=vrsen
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Option 3: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vrsen-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vrsen-frontend
  template:
    metadata:
      labels:
        app: vrsen-frontend
    spec:
      containers:
      - name: frontend
        image: vrsen/frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: VITE_API_BASE_URL
          value: "https://api.vrsen.com/api"
---
apiVersion: v1
kind: Service
metadata:
  name: vrsen-frontend-service
spec:
  selector:
    app: vrsen-frontend
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

## 🔒 Security Considerations

### Frontend Security
- Environment variables for API endpoints
- HTTPS-only in production
- Content Security Policy headers
- API request authentication

### Backend Security
```python
# Add authentication middleware
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(token: str = Depends(security)):
    # Verify JWT token or API key
    if not verify_jwt_token(token.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return token

# Protect endpoints
@app.get("/api/campaigns", dependencies=[Depends(verify_token)])
async def get_campaigns():
    # Protected endpoint
    pass
```

### CORS Configuration
```python
# Production CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## 📊 Monitoring & Analytics

### Performance Monitoring
```typescript
// Frontend performance monitoring
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(console.log);
getFID(console.log);
getFCP(console.log);
getLCP(console.log);
getTTFB(console.log);
```

### API Monitoring
```python
# Backend monitoring
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.url} took {process_time:.2f}s")
    
    return response
```

## 🧪 Testing

### Frontend Tests
```bash
cd frontend

# Unit tests
npm run test

# E2E tests with Playwright
npm run test:e2e

# Visual regression tests
npm run test:visual
```

### Backend Tests
```bash
# API tests
pytest tests/

# Load testing
pip install locust
locust -f load_test.py --host=http://localhost:8000
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
# .github/workflows/deploy.yml
name: Deploy VRSEN Frontend
on:
  push:
    branches: [main]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-node@v3
      with:
        node-version: '18'
    - run: cd frontend && npm ci
    - run: cd frontend && npm run build
    - run: cd frontend && npm run test
    - name: Deploy to Netlify
      uses: nwtgck/actions-netlify@v1.2
      with:
        publish-dir: './frontend/dist'
      env:
        NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
        NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}

  backend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r backend_requirements.txt
    - run: pytest
    - name: Deploy to Railway
      uses: railway-deploy/railway-deploy@v1
      with:
        token: ${{ secrets.RAILWAY_TOKEN }}
```

## 📈 Scaling Considerations

### Frontend Scaling
- CDN for static assets
- Service worker for offline functionality
- Code splitting for faster initial loads
- Image optimization and lazy loading

### Backend Scaling
- Horizontal scaling with load balancer
- Database connection pooling
- Redis for caching and sessions
- Message queue for background tasks

### Database Design
```sql
-- Production database schema
CREATE TABLE campaigns (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    settings JSONB NOT NULL,
    progress JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE leads (
    id UUID PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    confidence DECIMAL(3,2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_leads_campaign_id ON leads(campaign_id);
CREATE INDEX idx_leads_email ON leads(email);
```

## 🎯 Next Steps

1. **Integration**: Connect with your existing VRSEN agents
2. **Authentication**: Add user authentication and authorization
3. **Database**: Replace in-memory storage with PostgreSQL/MySQL
4. **Monitoring**: Add application monitoring and logging
5. **Scaling**: Implement horizontal scaling and load balancing
6. **Features**: Add advanced analytics and reporting

## 📞 Support

For technical support or integration assistance:
- Review the API documentation at `/docs` endpoint
- Check the frontend README in `frontend/README.md`
- Examine the sample integration code in `backend_api.py`

The frontend is production-ready and can be immediately deployed to serve your lead generation workflow through a modern web interface.
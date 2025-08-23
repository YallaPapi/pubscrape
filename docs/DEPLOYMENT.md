# Deployment Guide - PubScrape Infinite Scroll Scraper System

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Production Setup](#production-setup)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Security Considerations](#security-considerations)
8. [Scaling and Performance](#scaling-and-performance)

## Deployment Options

### Available Deployment Methods

- **Local Development**: Direct Python execution
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-service orchestration
- **Cloud Platforms**: AWS, Google Cloud, Azure
- **Kubernetes**: Container orchestration
- **Traditional Servers**: VPS/Dedicated servers

### Recommended Configurations

| Environment | Method | Resources | Use Case |
|-------------|--------|-----------|----------|
| Development | Local Python | 4GB RAM, 2 CPU | Testing, debugging |
| Staging | Docker | 8GB RAM, 4 CPU | Pre-production testing |
| Production | Docker Compose | 16GB RAM, 8 CPU | Production workloads |
| Scale | Kubernetes | 32GB+ RAM, 16+ CPU | High-volume operations |

## Local Development

### Prerequisites

```bash
# System requirements
- Python 3.8+
- Chrome/Chromium browser
- Git
- 4GB+ RAM
- 2GB+ disk space
```

### Development Setup

1. **Clone and Environment Setup**:
   ```bash
   git clone https://github.com/your-org/pubscrape.git
   cd pubscrape
   
   # Create virtual environment
   python -m venv venv
   
   # Activate environment
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   # Install core dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

3. **Environment Configuration**:
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your configuration
   nano .env
   ```

4. **Development Environment Variables**:
   ```bash
   # .env file for development
   OPENAI_API_KEY=sk-your-key-here
   DEBUG_MODE=true
   LOG_LEVEL=DEBUG
   BROWSER_MODE=headful
   RATE_LIMIT_RPM=6
   MAX_PAGES_PER_QUERY=2
   ENABLE_PROXY_ROTATION=false
   ```

5. **Verify Installation**:
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Test basic functionality
   python -c "from botasaurus_doctor_scraper import main; print('✅ Import successful')"
   
   # Run simple test
   python botasaurus_doctor_scraper.py
   ```

### Development Workflow

```bash
# Start development server (if using web interface)
python -m uvicorn backend_api:app --reload --host 0.0.0.0 --port 8000

# Run specific scraper
python botasaurus_doctor_scraper.py

# Run with custom configuration
python -c "
from src.core.config_manager import ConfigManager
config = ConfigManager()
config.set('search.rate_limit_rpm', 4)
config.set('debug_mode', True)
from botasaurus_doctor_scraper import main
main()
"

# Run tests continuously
pytest-watch tests/
```

## Docker Deployment

### Single Container Deployment

1. **Build Docker Image**:
   ```bash
   # Build image
   docker build -t pubscrape:latest .
   
   # Build with specific tag
   docker build -t pubscrape:v1.0.0 .
   ```

2. **Dockerfile Configuration**:
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       wget \
       gnupg \
       unzip \
       curl \
       && rm -rf /var/lib/apt/lists/*
   
   # Install Chrome
   RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
       && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
       && apt-get update \
       && apt-get install -y google-chrome-stable \
       && rm -rf /var/lib/apt/lists/*
   
   # Set working directory
   WORKDIR /app
   
   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create necessary directories
   RUN mkdir -p output logs cache temp
   
   # Set environment variables
   ENV PYTHONPATH=/app
   ENV CHROME_BIN=/usr/bin/google-chrome
   ENV DISPLAY=:99
   
   # Expose port (if using web interface)
   EXPOSE 8000
   
   # Default command
   CMD ["python", "botasaurus_doctor_scraper.py"]
   ```

3. **Run Container**:
   ```bash
   # Basic run
   docker run --rm \
     -e OPENAI_API_KEY=your_key_here \
     -v $(pwd)/output:/app/output \
     pubscrape:latest
   
   # Run with custom configuration
   docker run --rm \
     -e OPENAI_API_KEY=your_key_here \
     -e RATE_LIMIT_RPM=8 \
     -e MAX_PAGES_PER_QUERY=3 \
     -v $(pwd)/output:/app/output \
     -v $(pwd)/config.yaml:/app/config.yaml \
     pubscrape:latest
   
   # Run with web interface
   docker run -d \
     --name pubscrape \
     -p 8000:8000 \
     -e OPENAI_API_KEY=your_key_here \
     -v $(pwd)/output:/app/output \
     pubscrape:latest \
     python -m uvicorn backend_api:app --host 0.0.0.0 --port 8000
   ```

### Docker Compose Deployment

1. **Docker Compose Configuration**:
   ```yaml
   # docker-compose.yml
   version: '3.8'
   
   services:
     pubscrape:
       build: .
       container_name: pubscrape
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - RATE_LIMIT_RPM=12
         - LOG_LEVEL=INFO
         - BROWSER_MODE=headless
       volumes:
         - ./output:/app/output
         - ./logs:/app/logs
         - ./config:/app/config
         - ./cache:/app/cache
       ports:
         - "8000:8000"
       restart: unless-stopped
       depends_on:
         - redis
         - postgres
   
     redis:
       image: redis:7-alpine
       container_name: pubscrape_redis
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       restart: unless-stopped
   
     postgres:
       image: postgres:15-alpine
       container_name: pubscrape_postgres
       environment:
         - POSTGRES_DB=pubscrape
         - POSTGRES_USER=pubscrape
         - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       ports:
         - "5432:5432"
       restart: unless-stopped
   
     nginx:
       image: nginx:alpine
       container_name: pubscrape_nginx
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
       depends_on:
         - pubscrape
       restart: unless-stopped
   
     monitoring:
       image: prom/prometheus
       container_name: pubscrape_monitoring
       ports:
         - "9090:9090"
       volumes:
         - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
       restart: unless-stopped
   
   volumes:
     redis_data:
     postgres_data:
   ```

2. **Environment Configuration**:
   ```bash
   # .env file for Docker Compose
   OPENAI_API_KEY=sk-your-key-here
   POSTGRES_PASSWORD=secure_password_here
   NGINX_HOST=your-domain.com
   SSL_EMAIL=your-email@domain.com
   ```

3. **Deploy with Docker Compose**:
   ```bash
   # Start all services
   docker-compose up -d
   
   # View logs
   docker-compose logs -f pubscrape
   
   # Scale the main service
   docker-compose up -d --scale pubscrape=3
   
   # Update configuration
   docker-compose restart pubscrape
   
   # Stop all services
   docker-compose down
   
   # Clean up volumes
   docker-compose down -v
   ```

## Cloud Deployment

### AWS Deployment

#### EC2 Instance Setup

1. **Launch EC2 Instance**:
   ```bash
   # Launch instance (using AWS CLI)
   aws ec2 run-instances \
     --image-id ami-0abcdef1234567890 \
     --count 1 \
     --instance-type t3.large \
     --key-name your-key-pair \
     --security-group-ids sg-12345678 \
     --subnet-id subnet-12345678 \
     --user-data file://user-data.sh
   ```

2. **User Data Script**:
   ```bash
   #!/bin/bash
   # user-data.sh
   
   # Update system
   yum update -y
   
   # Install Docker
   amazon-linux-extras install docker
   systemctl start docker
   systemctl enable docker
   usermod -a -G docker ec2-user
   
   # Install Docker Compose
   curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   chmod +x /usr/local/bin/docker-compose
   
   # Clone repository
   cd /home/ec2-user
   git clone https://github.com/your-org/pubscrape.git
   cd pubscrape
   
   # Set up environment
   echo "OPENAI_API_KEY=your_key_here" > .env
   echo "POSTGRES_PASSWORD=secure_password" >> .env
   
   # Start services
   docker-compose up -d
   ```

#### ECS Deployment

1. **Task Definition**:
   ```json
   {
     "family": "pubscrape",
     "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
     "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "containerDefinitions": [
       {
         "name": "pubscrape",
         "image": "your-account.dkr.ecr.region.amazonaws.com/pubscrape:latest",
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "OPENAI_API_KEY",
             "value": "your-key-here"
           },
           {
             "name": "LOG_LEVEL",
             "value": "INFO"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/pubscrape",
             "awslogs-region": "us-west-2",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

2. **Deploy to ECS**:
   ```bash
   # Build and push image to ECR
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-west-2.amazonaws.com
   
   docker build -t pubscrape .
   docker tag pubscrape:latest your-account.dkr.ecr.us-west-2.amazonaws.com/pubscrape:latest
   docker push your-account.dkr.ecr.us-west-2.amazonaws.com/pubscrape:latest
   
   # Create ECS service
   aws ecs create-service \
     --cluster pubscrape-cluster \
     --service-name pubscrape-service \
     --task-definition pubscrape:1 \
     --desired-count 2 \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
   ```

### Google Cloud Platform

1. **Cloud Run Deployment**:
   ```bash
   # Build and deploy to Cloud Run
   gcloud builds submit --tag gcr.io/your-project/pubscrape
   
   gcloud run deploy pubscrape \
     --image gcr.io/your-project/pubscrape \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 1 \
     --max-instances 10 \
     --set-env-vars OPENAI_API_KEY=your-key-here
   ```

2. **GKE Deployment**:
   ```yaml
   # k8s-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: pubscrape
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: pubscrape
     template:
       metadata:
         labels:
           app: pubscrape
       spec:
         containers:
         - name: pubscrape
           image: gcr.io/your-project/pubscrape:latest
           ports:
           - containerPort: 8000
           env:
           - name: OPENAI_API_KEY
             valueFrom:
               secretKeyRef:
                 name: pubscrape-secrets
                 key: openai-api-key
           resources:
             requests:
               memory: "1Gi"
               cpu: "500m"
             limits:
               memory: "2Gi"
               cpu: "1000m"
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: pubscrape-service
   spec:
     selector:
       app: pubscrape
     ports:
     - port: 80
       targetPort: 8000
     type: LoadBalancer
   ```

### Azure Deployment

1. **Container Instances**:
   ```bash
   # Create resource group
   az group create --name pubscrape-rg --location eastus
   
   # Deploy container instance
   az container create \
     --resource-group pubscrape-rg \
     --name pubscrape \
     --image your-registry/pubscrape:latest \
     --cpu 2 \
     --memory 4 \
     --ports 8000 \
     --environment-variables OPENAI_API_KEY=your-key-here \
     --restart-policy Always
   ```

## Production Setup

### Production Environment Configuration

1. **Production Environment Variables**:
   ```bash
   # .env.production
   # API Configuration
   OPENAI_API_KEY=sk-production-key-here
   
   # Performance Settings
   RATE_LIMIT_RPM=20
   MAX_PAGES_PER_QUERY=5
   MAX_CONCURRENT_SEARCHES=4
   TIMEOUT_SECONDS=30
   
   # Browser Configuration
   BROWSER_MODE=headless
   ENABLE_PROXY_ROTATION=true
   
   # Processing Settings
   BATCH_SIZE=200
   MAX_WORKERS=8
   ENABLE_DEDUPLICATION=true
   VALIDATION_ENABLED=true
   
   # Storage Configuration
   OUTPUT_DIRECTORY=/data/output
   LOG_DIRECTORY=/var/log/pubscrape
   CACHE_DIRECTORY=/data/cache
   
   # Security
   DEBUG_MODE=false
   LOG_LEVEL=INFO
   ENABLE_METRICS=true
   ```

2. **Production Docker Compose**:
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   
   services:
     pubscrape:
       image: pubscrape:latest
       container_name: pubscrape_prod
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - RATE_LIMIT_RPM=20
         - LOG_LEVEL=INFO
         - BROWSER_MODE=headless
         - ENABLE_METRICS=true
       volumes:
         - /data/output:/app/output
         - /var/log/pubscrape:/app/logs
         - /data/cache:/app/cache
       ports:
         - "8000:8000"
       restart: always
       deploy:
         resources:
           limits:
             memory: 4G
             cpus: '2.0'
           reservations:
             memory: 2G
             cpus: '1.0'
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
   
     nginx:
       image: nginx:alpine
       container_name: pubscrape_nginx_prod
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx/nginx.conf:/etc/nginx/nginx.conf
         - /etc/letsencrypt:/etc/letsencrypt
       depends_on:
         - pubscrape
       restart: always
   
     redis:
       image: redis:7-alpine
       container_name: pubscrape_redis_prod
       volumes:
         - redis_data:/data
       restart: always
       command: redis-server --appendonly yes
   
     monitoring:
       image: prom/prometheus
       container_name: pubscrape_prometheus
       ports:
         - "9090:9090"
       volumes:
         - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
         - prometheus_data:/prometheus
       restart: always
   
   volumes:
     redis_data:
     prometheus_data:
   ```

### SSL/TLS Configuration

1. **Nginx Configuration with SSL**:
   ```nginx
   # nginx/nginx.conf
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl;
       server_name your-domain.com;
   
       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
   
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
       ssl_prefer_server_ciphers off;
   
       location / {
           proxy_pass http://pubscrape:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   
       location /health {
           proxy_pass http://pubscrape:8000/health;
       }
   }
   ```

2. **Let's Encrypt SSL Setup**:
   ```bash
   # Install certbot
   sudo apt-get install certbot python3-certbot-nginx
   
   # Obtain certificate
   sudo certbot --nginx -d your-domain.com
   
   # Auto-renewal setup
   sudo crontab -e
   # Add: 0 12 * * * /usr/bin/certbot renew --quiet
   ```

### Database Setup (Optional)

1. **PostgreSQL Configuration**:
   ```sql
   -- Create database and user
   CREATE DATABASE pubscrape;
   CREATE USER pubscrape_user WITH ENCRYPTED PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE pubscrape TO pubscrape_user;
   
   -- Create tables
   \c pubscrape;
   
   CREATE TABLE campaigns (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       queries TEXT[],
       status VARCHAR(50),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   CREATE TABLE leads (
       id SERIAL PRIMARY KEY,
       campaign_id INTEGER REFERENCES campaigns(id),
       business_name VARCHAR(255),
       website VARCHAR(500),
       email VARCHAR(255),
       phone VARCHAR(50),
       address TEXT,
       extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   CREATE INDEX idx_leads_campaign_id ON leads(campaign_id);
   CREATE INDEX idx_leads_email ON leads(email);
   ```

## Monitoring and Logging

### Prometheus Monitoring

1. **Prometheus Configuration**:
   ```yaml
   # monitoring/prometheus.yml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'pubscrape'
       static_configs:
         - targets: ['pubscrape:8000']
       metrics_path: '/metrics'
       scrape_interval: 30s
   
     - job_name: 'node-exporter'
       static_configs:
         - targets: ['node-exporter:9100']
   ```

2. **Application Metrics**:
   ```python
   # Add to your application
   from prometheus_client import Counter, Histogram, generate_latest
   
   # Metrics
   REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
   REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
   EXTRACTION_SUCCESS = Counter('extractions_total', 'Total extractions', ['status'])
   
   # Health check endpoint
   @app.route('/health')
   def health_check():
       return {'status': 'healthy', 'timestamp': time.time()}
   
   # Metrics endpoint
   @app.route('/metrics')
   def metrics():
       return generate_latest()
   ```

### Centralized Logging

1. **ELK Stack Setup**:
   ```yaml
   # Add to docker-compose.yml
   elasticsearch:
     image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
     environment:
       - discovery.type=single-node
       - xpack.security.enabled=false
     volumes:
       - elasticsearch_data:/usr/share/elasticsearch/data
   
   logstash:
     image: docker.elastic.co/logstash/logstash:8.5.0
     volumes:
       - ./logstash/pipeline:/usr/share/logstash/pipeline
   
   kibana:
     image: docker.elastic.co/kibana/kibana:8.5.0
     ports:
       - "5601:5601"
     environment:
       - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
   ```

2. **Structured Logging Configuration**:
   ```python
   # logging_config.py
   import structlog
   
   # Configure structured logging
   structlog.configure(
       processors=[
           structlog.stdlib.filter_by_level,
           structlog.stdlib.add_logger_name,
           structlog.stdlib.add_log_level,
           structlog.stdlib.PositionalArgumentsFormatter(),
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.format_exc_info,
           structlog.processors.UnicodeDecoder(),
           structlog.processors.JSONRenderer()
       ],
       context_class=dict,
       logger_factory=structlog.stdlib.LoggerFactory(),
       wrapper_class=structlog.stdlib.BoundLogger,
       cache_logger_on_first_use=True,
   )
   ```

### Health Checks and Alerting

1. **Health Check Implementation**:
   ```python
   # health.py
   import time
   import psutil
   from src.core.config_manager import ConfigManager
   
   def get_system_health():
       return {
           'status': 'healthy',
           'timestamp': time.time(),
           'memory_usage': psutil.virtual_memory().percent,
           'cpu_usage': psutil.cpu_percent(interval=1),
           'disk_usage': psutil.disk_usage('/').percent,
           'config_valid': ConfigManager().validate()[0]
       }
   ```

2. **Alerting Rules**:
   ```yaml
   # alerting/rules.yml
   groups:
     - name: pubscrape
       rules:
         - alert: HighMemoryUsage
           expr: memory_usage > 90
           for: 5m
           labels:
             severity: warning
           annotations:
             summary: "High memory usage detected"
   
         - alert: ExtractionFailureRate
           expr: rate(extractions_total{status="failed"}[5m]) > 0.1
           for: 2m
           labels:
             severity: critical
           annotations:
             summary: "High extraction failure rate"
   ```

## Security Considerations

### API Key Management

```bash
# Use environment variables or secret management
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString --output text)

# Or use Docker secrets
echo "sk-your-key-here" | docker secret create openai_api_key -
```

### Network Security

```bash
# Firewall rules (iptables)
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT    # SSH
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT    # HTTP
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT   # HTTPS
sudo iptables -A INPUT -p tcp --dport 8000 -j DROP    # Block direct access to app
sudo iptables -P INPUT DROP                           # Default deny
```

### Data Privacy

```yaml
# GDPR compliance configuration
privacy:
  data_retention_days: 90
  anonymize_logs: true
  encryption_at_rest: true
  gdpr_compliance: true
```

## Scaling and Performance

### Horizontal Scaling

1. **Docker Swarm Setup**:
   ```bash
   # Initialize swarm
   docker swarm init
   
   # Deploy stack
   docker stack deploy -c docker-compose.yml pubscrape
   
   # Scale service
   docker service scale pubscrape_pubscrape=5
   ```

2. **Kubernetes Scaling**:
   ```yaml
   # Horizontal Pod Autoscaler
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: pubscrape-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: pubscrape
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

### Load Balancing

1. **Nginx Load Balancer**:
   ```nginx
   upstream pubscrape_backend {
       least_conn;
       server pubscrape1:8000 weight=1 max_fails=3 fail_timeout=30s;
       server pubscrape2:8000 weight=1 max_fails=3 fail_timeout=30s;
       server pubscrape3:8000 weight=1 max_fails=3 fail_timeout=30s;
   }
   
   server {
       listen 80;
       location / {
           proxy_pass http://pubscrape_backend;
           proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
       }
   }
   ```

### Performance Optimization

```yaml
# Performance tuning configuration
performance:
  worker_processes: auto
  worker_connections: 1024
  keepalive_timeout: 65
  client_max_body_size: 10M
  
  # Browser optimization
  browser_pool_size: 5
  session_reuse: true
  resource_blocking: true
  
  # Memory management
  max_memory_per_worker: 1GB
  garbage_collection_threshold: 100MB
```

This deployment guide provides comprehensive instructions for deploying PubScrape in various environments, from development to production scale.
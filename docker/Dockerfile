# Multi-stage Dockerfile for VRSEN PubScrape
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    curl \
    wget \
    git \
    # Chrome/Chromium dependencies for Botasaurus
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    # Additional dependencies
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r scraper && useradd -r -g scraper -m -d /home/scraper scraper

# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
COPY requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p /app/output /app/logs /app/cache /app/data /app/state /app/temp

# Set ownership
RUN chown -R scraper:scraper /app

# Switch to non-root user
USER scraper

# Set environment
ENV VRSEN_ENV=development
ENV PYTHONPATH=/app

# Expose ports
EXPOSE 8000 8080

# Development command
CMD ["python", "main.py", "--help"]

# Production stage
FROM base as production

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies (production only)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY main.py ./
COPY *.py ./
COPY campaigns/ ./campaigns/
COPY configs/ ./configs/

# Create necessary directories
RUN mkdir -p /app/output /app/logs /app/cache /app/data /app/state /app/temp

# Set ownership
RUN chown -R scraper:scraper /app

# Switch to non-root user
USER scraper

# Set environment
ENV VRSEN_ENV=production
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Production command
CMD ["python", "main.py", "scrape", "--campaign", "campaigns/default.yaml"]

# Nginx stage for serving static files and API proxy
FROM nginx:alpine as nginx

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf /etc/nginx/conf.d/default.conf

# Create directory for static files
RUN mkdir -p /usr/share/nginx/html/static

# Copy static files if they exist
COPY frontend/dist/ /usr/share/nginx/html/ 2>/dev/null || echo "No frontend dist found"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
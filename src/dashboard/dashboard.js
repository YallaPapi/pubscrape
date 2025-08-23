class BusinessScraperDashboard {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isScrapingActive = false;
        this.screenshots = [];
        this.currentScreenshotIndex = 0;
        this.extractedData = [];
        this.startTime = null;
        this.charts = {};
        this.metrics = {
            leadsExtracted: 0,
            totalProgress: 0,
            successRate: 0,
            avgTime: 0,
            memoryUsage: 0,
            cpuUsage: 0,
            requestRate: 0
        };

        this.initializeElements();
        this.initializeEventListeners();
        this.initializeWebSocket();
        this.initializeCharts();
        this.startMetricsTimer();
    }

    initializeElements() {
        // Connection status
        this.connectionStatus = document.getElementById('connectionStatus');
        this.statusDot = this.connectionStatus.querySelector('.status-dot');
        this.statusText = this.connectionStatus.querySelector('.status-text');

        // Controls
        this.startButton = document.getElementById('startScraping');
        this.stopButton = document.getElementById('stopScraping');
        this.exportButton = document.getElementById('exportData');

        // Configuration
        this.businessTypeInput = document.getElementById('businessType');
        this.locationInput = document.getElementById('location');
        this.leadCountSlider = document.getElementById('leadCount');
        this.leadCountValue = document.getElementById('leadCountValue');
        this.regionSelect = document.getElementById('region');
        this.antiDetectionSelect = document.getElementById('antiDetection');
        this.exportFormatSelect = document.getElementById('exportFormat');

        // Progress elements
        this.totalProgressSpan = document.getElementById('totalProgress');
        this.leadsExtractedSpan = document.getElementById('leadsExtracted');
        this.successRateSpan = document.getElementById('successRate');
        this.avgTimeSpan = document.getElementById('avgTime');
        this.progressBar = document.getElementById('mainProgressBar');
        this.currentActivity = document.getElementById('currentActivity');

        // Screenshots
        this.screenshotCarousel = document.getElementById('screenshotCarousel');
        this.prevScreenshotBtn = document.getElementById('prevScreenshot');
        this.nextScreenshotBtn = document.getElementById('nextScreenshot');
        this.screenshotCounter = this.screenshotCarousel.parentElement.querySelector('.screenshot-counter');

        // Data table
        this.dataTableBody = document.getElementById('dataTableBody');

        // Logs
        this.logsContainer = document.getElementById('logsContainer');
        this.clearLogsBtn = document.getElementById('clearLogs');

        // Metrics
        this.memoryUsageSpan = document.getElementById('memoryUsage');
        this.cpuUsageSpan = document.getElementById('cpuUsage');
        this.requestRateSpan = document.getElementById('requestRate');
        this.runtimeSpan = document.getElementById('runtime');

        // Modal
        this.screenshotModal = document.getElementById('screenshotModal');
        this.modalScreenshot = document.getElementById('modalScreenshot');
        this.screenshotCaption = document.getElementById('screenshotCaption');
        this.modalClose = this.screenshotModal.querySelector('.close');
    }

    initializeEventListeners() {
        // Control buttons
        this.startButton.addEventListener('click', () => this.startScraping());
        this.stopButton.addEventListener('click', () => this.stopScraping());
        this.exportButton.addEventListener('click', () => this.exportData());

        // Configuration
        this.leadCountSlider.addEventListener('input', (e) => {
            this.leadCountValue.textContent = e.target.value;
        });

        // Screenshot navigation
        this.prevScreenshotBtn.addEventListener('click', () => this.previousScreenshot());
        this.nextScreenshotBtn.addEventListener('click', () => this.nextScreenshot());

        // Screenshot modal
        this.modalClose.addEventListener('click', () => this.closeScreenshotModal());
        this.screenshotModal.addEventListener('click', (e) => {
            if (e.target === this.screenshotModal) {
                this.closeScreenshotModal();
            }
        });

        // Clear logs
        this.clearLogsBtn.addEventListener('click', () => this.clearLogs());

        // Window events
        window.addEventListener('beforeunload', () => {
            if (this.socket) {
                this.socket.disconnect();
            }
        });
    }

    initializeWebSocket() {
        const wsUrl = `ws://${window.location.hostname}:5000`;
        this.addLog('info', `Connecting to ${wsUrl}...`);

        try {
            this.socket = io(wsUrl, {
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true
            });

            this.socket.on('connect', () => {
                this.onConnect();
            });

            this.socket.on('disconnect', () => {
                this.onDisconnect();
            });

            this.socket.on('scraping_progress', (data) => {
                this.updateProgress(data);
            });

            this.socket.on('screenshot_update', (data) => {
                this.addScreenshot(data);
            });

            this.socket.on('lead_extracted', (data) => {
                this.addExtractedLead(data);
            });

            this.socket.on('log_message', (data) => {
                this.addLog(data.level, data.message, data.timestamp);
            });

            this.socket.on('system_metrics', (data) => {
                this.updateSystemMetrics(data);
            });

            this.socket.on('scraping_complete', (data) => {
                this.onScrapingComplete(data);
            });

            this.socket.on('error', (error) => {
                this.addLog('error', `Socket error: ${error.message}`);
            });

        } catch (error) {
            this.addLog('error', `WebSocket connection failed: ${error.message}`);
            this.onDisconnect();
        }
    }

    initializeCharts() {
        // Leads over time chart
        const leadsCtx = document.getElementById('leadsChart').getContext('2d');
        this.charts.leads = new Chart(leadsCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Leads Extracted',
                    data: [],
                    borderColor: '#4facfe',
                    backgroundColor: 'rgba(79, 172, 254, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Leads Extracted Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Performance metrics chart
        const perfCtx = document.getElementById('performanceChart').getContext('2d');
        this.charts.performance = new Chart(perfCtx, {
            type: 'doughnut',
            data: {
                labels: ['Success', 'Failed', 'Pending'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Success Rate'
                    }
                }
            }
        });
    }

    onConnect() {
        this.isConnected = true;
        this.statusDot.className = 'status-dot online';
        this.statusText.textContent = 'Connected';
        this.addLog('success', 'Connected to scraping server');
    }

    onDisconnect() {
        this.isConnected = false;
        this.statusDot.className = 'status-dot offline';
        this.statusText.textContent = 'Disconnected';
        this.addLog('warning', 'Disconnected from scraping server');
    }

    startScraping() {
        if (!this.isConnected) {
            this.addLog('error', 'Cannot start scraping: Not connected to server');
            return;
        }

        const config = {
            businessType: this.businessTypeInput.value.trim(),
            location: this.locationInput.value.trim(),
            leadCount: parseInt(this.leadCountSlider.value),
            region: this.regionSelect.value,
            antiDetection: this.antiDetectionSelect.value,
            exportFormat: this.exportFormatSelect.value
        };

        if (!config.businessType || !config.location) {
            this.addLog('error', 'Please enter business type and location');
            return;
        }

        this.isScrapingActive = true;
        this.startTime = new Date();
        this.extractedData = [];
        this.screenshots = [];
        this.currentScreenshotIndex = 0;

        // Update UI
        this.startButton.disabled = true;
        this.stopButton.disabled = false;
        this.currentActivity.textContent = 'Initializing scraping...';

        // Clear previous data
        this.dataTableBody.innerHTML = '';
        this.resetMetrics();
        this.updateScreenshotCarousel();

        // Send start command to server
        this.socket.emit('start_scraping', config);
        this.addLog('info', `Starting scraping: ${config.businessType} in ${config.location}`);
    }

    stopScraping() {
        if (!this.isConnected) return;

        this.isScrapingActive = false;
        this.startButton.disabled = false;
        this.stopButton.disabled = true;
        this.currentActivity.textContent = 'Stopping scraping...';

        this.socket.emit('stop_scraping');
        this.addLog('warning', 'Scraping stopped by user');
    }

    updateProgress(data) {
        this.metrics.totalProgress = data.progress || 0;
        this.metrics.leadsExtracted = data.leads_found || 0;
        this.metrics.successRate = data.success_rate || 0;
        this.metrics.avgTime = data.avg_time || 0;

        // Update UI elements
        this.totalProgressSpan.textContent = `${this.metrics.totalProgress}%`;
        this.leadsExtractedSpan.textContent = this.metrics.leadsExtracted;
        this.successRateSpan.textContent = `${this.metrics.successRate}%`;
        this.avgTimeSpan.textContent = `${this.metrics.avgTime}s`;

        // Update progress bar
        const progressFill = this.progressBar.querySelector('.progress-fill');
        progressFill.style.width = `${this.metrics.totalProgress}%`;

        // Update current activity
        if (data.current_activity) {
            this.currentActivity.textContent = data.current_activity;
        }

        // Update charts
        this.updateCharts();
    }

    addScreenshot(data) {
        const screenshot = {
            id: data.id || Date.now(),
            url: data.url,
            timestamp: data.timestamp || new Date().toISOString(),
            caption: data.caption || 'Browser screenshot'
        };

        this.screenshots.push(screenshot);
        this.updateScreenshotCarousel();
        this.addLog('info', `Screenshot captured: ${screenshot.caption}`);
    }

    updateScreenshotCarousel() {
        if (this.screenshots.length === 0) {
            this.screenshotCarousel.innerHTML = `
                <div class="screenshot-placeholder">
                    <i class="fas fa-image"></i>
                    <p>Screenshots will appear here during scraping</p>
                </div>
            `;
            this.screenshotCounter.textContent = '0 / 0';
            return;
        }

        const screenshot = this.screenshots[this.currentScreenshotIndex];
        this.screenshotCarousel.innerHTML = `
            <img class="screenshot-image" 
                 src="${screenshot.url}" 
                 alt="${screenshot.caption}"
                 onclick="dashboard.openScreenshotModal(${this.currentScreenshotIndex})">
        `;

        this.screenshotCounter.textContent = 
            `${this.currentScreenshotIndex + 1} / ${this.screenshots.length}`;

        // Enable/disable navigation buttons
        this.prevScreenshotBtn.disabled = this.currentScreenshotIndex === 0;
        this.nextScreenshotBtn.disabled = this.currentScreenshotIndex === this.screenshots.length - 1;
    }

    previousScreenshot() {
        if (this.currentScreenshotIndex > 0) {
            this.currentScreenshotIndex--;
            this.updateScreenshotCarousel();
        }
    }

    nextScreenshot() {
        if (this.currentScreenshotIndex < this.screenshots.length - 1) {
            this.currentScreenshotIndex++;
            this.updateScreenshotCarousel();
        }
    }

    openScreenshotModal(index) {
        if (index >= 0 && index < this.screenshots.length) {
            const screenshot = this.screenshots[index];
            this.modalScreenshot.src = screenshot.url;
            this.screenshotCaption.textContent = `${screenshot.caption} - ${new Date(screenshot.timestamp).toLocaleString()}`;
            this.screenshotModal.style.display = 'block';
        }
    }

    closeScreenshotModal() {
        this.screenshotModal.style.display = 'none';
    }

    addExtractedLead(data) {
        this.extractedData.push(data);

        // Add to table
        const row = document.createElement('tr');
        row.className = 'slide-in';
        row.innerHTML = `
            <td>${this.escapeHtml(data.name || 'N/A')}</td>
            <td>${this.escapeHtml(data.phone || 'N/A')}</td>
            <td>${this.escapeHtml(data.email || 'N/A')}</td>
            <td>${this.escapeHtml(data.address || 'N/A')}</td>
            <td>${data.website ? `<a href="${data.website}" target="_blank">${this.escapeHtml(data.website)}</a>` : 'N/A'}</td>
            <td><span class="status-badge status-${data.status || 'success'}">${data.status || 'Success'}</span></td>
        `;

        // Insert at the top
        this.dataTableBody.insertBefore(row, this.dataTableBody.firstChild);

        // Enable export button
        this.exportButton.disabled = false;

        // Scroll to top of table
        this.dataTableBody.parentElement.scrollTop = 0;
    }

    addLog(level, message, timestamp = null) {
        const logTime = timestamp ? new Date(timestamp) : new Date();
        const timeString = logTime.toLocaleTimeString();

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${level}`;
        logEntry.innerHTML = `
            <span class="log-time">${timeString}</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;

        this.logsContainer.appendChild(logEntry);
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;

        // Limit log entries to prevent memory issues
        const maxLogs = 1000;
        while (this.logsContainer.children.length > maxLogs) {
            this.logsContainer.removeChild(this.logsContainer.firstChild);
        }
    }

    clearLogs() {
        this.logsContainer.innerHTML = '';
        this.addLog('info', 'Logs cleared');
    }

    updateSystemMetrics(data) {
        this.metrics.memoryUsage = data.memory || 0;
        this.metrics.cpuUsage = data.cpu || 0;
        this.metrics.requestRate = data.request_rate || 0;

        this.memoryUsageSpan.textContent = `${this.metrics.memoryUsage} MB`;
        this.cpuUsageSpan.textContent = `${this.metrics.cpuUsage}%`;
        this.requestRateSpan.textContent = this.metrics.requestRate;
    }

    updateCharts() {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();

        // Update leads chart
        this.charts.leads.data.labels.push(timeLabel);
        this.charts.leads.data.datasets[0].data.push(this.metrics.leadsExtracted);

        // Keep only last 20 data points
        if (this.charts.leads.data.labels.length > 20) {
            this.charts.leads.data.labels.shift();
            this.charts.leads.data.datasets[0].data.shift();
        }

        this.charts.leads.update('none');

        // Update performance chart
        const successCount = Math.round(this.metrics.leadsExtracted * this.metrics.successRate / 100);
        const failedCount = this.metrics.leadsExtracted - successCount;
        const pendingCount = Math.max(0, parseInt(this.leadCountSlider.value) - this.metrics.leadsExtracted);

        this.charts.performance.data.datasets[0].data = [successCount, failedCount, pendingCount];
        this.charts.performance.update('none');
    }

    onScrapingComplete(data) {
        this.isScrapingActive = false;
        this.startButton.disabled = false;
        this.stopButton.disabled = true;
        this.currentActivity.textContent = 'Scraping completed';

        this.addLog('success', `Scraping completed: ${data.total_leads} leads extracted`);

        // Final metrics update
        if (data.final_metrics) {
            this.updateProgress(data.final_metrics);
        }
    }

    exportData() {
        if (this.extractedData.length === 0) {
            this.addLog('warning', 'No data to export');
            return;
        }

        const format = this.exportFormatSelect.value;
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const filename = `business_leads_${timestamp}`;

        switch (format) {
            case 'csv':
                this.exportAsCSV(filename);
                break;
            case 'json':
                this.exportAsJSON(filename);
                break;
            case 'excel':
                this.exportAsExcel(filename);
                break;
        }

        this.addLog('success', `Data exported as ${format.toUpperCase()}: ${filename}`);
    }

    exportAsCSV(filename) {
        const headers = ['Business Name', 'Phone', 'Email', 'Address', 'Website', 'Status'];
        const csvContent = [
            headers.join(','),
            ...this.extractedData.map(lead => [
                this.escapeCSV(lead.name || ''),
                this.escapeCSV(lead.phone || ''),
                this.escapeCSV(lead.email || ''),
                this.escapeCSV(lead.address || ''),
                this.escapeCSV(lead.website || ''),
                this.escapeCSV(lead.status || 'Success')
            ].join(','))
        ].join('\n');

        this.downloadFile(csvContent, `${filename}.csv`, 'text/csv');
    }

    exportAsJSON(filename) {
        const jsonContent = JSON.stringify(this.extractedData, null, 2);
        this.downloadFile(jsonContent, `${filename}.json`, 'application/json');
    }

    exportAsExcel(filename) {
        // For simplicity, export as CSV with .xlsx extension
        // In a real implementation, you'd use a library like SheetJS
        this.exportAsCSV(filename.replace('.csv', '.xlsx'));
    }

    downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    resetMetrics() {
        this.metrics = {
            leadsExtracted: 0,
            totalProgress: 0,
            successRate: 0,
            avgTime: 0,
            memoryUsage: 0,
            cpuUsage: 0,
            requestRate: 0
        };

        this.totalProgressSpan.textContent = '0%';
        this.leadsExtractedSpan.textContent = '0';
        this.successRateSpan.textContent = '0%';
        this.avgTimeSpan.textContent = '0s';

        const progressFill = this.progressBar.querySelector('.progress-fill');
        progressFill.style.width = '0%';

        // Reset charts
        this.charts.leads.data.labels = [];
        this.charts.leads.data.datasets[0].data = [];
        this.charts.leads.update();

        this.charts.performance.data.datasets[0].data = [0, 0, 0];
        this.charts.performance.update();
    }

    startMetricsTimer() {
        setInterval(() => {
            if (this.startTime && this.isScrapingActive) {
                const elapsed = Math.floor((new Date() - this.startTime) / 1000);
                const hours = Math.floor(elapsed / 3600);
                const minutes = Math.floor((elapsed % 3600) / 60);
                const seconds = elapsed % 60;
                this.runtimeSpan.textContent = 
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeCSV(text) {
        if (typeof text !== 'string') return text;
        if (text.includes('"') || text.includes(',') || text.includes('\n')) {
            return `"${text.replace(/"/g, '""')}"`;
        }
        return text;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new BusinessScraperDashboard();
});

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.dashboard && !window.dashboard.isConnected) {
        // Try to reconnect when page becomes visible
        setTimeout(() => {
            window.dashboard.initializeWebSocket();
        }, 1000);
    }
});
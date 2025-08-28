// Modern YGG Scraper Dashboard
class YggDashboard {
    constructor() {
        this.ws = null;
        this.isScrapingActive = false;
        this.init();
    }

    async init() {
        await this.loadStats();
        this.initWebSocket();
        this.bindEvents();
        this.startPolling();
    }

    // WebSocket connection for real-time updates
    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
            // Reconnect after 5 seconds
            setTimeout(() => this.initWebSocket(), 5000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'scraping_started':
                this.isScrapingActive = true;
                this.updateScrapingStatus('running', data.message);
                break;
            case 'scraping_progress':
                this.updateProgress(data.progress, data.message);
                break;
            case 'scraping_completed':
                this.isScrapingActive = false;
                this.updateScrapingStatus('completed', data.message);
                this.loadStats(); // Refresh stats
                break;
            case 'stats_update':
                this.updateStats(data.stats);
                break;
        }
    }

    // Load dashboard statistics
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            this.updateStats(data);
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showAlert('Erreur lors du chargement des statistiques', 'danger');
        }
    }

    // Update statistics display
    updateStats(stats) {
        document.getElementById('series-count').textContent = stats.anime_series.total_count.toLocaleString();
        document.getElementById('films-count').textContent = stats.anime_films.total_count.toLocaleString();
        document.getElementById('series-last-id').textContent = stats.anime_series.last_known_id || 'N/A';
        document.getElementById('films-last-id').textContent = stats.anime_films.last_known_id || 'N/A';
        
        // Update last scrape times
        const seriesLastScrape = stats.anime_series.last_scrape_time 
            ? new Date(stats.anime_series.last_scrape_time).toLocaleString('fr-FR')
            : 'Jamais';
        const filmsLastScrape = stats.anime_films.last_scrape_time 
            ? new Date(stats.anime_films.last_scrape_time).toLocaleString('fr-FR')
            : 'Jamais';
            
        document.getElementById('series-last-scrape').textContent = seriesLastScrape;
        document.getElementById('films-last-scrape').textContent = filmsLastScrape;

        // Update scheduler status
        const nextRun = stats.scheduler.next_run 
            ? new Date(stats.scheduler.next_run).toLocaleString('fr-FR')
            : 'N/A';
        document.getElementById('next-run').textContent = nextRun;
        
        // Update scraping status
        const isInitialComplete = stats.anime_series.initial_scrape_completed && 
                                  stats.anime_films.initial_scrape_completed;
        this.updateScrapingButtons(isInitialComplete);
    }

    // Update connection status indicator
    updateConnectionStatus(status) {
        const indicator = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        indicator.className = 'status-dot';
        
        switch (status) {
            case 'connected':
                indicator.classList.add('success');
                statusText.textContent = 'Connecté';
                break;
            case 'disconnected':
                indicator.classList.add('warning');
                statusText.textContent = 'Déconnecté';
                break;
            case 'error':
                indicator.classList.add('error');
                statusText.textContent = 'Erreur';
                break;
        }
    }

    // Update scraping status
    updateScrapingStatus(status, message) {
        const statusEl = document.getElementById('scraping-status');
        const messageEl = document.getElementById('scraping-message');
        
        statusEl.className = 'alert';
        
        switch (status) {
            case 'running':
                statusEl.classList.add('alert-info');
                statusEl.innerHTML = '<div class="d-flex align-items-center gap-2"><div class="loading"></div>Scraping en cours...</div>';
                break;
            case 'completed':
                statusEl.classList.add('alert-success');
                statusEl.textContent = 'Scraping terminé avec succès';
                break;
            case 'error':
                statusEl.classList.add('alert-danger');
                statusEl.textContent = 'Erreur lors du scraping';
                break;
        }
        
        if (messageEl && message) {
            messageEl.textContent = message;
        }
    }

    // Update progress bar
    updateProgress(percent, message) {
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.getElementById('progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
        
        if (progressText && message) {
            progressText.textContent = message;
        }
    }

    // Update scraping buttons based on status
    updateScrapingButtons(isInitialComplete) {
        const manualBtn = document.getElementById('manual-scrape-btn');
        const initialBtn = document.getElementById('initial-scrape-btn');
        
        if (this.isScrapingActive) {
            manualBtn.disabled = true;
            initialBtn.disabled = true;
        } else {
            manualBtn.disabled = false;
            initialBtn.disabled = isInitialComplete; // Disable if initial scrape is done
        }
    }

    // Bind event handlers
    bindEvents() {
        // Manual scrape button
        document.getElementById('manual-scrape-btn')?.addEventListener('click', () => {
            this.showConfirmModal(
                'Vérification Manuelle',
                'Êtes-vous sûr de vouloir déclencher une vérification maintenant ?',
                () => this.triggerManualScrape()
            );
        });

        // Initial scrape button
        document.getElementById('initial-scrape-btn')?.addEventListener('click', () => {
            this.showConfirmModal(
                'Scraping Initial Complet',
                'ATTENTION: Cette opération va récupérer TOUS les torrents depuis le début. Cela peut prendre plusieurs heures. Êtes-vous sûr ?',
                () => this.triggerInitialScrape()
            );
        });

        // Table navigation buttons
        document.getElementById('view-series-btn')?.addEventListener('click', () => this.loadTable('series'));
        document.getElementById('view-films-btn')?.addEventListener('click', () => this.loadTable('films'));
        document.getElementById('view-state-btn')?.addEventListener('click', () => this.loadTable('state'));
    }

    // Show confirmation modal
    showConfirmModal(title, message, onConfirm) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').textContent = message;
        
        const modal = document.getElementById('confirm-modal');
        modal.classList.add('show');
        
        const confirmBtn = document.getElementById('confirm-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        
        confirmBtn.onclick = () => {
            modal.classList.remove('show');
            onConfirm();
        };
        
        cancelBtn.onclick = () => {
            modal.classList.remove('show');
        };
        
        // Close on backdrop click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        };
    }

    // Trigger manual scrape
    async triggerManualScrape() {
        try {
            this.isScrapingActive = true;
            this.updateScrapingButtons(false);
            
            const response = await fetch('/api/scrape/trigger', { method: 'POST' });
            const data = await response.json();
            
            if (response.ok) {
                this.showAlert('Vérification déclenchée avec succès', 'success');
            } else {
                throw new Error(data.detail || 'Erreur inconnue');
            }
        } catch (error) {
            console.error('Error triggering scrape:', error);
            this.showAlert(`Erreur: ${error.message}`, 'danger');
            this.isScrapingActive = false;
            this.updateScrapingButtons(true);
        }
    }

    // Trigger initial scrape
    async triggerInitialScrape() {
        try {
            this.isScrapingActive = true;
            this.updateScrapingButtons(false);
            
            const response = await fetch('/api/scrape/initial', { method: 'POST' });
            const data = await response.json();
            
            if (response.ok) {
                this.showAlert('Scraping initial démarré. Cela peut prendre plusieurs heures...', 'info');
            } else {
                throw new Error(data.detail || 'Erreur inconnue');
            }
        } catch (error) {
            console.error('Error triggering initial scrape:', error);
            this.showAlert(`Erreur: ${error.message}`, 'danger');
            this.isScrapingActive = false;
            this.updateScrapingButtons(true);
        }
    }

    // Load table data
    async loadTable(type) {
        const tableContainer = document.getElementById('data-table-container');
        const tableTitle = document.getElementById('table-title');
        
        try {
            let response;
            let title;
            
            switch (type) {
                case 'series':
                    response = await fetch('/api/series?limit=50');
                    title = 'Séries Anime';
                    break;
                case 'films':
                    response = await fetch('/api/films?limit=50');
                    title = 'Films Anime';
                    break;
                case 'state':
                    response = await fetch('/api/scraping-state');
                    title = 'État du Scraping';
                    break;
            }
            
            const data = await response.json();
            tableTitle.textContent = title;
            this.renderTable(data, type, tableContainer);
            
        } catch (error) {
            console.error('Error loading table:', error);
            this.showAlert(`Erreur lors du chargement: ${error.message}`, 'danger');
        }
    }

    // Render table based on type
    renderTable(data, type, container) {
        let html = '<div class="table-container"><table class="table"><thead><tr>';
        
        if (type === 'series' || type === 'films') {
            html += '<th>ID</th><th>Titre</th><th>Seeders</th><th>Leechers</th><th>Taille</th><th>Uploadé le</th></tr></thead><tbody>';
            
            data.data.forEach(item => {
                const size = (item.size / (1024 * 1024 * 1024)).toFixed(2);
                const date = new Date(item.uploaded_at).toLocaleDateString('fr-FR');
                html += `
                    <tr>
                        <td>${item.id}</td>
                        <td title="${item.title}">${item.title.substring(0, 50)}...</td>
                        <td>${item.seeders}</td>
                        <td>${item.leechers}</td>
                        <td>${size} GB</td>
                        <td>${date}</td>
                    </tr>
                `;
            });
        } else if (type === 'state') {
            html += '<th>Catégorie</th><th>Dernier ID</th><th>Dernière vérification</th><th>Scraping initial</th></tr></thead><tbody>';
            
            data.forEach(item => {
                const lastScrape = item.last_scrape_time 
                    ? new Date(item.last_scrape_time).toLocaleString('fr-FR')
                    : 'Jamais';
                html += `
                    <tr>
                        <td>${item.category}</td>
                        <td>${item.last_known_id || 'N/A'}</td>
                        <td>${lastScrape}</td>
                        <td>${item.initial_scrape_completed ? '✅ Terminé' : '❌ En attente'}</td>
                    </tr>
                `;
            });
        }
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    // Show alert message
    showAlert(message, type) {
        const alertContainer = document.getElementById('alert-container');
        const alertEl = document.createElement('div');
        alertEl.className = `alert alert-${type}`;
        alertEl.textContent = message;
        
        alertContainer.appendChild(alertEl);
        
        setTimeout(() => {
            alertEl.remove();
        }, 5000);
    }

    // Start periodic polling (fallback if WebSocket fails)
    startPolling() {
        setInterval(() => {
            if (this.ws?.readyState !== WebSocket.OPEN) {
                this.loadStats();
            }
        }, 30000); // Every 30 seconds
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new YggDashboard();
});
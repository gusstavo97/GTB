class TradingBotUI {
    constructor() {
        this.isRunning = false;
        this.updateInterval = null;
        this.initializeElements();
        this.bindEvents();
        this.startUpdates();
    }

    initializeElements() {
        // Control buttons
        this.startBtn = document.getElementById('start-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.statusBadge = document.getElementById('status-badge');

        // Price elements
        this.currentPrice = document.getElementById('current-price');
        this.priceChange = document.getElementById('price-change');
        this.ema13 = document.getElementById('ema-13');
        this.ema55 = document.getElementById('ema-55');
        this.atr = document.getElementById('atr');

        // Status elements
        this.botStatus = document.getElementById('bot-status');
        this.lastCheck = document.getElementById('last-check');
        this.errorCount = document.getElementById('error-count');
        this.lastSignal = document.getElementById('last-signal');
        this.signalDetails = document.getElementById('signal-details');
        this.signalsTable = document.getElementById('signals-table');
    }

    bindEvents() {
        this.startBtn.addEventListener('click', () => this.startBot());
        this.stopBtn.addEventListener('click', () => this.stopBot());
    }

    async startBot() {
        try {
            this.startBtn.disabled = true;
            this.startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Iniciando...';

            const response = await fetch('/api/start_bot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (response.ok) {
                this.isRunning = true;
                this.updateControlButtons();
                this.showAlert('success', 'Bot iniciado correctamente');
            } else {
                this.showAlert('danger', data.error || 'Error al iniciar el bot');
            }
        } catch (error) {
            this.showAlert('danger', 'Error de conexión: ' + error.message);
        } finally {
            this.startBtn.disabled = false;
            this.startBtn.innerHTML = '<i class="fas fa-play"></i> Iniciar';
        }
    }

    async stopBot() {
        try {
            const response = await fetch('/api/stop_bot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (response.ok) {
                this.isRunning = false;
                this.updateControlButtons();
                this.showAlert('info', 'Bot detenido');
            } else {
                this.showAlert('danger', data.error || 'Error al detener el bot');
            }
        } catch (error) {
            this.showAlert('danger', 'Error de conexión: ' + error.message);
        }
    }

    updateControlButtons() {
        if (this.isRunning) {
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.statusBadge.textContent = 'Ejecutándose';
            this.statusBadge.className = 'badge bg-success me-2';
            this.botStatus.textContent = 'Ejecutándose';
            this.botStatus.className = 'fw-bold status-running';
        } else {
            this.startBtn.disabled = false;
            this.stopBtn.disabled = true;
            this.statusBadge.textContent = 'Detenido';
            this.statusBadge.className = 'badge bg-secondary me-2';
            this.botStatus.textContent = 'Detenido';
            this.botStatus.className = 'fw-bold status-stopped';
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();

            this.isRunning = status.running;
            this.updateControlButtons();

            // Update last check
            if (status.last_check) {
                const date = new Date(status.last_check);
                this.lastCheck.textContent = date.toLocaleString('es-ES');
            }

            // Update error count
            this.errorCount.textContent = status.error_count || 0;

            // Update last signal
            if (status.last_signal) {
                const signal = status.last_signal;
                this.lastSignal.textContent = `${signal.type} - $${signal.entry.toFixed(2)}`;
                this.updateSignalDetails(signal);
            }

        } catch (error) {
            console.error('Error updating status:', error);
        }
    }

    async updatePrice() {
        try {
            const response = await fetch('/api/current_price');
            const data = await response.json();

            if (response.ok) {
                // Update price
                this.currentPrice.textContent = `$${data.price.toLocaleString('es-ES', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                })}`;

                // Update 24h change
                const change = data.change_24h;
                this.priceChange.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
                this.priceChange.className = change >= 0 ? 'h5 mb-0 price-positive' : 'h5 mb-0 price-negative';

                // Update indicators
                this.ema13.textContent = `$${data.ema_13.toFixed(2)}`;
                this.ema55.textContent = `$${data.ema_55.toFixed(2)}`;
                this.atr.textContent = data.atr.toFixed(2);

            }
        } catch (error) {
            console.error('Error updating price:', error);
        }
    }

    async updateSignals() {
        try {
            const response = await fetch('/api/signals');
            const data = await response.json();

            if (data.signals && data.signals.length > 0) {
                this.renderSignalsTable(data.signals);
            }
        } catch (error) {
            console.error('Error updating signals:', error);
        }
    }

    updateSignalDetails(signal) {
        const timestamp = new Date(signal.timestamp).toLocaleString('es-ES');
        const signalClass = signal.type === 'LONG' ? 'signal-long' : 'signal-short';
        const icon = signal.type === 'LONG' ? 'fa-arrow-up' : 'fa-arrow-down';

        this.signalDetails.innerHTML = `
            <div class="${signalClass}">
                <div class="signal-type">
                    <i class="fas ${icon}"></i> ${signal.type}
                </div>
                <div class="signal-price">Entrada: $${signal.entry.toFixed(2)}</div>
                <div class="signal-price">SL: $${signal.stop_loss.toFixed(2)}</div>
                <div class="signal-price">TP: $${signal.take_profit.toFixed(2)}</div>
                <small class="opacity-75">${timestamp}</small>
            </div>
        `;
    }

    renderSignalsTable(signals) {
        if (signals.length === 0) {
            this.signalsTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        No hay señales disponibles
                    </td>
                </tr>
            `;
            return;
        }

        this.signalsTable.innerHTML = signals.map(signal => {
            const timestamp = new Date(signal.timestamp).toLocaleString('es-ES');
            const badgeClass = signal.type === 'LONG' ? 'badge-long' : 'badge-short';
            
            return `
                <tr>
                    <td>${timestamp}</td>
                    <td><span class="badge ${badgeClass}">${signal.type}</span></td>
                    <td>$${signal.entry.toFixed(2)}</td>
                    <td>$${signal.stop_loss.toFixed(2)}</td>
                    <td>$${signal.take_profit.toFixed(2)}</td>
                    <td>${signal.atr.toFixed(2)}</td>
                </tr>
            `;
        }).join('');
    }

    showAlert(type, message) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    startUpdates() {
        // Initial updates
        this.updateStatus();
        this.updatePrice();
        this.updateSignals();

        // Set up periodic updates
        this.updateInterval = setInterval(() => {
            this.updateStatus();
            this.updatePrice();
            this.updateSignals();
        }, 5000); // Update every 5 seconds
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }
}

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new TradingBotUI();
});

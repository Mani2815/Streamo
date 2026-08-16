const API_BASE = '/api/v1/sources';
let currentSourceId = null;
let charts = {};
let currentSchema = {};
let currentPollInterval = null;
let currentView = 'overview';

const app = {
    init() {
        this.setupNavigation();
        this.loadGlobalSources(); // Load once for global selector
        this.navigate('overview');
    },

    setupNavigation() {
        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
                const target = e.target.closest('a');
                target.classList.add('active');
                this.navigate(target.dataset.route);
            });
        });
    },

    async loadGlobalSources() {
        const select = document.getElementById('global-source-select');
        try {
            const res = await fetch(`${API_BASE}/`);
            if (!res.ok) throw new Error('Network error');
            const data = await res.json();
            
            let sources = Array.isArray(data) ? data : (data.sources || []);
            
            const currentVal = select.value;
            select.innerHTML = '<option value="">Select a source...</option>';
            sources.forEach(s => {
                select.innerHTML += `<option value="${s.id}">${s.name}</option>`;
            });
            if (currentVal && sources.find(s => s.id == currentVal)) {
                select.value = currentVal;
            } else if (sources.length > 0 && !currentVal) {
                // select.value = sources[0].id;
                // currentSourceId = select.value;
            }
        } catch (e) {
            console.error('Error loading global sources', e);
        }
    },

    handleGlobalSourceChange() {
        const select = document.getElementById('global-source-select');
        currentSourceId = select.value;
        
        // Immediately clear old data and show skeletons for the active view
        if (currentView === 'analytics') {
            this.clearAnalyticsData();
            if (currentSourceId) this.loadAnalytics();
        } else if (currentView === 'quality') {
            this.clearQualityData();
            if (currentSourceId) this.loadQuality();
        }
    },

    async navigate(viewId) {
        currentView = viewId;
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewId}`).classList.add('active');
        
        if (currentPollInterval) clearInterval(currentPollInterval);

        // Update Global Header
        const titleMap = {
            'overview': 'Pipeline Overview',
            'sources': 'Data Sources',
            'add-source': 'Add Data Source',
            'source-details': 'Source Configuration',
            'analytics': 'Analytics Workspace',
            'quality': 'Data Quality Monitor'
        };
        document.getElementById('global-page-title').innerText = titleMap[viewId] || 'Streamo';

        const selectorContainer = document.getElementById('global-source-selector-container');
        if (viewId === 'analytics' || viewId === 'quality') {
            selectorContainer.classList.remove('hidden');
            await this.loadGlobalSources(); // Ensure fresh
            
            const select = document.getElementById('global-source-select');
            currentSourceId = select.value;

            if (viewId === 'analytics') {
                if (currentSourceId) {
                    this.loadAnalytics();
                    currentPollInterval = setInterval(() => this.loadAnalytics(), 5000);
                } else {
                    this.clearAnalyticsData();
                }
            } else if (viewId === 'quality') {
                if (currentSourceId) {
                    this.loadQuality();
                    currentPollInterval = setInterval(() => this.loadQuality(), 10000);
                } else {
                    this.clearQualityData();
                }
            }
        } else {
            selectorContainer.classList.add('hidden');
            if (viewId === 'overview') {
                this.loadOverview();
                currentPollInterval = setInterval(() => this.loadOverview(), 10000);
            } else if (viewId === 'sources') {
                this.loadSources();
            }
        }
    },

    // --- OVERVIEW ---
    async loadOverview() {
        this.toggleSkeletons('overview', true);
        try {
            const res = await fetch(`${API_BASE}/`);
            const sources = await res.json();
            
            const sourcesList = Array.isArray(sources) ? sources : (sources.sources || []);
            
            const activeCount = sourcesList.filter(s => s.status === 'active').length;
            document.getElementById('ov-active-sources').innerText = activeCount;
            document.getElementById('ov-total-configured').innerText = `of ${sourcesList.length} configured`;
            
            let totalRecords = 0;
            let totalQuality = 0;
            let qualitySources = 0;
            
            const tbody = document.getElementById('ov-sources-body');
            tbody.innerHTML = '';
            
            for (const src of sourcesList) {
                try {
                    const qRes = await fetch(`${API_BASE}/${src.id}/quality`);
                    if (qRes.ok) {
                        const q = await qRes.json();
                        totalRecords += (q.total_records || 0);
                        if (q.quality_rate !== null && q.quality_rate !== undefined) {
                            totalQuality += q.quality_rate;
                            qualitySources++;
                        }
                    }
                } catch (err) {} // ignore individual failures
                
                let badgeClass = 'neutral';
                if (src.status === 'active') badgeClass = 'active';
                if (src.status === 'paused') badgeClass = 'paused';
                if (src.status === 'error') badgeClass = 'error';
                if (src.status === 'stopped') badgeClass = 'stopped';
                
                tbody.innerHTML += `
                    <tr style="cursor:pointer;" onclick="app.viewSourceDetails(${src.id})">
                        <td><strong>${src.name}</strong></td>
                        <td style="font-family: monospace; font-size: 0.8em;">${src.url}</td>
                        <td><span class="badge ${badgeClass}">${src.status}</span></td>
                    </tr>
                `;
            }
            
            document.getElementById('ov-total-records').innerText = totalRecords.toLocaleString();
            document.getElementById('ov-avg-quality').innerText = qualitySources ? (totalQuality / qualitySources).toFixed(1) + '%' : '—';
            
            this.toggleSkeletons('overview', false);
        } catch (e) {
            console.error("Overview load failed", e);
            this.toggleSkeletons('overview', false);
        }
    },
    
    // --- SOURCES ---
    async loadSources() {
        try {
            const res = await fetch(`${API_BASE}/`);
            const data = await res.json();
            const sources = Array.isArray(data) ? data : (data.sources || []);
            
            const tbody = document.getElementById('src-table-body');
            tbody.innerHTML = '';
            
            if (sources.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--text-secondary);">No sources configured.</td></tr>`;
                return;
            }
            
            sources.forEach(src => {
                const date = new Date(src.created_at).toLocaleString();
                let badgeClass = 'neutral';
                if (src.status === 'active') badgeClass = 'active';
                if (src.status === 'paused') badgeClass = 'paused';
                if (src.status === 'stopped') badgeClass = 'stopped';
                
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${src.name}</strong></td>
                        <td><span class="badge ${badgeClass}">${src.status.toUpperCase()}</span></td>
                        <td>${src.poll_interval}s</td>
                        <td>${date}</td>
                        <td><button class="btn secondary" onclick="app.viewSourceDetails(${src.id})">Manage</button></td>
                    </tr>
                `;
            });
        } catch (e) {
            console.error('Error loading sources:', e);
            document.getElementById('src-table-body').innerHTML = `<tr><td colspan="5">Error loading sources.</td></tr>`;
        }
    },

    async viewSourceDetails(id) {
        currentSourceId = id;
        this.navigate('source-details');
        
        try {
            const res = await fetch(`${API_BASE}/${id}`);
            const source = await res.json();
            
            document.getElementById('sd-title').innerText = source.name;
            
            const statusEl = document.getElementById('sd-status');
            statusEl.className = `badge ${source.status === 'active' ? 'active' : (source.status === 'paused' ? 'paused' : 'stopped')}`;
            statusEl.innerText = source.status.toUpperCase();
            
            document.getElementById('sd-url').innerText = source.url;
            document.getElementById('sd-interval').innerText = `${source.poll_interval} sec`;
            document.getElementById('sd-topic').innerText = `streamo.raw.${source.name}`;
            
        } catch(e) {
            console.error(e);
        }
    },

    async startSource() {
        if (!currentSourceId) return;
        await fetch(`${API_BASE}/${currentSourceId}/start`, { method: 'POST' });
        this.viewSourceDetails(currentSourceId);
    },

    async pauseSource() {
        if (!currentSourceId) return;
        await fetch(`${API_BASE}/${currentSourceId}/pause`, { method: 'POST' });
        this.viewSourceDetails(currentSourceId);
    },

    async stopSource() {
        if (!currentSourceId) return;
        await fetch(`${API_BASE}/${currentSourceId}/stop`, { method: 'POST' });
        this.viewSourceDetails(currentSourceId);
    },

    async validateSource() {
        const name = document.getElementById('add-name').value;
        const url = document.getElementById('add-url').value;
        const list = document.getElementById('validation-list');
        
        list.innerHTML = '<li><span class="skeleton skeleton-text short"></span></li>';
        document.getElementById('validation-result').classList.remove('hidden');
        document.getElementById('btn-connect').classList.add('hidden');
        document.getElementById('schema-detected').classList.add('hidden');
        
        try {
            const res = await fetch(`${API_BASE}/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url })
            });
            const result = await res.json();
            list.innerHTML = '';
            
            if (result.valid) {
                list.innerHTML += `<li style="color: var(--success);">✓ URL is valid format</li>`;
                list.innerHTML += `<li style="color: var(--success);">✓ Target API is reachable (HTTP ${result.status_code})</li>`;
                list.innerHTML += `<li style="color: var(--success);">✓ Valid JSON response payload detected</li>`;
                
                if (result.detected_fields && Object.keys(result.detected_fields).length > 0) {
                    currentSchema = result.detected_fields;
                    document.getElementById('schema-detected').classList.remove('hidden');
                    const tbody = document.getElementById('schema-body');
                    tbody.innerHTML = '';
                    for (const [field, type] of Object.entries(result.detected_fields)) {
                        tbody.innerHTML += `<tr><td><code style="background: var(--bg-primary); padding: 2px 4px; border-radius: 4px;">${field}</code></td><td><span class="badge neutral">${type}</span></td></tr>`;
                    }
                }
                document.getElementById('btn-connect').classList.remove('hidden');
            } else {
                list.innerHTML += `<li style="color: var(--danger);">✕ Validation failed</li>`;
                if (result.error) list.innerHTML += `<li style="color: var(--text-secondary);">Reason: ${result.error}</li>`;
            }
        } catch (e) {
            list.innerHTML = `<li style="color: var(--danger);">✕ Network error communicating with Control Plane</li>`;
        }
    },

    async connectSource() {
        const name = document.getElementById('add-name').value;
        const url = document.getElementById('add-url').value;
        const poll_interval = parseInt(document.getElementById('add-interval').value);
        
        try {
            const res = await fetch(`${API_BASE}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, poll_interval })
            });
            if (res.ok) {
                // Navigate to sources and refresh global source dropdowns
                await this.loadGlobalSources();
                this.navigate('sources');
            } else {
                let errMessage = "Failed to connect source.";
                try {
                    const err = await res.json();
                    if (err.detail) errMessage = err.detail;
                } catch(e) {
                    errMessage += ` HTTP ${res.status}`;
                }
                alert("Error: " + errMessage);
            }
        } catch (e) {
            alert("Failed to connect source. Please check your network connection.");
        }
    },

    // --- ANALYTICS ---
    clearAnalyticsData() {
        document.getElementById('analytics-content').classList.add('hidden');
        document.getElementById('analytics-empty').classList.remove('hidden');
        
        // Clear all values
        document.getElementById('kpi-total-records').innerText = '0';
        document.getElementById('kpi-quality-rate').innerText = '0%';
        document.getElementById('kpi-freshness').innerText = '-';
        document.getElementById('kpi-ingestion-rate').innerText = '0 /s';
        
        document.getElementById('analytics-charts').innerHTML = '';
        charts = {};
        
        document.getElementById('insights-list').innerHTML = '';
        document.getElementById('metric-summary-grid').innerHTML = '';
        document.getElementById('records-head').innerHTML = '';
        document.getElementById('records-body').innerHTML = '';
    },

    async loadAnalytics() {
        if (!currentSourceId) return this.clearAnalyticsData();
        
        document.getElementById('analytics-empty').classList.add('hidden');
        document.getElementById('analytics-content').classList.remove('hidden');
        
        // Show skeletons, hide data if this is a fresh switch (data empty)
        const isFresh = document.getElementById('kpi-total-records').innerText === '0' || document.getElementById('kpi-total-records').classList.contains('hidden');
        if (isFresh) {
            this.toggleSkeletons('analytics', true);
        }
        
        try {
            const res = await fetch(`${API_BASE}/${currentSourceId}/analytics`);
            const json = await res.json();
            
            if (isFresh) this.toggleSkeletons('analytics', false);
            
            // 1. KPIs
            if (json.kpis) {
                document.getElementById('kpi-total-records').innerText = (json.kpis.total_records || 0).toLocaleString();
                document.getElementById('kpi-quality-rate').innerText = json.kpis.quality_rate !== null ? (json.kpis.quality_rate.toFixed(1) + '%') : '—';
                document.getElementById('kpi-ingestion-rate').innerText = (json.kpis.ingestion_rate || 0) + ' /s';
                
                if (json.kpis.freshness_seconds !== null && json.kpis.freshness_seconds !== undefined) {
                    const sec = json.kpis.freshness_seconds;
                    if (sec < 60) {
                        document.getElementById('kpi-freshness').innerHTML = `<span class="status-indicator live">Live</span>`;
                    } else if (sec < 3600) {
                        document.getElementById('kpi-freshness').innerHTML = `<span class="status-indicator stale">${Math.floor(sec / 60)}m ago</span>`;
                    } else {
                        document.getElementById('kpi-freshness').innerHTML = `<span class="status-indicator error">${Math.floor(sec / 3600)}h ago</span>`;
                    }
                } else {
                    document.getElementById('kpi-freshness').innerText = '—';
                }
            }
            
            // 2. Insights
            const insightsList = document.getElementById('insights-list');
            insightsList.innerHTML = '';
            if (json.insights && json.insights.length > 0) {
                json.insights.forEach(insight => {
                    let icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
                    if (insight.includes('increased') || insight.includes('surge')) icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>';
                    if (insight.includes('decreased') || insight.includes('drop')) icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>';
                    if (insight.includes('stable')) icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
                    if (insight.includes('anomalies') || insight.includes('degradation')) icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
                    insightsList.innerHTML += `<li><span>${icon}</span> <span>${insight}</span></li>`;
                });
            } else {
                insightsList.innerHTML = '<li><span style="color:var(--text-muted)">Collecting data to generate insights...</span></li>';
            }
            
            // 3. Metric Summary
            const summaryGrid = document.getElementById('metric-summary-grid');
            summaryGrid.innerHTML = '';
            if (json.metrics_summary && Object.keys(json.metrics_summary).length > 0) {
                for (const [metric, stats] of Object.entries(json.metrics_summary)) {
                    let trendColor = 'var(--text-primary)';
                    if (stats.trend.direction === 'up') trendColor = 'var(--success)';
                    if (stats.trend.direction === 'down') trendColor = 'var(--danger)';
                    
                    summaryGrid.innerHTML += `
                        <div class="metric-summary-card">
                            <h4>${metric.charAt(0).toUpperCase() + metric.slice(1)}</h4>
                            <p>Average <span>${stats.avg.toFixed(2)}</span></p>
                            <p>Min / Max <span>${stats.min.toFixed(1)} / ${stats.max.toFixed(1)}</span></p>
                            <p>Trend <span style="color: ${trendColor}">${stats.trend.direction === 'up' ? '▲' : (stats.trend.direction === 'down' ? '▼' : '—')} ${Math.abs(stats.trend.percentage)}%</span></p>
                        </div>
                    `;
                }
            } else {
                summaryGrid.innerHTML = '<div style="color:var(--text-muted); padding:1rem;">No numerical metrics detected in payload.</div>';
            }
            
            // 4. Charts
            const data = json.data || [];
            const schema = json.schema || {};
            const numericFields = Object.keys(schema).filter(k => schema[k] === 'metric');
            
            const chartsGrid = document.getElementById('analytics-charts');
            
            // Clean up stale charts if schema changed or empty
            if (numericFields.length === 0) {
                chartsGrid.innerHTML = '<div style="color:var(--text-muted); padding:1rem; border:1px dashed var(--border); border-radius:8px; text-align:center;">No time-series data available for visualization.</div>';
            } else {
                numericFields.forEach(field => {
                    if (!document.getElementById(`chart-${field}`)) {
                        chartsGrid.innerHTML += `
                            <div class="chart-container">
                                <div class="chart-title">${field.charAt(0).toUpperCase() + field.slice(1)}</div>
                                <canvas id="chart-${field}"></canvas>
                            </div>
                        `;
                    }
                });
                
                const labels = data.map(d => {
                    const dt = new Date(d.timestamp);
                    return `${dt.getHours().toString().padStart(2, '0')}:${dt.getMinutes().toString().padStart(2, '0')}:${dt.getSeconds().toString().padStart(2, '0')}`;
                });
                
                numericFields.forEach(field => {
                    const ctx = document.getElementById(`chart-${field}`);
                    if (!ctx) return;
                    
                    const plotData = data.map(d => d.payload ? d.payload[field] : null);
                    
                    if (charts[field]) {
                        charts[field].data.labels = labels;
                        charts[field].data.datasets[0].data = plotData;
                        charts[field].update('none');
                    } else {
                        // Use CSS variables for chart colors
                        const brandColor = '#4F46E5'; // Indigo
                        const bgColor = 'rgba(79, 70, 229, 0.1)';
                        
                        charts[field] = new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: labels,
                                datasets: [{
                                    label: field,
                                    data: plotData,
                                    borderColor: brandColor,
                                    backgroundColor: bgColor,
                                    borderWidth: 2,
                                    pointRadius: 0,
                                    pointHoverRadius: 4,
                                    tension: 0.3,
                                    fill: true
                                }]
                            },
                            options: {
                                responsive: true,
                                animation: false,
                                plugins: { 
                                    legend: { display: false },
                                    tooltip: {
                                        mode: 'index',
                                        intersect: false,
                                        backgroundColor: '#0F172A',
                                        titleColor: '#FFFFFF',
                                        bodyColor: '#FFFFFF',
                                        padding: 10,
                                        cornerRadius: 4
                                    }
                                },
                                scales: {
                                    x: {
                                        grid: { display: false, drawBorder: false },
                                        ticks: { color: '#94A3B8', maxTicksLimit: 8 }
                                    },
                                    y: {
                                        grid: { color: '#F1F5F9', borderDash: [4, 4], drawBorder: false },
                                        ticks: { color: '#94A3B8' }
                                    }
                                },
                                interaction: {
                                    mode: 'nearest',
                                    axis: 'x',
                                    intersect: false
                                }
                            }
                        });
                    }
                });
            }
            
            // 5. Records
            const recent = [...data].reverse().slice(0, 10);
            const tableFields = Object.keys(schema);
            
            let thead = '<tr><th>Timestamp</th>';
            tableFields.forEach(f => {
                let badge = '';
                if (schema[f] === 'metric') badge = '<span style="font-size:0.7em; margin-left:4px; opacity:0.6;">#</span>';
                if (schema[f] === 'identifier') badge = '<span style="font-size:0.7em; margin-left:4px; opacity:0.6;">ID</span>';
                thead += `<th>${f}${badge}</th>`;
            });
            thead += '</tr>';
            document.getElementById('records-head').innerHTML = thead;
            
            let tbody = '';
            if (recent.length === 0) {
                tbody = `<tr><td colspan="${tableFields.length + 1}" style="text-align:center; padding:2rem; color:var(--text-muted);">No records available</td></tr>`;
            } else {
                recent.forEach(r => {
                    const dt = new Date(r.timestamp);
                    const timeStr = `${dt.getHours().toString().padStart(2,'0')}:${dt.getMinutes().toString().padStart(2,'0')}:${dt.getSeconds().toString().padStart(2,'0')}`;
                    tbody += `<tr><td style="color:var(--text-secondary); font-variant-numeric: tabular-nums;">${timeStr}</td>`;
                    tableFields.forEach(f => {
                        const val = r.payload && r.payload[f] !== undefined ? r.payload[f] : '—';
                        tbody += `<td style="${schema[f] === 'metric' ? 'font-variant-numeric: tabular-nums;' : ''}">${val}</td>`;
                    });
                    tbody += '</tr>';
                });
            }
            document.getElementById('records-body').innerHTML = tbody;
            
        } catch (e) {
            console.error("Analytics load failed", e);
            if (isFresh) this.toggleSkeletons('analytics', false);
        }
    },
    
    // --- QUALITY ---
    clearQualityData() {
        document.getElementById('quality-content').classList.add('hidden');
        document.getElementById('quality-empty').classList.remove('hidden');
        document.getElementById('quality-error').classList.add('hidden');
        
        document.getElementById('dq-rate').innerText = '0%';
        document.getElementById('dq-valid').innerText = '0';
        document.getElementById('dq-invalid').innerText = '0';
        document.getElementById('dq-total').innerText = '0';
        
        document.getElementById('dq-breakdown-card').classList.add('hidden');
        const limitedCards = document.querySelectorAll('#view-quality .limited-data-state');
        limitedCards.forEach(c => c.parentElement.classList.add('hidden'));
    },

    async loadQuality() {
        if (!currentSourceId) return this.clearQualityData();
        
        document.getElementById('quality-empty').classList.add('hidden');
        document.getElementById('quality-error').classList.add('hidden');
        document.getElementById('quality-no-data').classList.add('hidden');
        document.getElementById('quality-content').classList.remove('hidden');
        
        const isFresh = document.getElementById('dq-total').innerText === '0' || document.getElementById('dq-total').classList.contains('hidden');
        if (isFresh) this.toggleSkeletons('quality', true);
        
        try {
            const res = await fetch(`${API_BASE}/${currentSourceId}/quality`);
            if (!res.ok) throw new Error('API Request Failed');
            const q = await res.json();
            
            if (isFresh) this.toggleSkeletons('quality', false);
            
            if (q.total_records === 0) {
                document.getElementById('dq-rate').innerText = '—';
                document.getElementById('dq-valid').innerText = '0';
                document.getElementById('dq-invalid').innerText = '0';
                document.getElementById('dq-total').innerText = '0';
                
                document.getElementById('dq-breakdown-card').classList.add('hidden');
                
                const limitedCards = document.querySelectorAll('#view-quality .limited-data-state');
                limitedCards.forEach(c => c.parentElement.classList.add('hidden'));
                
                document.getElementById('quality-no-data').classList.remove('hidden');
            } else {
                document.getElementById('dq-rate').innerText = q.quality_rate !== null ? (q.quality_rate.toFixed(1) + '%') : '—';
                document.getElementById('dq-valid').innerText = (q.valid_records || 0).toLocaleString();
                document.getElementById('dq-invalid').innerText = (q.invalid_records || 0).toLocaleString();
                document.getElementById('dq-total').innerText = (q.total_records || 0).toLocaleString();
                
                document.getElementById('dq-breakdown-card').classList.remove('hidden');
                const limitedCards = document.querySelectorAll('#view-quality .limited-data-state');
                limitedCards.forEach(c => c.parentElement.classList.remove('hidden'));
                
                // Update Bars
                const totalViolations = (q.null_violations || 0) + (q.range_violations || 0) + (q.format_violations || 0) + (q.duplicate_records || 0);
                const safeTotal = totalViolations === 0 ? 1 : totalViolations; // prevent div by zero
                
                const nullPct = ((q.null_violations || 0) / safeTotal) * 100;
                const rangePct = ((q.range_violations || 0) / safeTotal) * 100;
                const formatPct = ((q.format_violations || 0) / safeTotal) * 100;
                const dupPct = ((q.duplicate_records || 0) / safeTotal) * 100;
                
                document.getElementById('dq-nulls-text').innerText = (q.null_violations || 0).toLocaleString();
                document.getElementById('dq-nulls-bar').style.width = `${nullPct}%`;
                
                document.getElementById('dq-ranges-text').innerText = (q.range_violations || 0).toLocaleString();
                document.getElementById('dq-ranges-bar').style.width = `${rangePct}%`;
                
                document.getElementById('dq-formats-text').innerText = (q.format_violations || 0).toLocaleString();
                document.getElementById('dq-formats-bar').style.width = `${formatPct}%`;
                
                document.getElementById('dq-duplicates-text').innerText = (q.duplicate_records || 0).toLocaleString();
                document.getElementById('dq-duplicates-bar').style.width = `${dupPct}%`;
            }
        } catch (e) {
            console.error(e);
            if (isFresh) this.toggleSkeletons('quality', false);
            document.getElementById('quality-content').classList.add('hidden');
            document.getElementById('quality-error').classList.remove('hidden');
        }
    },

    // --- UTILITIES ---
    toggleSkeletons(viewId, show) {
        if (viewId === 'overview') {
            const keys = ['sources', 'records', 'quality'];
            keys.forEach(k => {
                const skel = document.getElementById(`ov-kpi-${k}`);
                const val = document.getElementById(`ov-${k === 'sources' ? 'active-sources' : (k === 'records' ? 'total-records' : 'avg-quality')}`);
                if (show) { skel?.classList.remove('hidden'); val?.classList.add('hidden'); }
                else { skel?.classList.add('hidden'); val?.classList.remove('hidden'); }
            });
        } else if (viewId === 'analytics') {
            const kpis = ['rec', 'qual', 'fresh', 'rate'];
            kpis.forEach(k => {
                const skel = document.getElementById(`skel-kpi-${k}`);
                const idMap = {'rec':'kpi-total-records', 'qual':'kpi-quality-rate', 'fresh':'kpi-freshness', 'rate':'kpi-ingestion-rate'};
                const val = document.getElementById(idMap[k]);
                if (show) { skel?.classList.remove('hidden'); val?.classList.add('hidden'); }
                else { skel?.classList.add('hidden'); val?.classList.remove('hidden'); }
            });
            
            const areas = ['charts', 'insights', 'summary', 'records'];
            areas.forEach(a => {
                const skel = document.getElementById(`skel-${a}`);
                const idMap = {'charts':'analytics-charts', 'insights':'insights-list', 'summary':'metric-summary-grid', 'records':'records-container'};
                const val = document.getElementById(idMap[a]);
                if (show) { skel?.classList.remove('hidden'); val?.classList.add('hidden'); }
                else { skel?.classList.add('hidden'); val?.classList.remove('hidden'); }
            });
        } else if (viewId === 'quality') {
            const keys = ['rate', 'valid', 'invalid', 'total'];
            keys.forEach(k => {
                const skel = document.getElementById(`dq-skel-${k}`);
                const val = document.getElementById(`dq-${k}`);
                if (show) { skel?.classList.remove('hidden'); val?.classList.add('hidden'); }
                else { skel?.classList.add('hidden'); val?.classList.remove('hidden'); }
            });
        }
    }
};

window.onload = () => app.init();

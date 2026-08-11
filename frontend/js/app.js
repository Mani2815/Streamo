const API_BASE = '/api/v1/sources';
let currentSourceId = null;
let charts = {};
let currentSchema = {};
let currentPollInterval = null;

const app = {
    init() {
        this.setupNavigation();
        this.navigate('overview');
    },

    setupNavigation() {
        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
                e.target.classList.add('active');
                this.navigate(e.target.dataset.route);
            });
        });
    },

    async navigate(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewId}`).classList.add('active');
        
        if (currentPollInterval) clearInterval(currentPollInterval);

        if (viewId === 'overview') {
            this.loadOverview();
            currentPollInterval = setInterval(() => this.loadOverview(), 10000);
        } else if (viewId === 'sources') {
            this.loadSources();
        } else if (viewId === 'analytics') {
            await this.loadDropdowns('analytics-source-select');
            if (document.getElementById('analytics-source-select').value) {
                this.loadAnalytics();
                currentPollInterval = setInterval(() => this.loadAnalytics(), 5000);
            }
        } else if (viewId === 'quality') {
            await this.loadDropdowns('quality-source-select');
            if (document.getElementById('quality-source-select').value) {
                this.loadQuality();
                currentPollInterval = setInterval(() => this.loadQuality(), 10000);
            }
        }
    },

    async loadOverview() {
        try {
            const res = await fetch(`${API_BASE}/`);
            const sources = await res.json();
            
            document.getElementById('ov-active-sources').innerText = sources.filter(s => s.status === 'active').length;
            
            let totalRecords = 0;
            let totalQuality = 0;
            let activeCount = 0;
            
            const tbody = document.getElementById('ov-sources-body');
            tbody.innerHTML = '';
            
            for (const src of sources) {
                // Fetch quality briefly to get metrics
                const qRes = await fetch(`${API_BASE}/${src.id}/quality`);
                if (qRes.ok) {
                    const q = await qRes.json();
                    totalRecords += (q.total_records || 0);
                    if (q.quality_rate) {
                        totalQuality += q.quality_rate;
                        activeCount++;
                    }
                }
                
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${src.name}</strong></td>
                        <td>${src.url}</td>
                        <td><span class="badge ${src.status}">${src.status}</span></td>
                    </tr>
                `;
            }
            
            document.getElementById('ov-total-records').innerText = totalRecords.toLocaleString();
            document.getElementById('ov-avg-quality').innerText = activeCount ? (totalQuality / activeCount).toFixed(1) + '%' : '0%';
            
        } catch (e) {
            console.error("Overview load failed", e);
        }
    },
    
    async loadSources() {
        try {
            console.log(`[DEBUG] Fetching sources from: ${API_BASE}/`);
            const res = await fetch(`${API_BASE}/`);
            console.log(`[DEBUG] HTTP Status: ${res.status}`);
            
            const sources = await res.json();
            console.log(`[DEBUG] Response JSON:`, sources);
            console.log(`[DEBUG] Number of sources received:`, Array.isArray(sources) ? sources.length : 'not an array');
            
            const tbody = document.getElementById('src-table-body');
            tbody.innerHTML = '';
            
            if (Array.isArray(sources)) {
                sources.forEach(src => {
                    const date = new Date(src.created_at).toLocaleString();
                    tbody.innerHTML += `
                        <tr>
                            <td><strong>${src.name}</strong></td>
                            <td><span class="badge ${src.status}">${src.status}</span></td>
                            <td>${src.poll_interval}s</td>
                            <td>${date}</td>
                            <td><button class="btn secondary" onclick="app.viewSourceDetails(${src.id})">View Details</button></td>
                        </tr>
                    `;
                });
            } else if (sources.sources) {
                sources.sources.forEach(src => {
                    const date = new Date(src.created_at).toLocaleString();
                    tbody.innerHTML += `
                        <tr>
                            <td><strong>${src.name}</strong></td>
                            <td><span class="badge ${src.status}">${src.status}</span></td>
                            <td>${src.poll_interval}s</td>
                            <td>${date}</td>
                            <td><button class="btn secondary" onclick="app.viewSourceDetails(${src.id})">View Details</button></td>
                        </tr>
                    `;
                });
            }
        } catch (e) {
            console.error('[DEBUG] Error loading sources:', e);
            document.getElementById('src-table-body').innerHTML = `<tr><td colspan="5">Error loading sources: ${e.message}</td></tr>`;
        }
    },

    async viewSourceDetails(id) {
        currentSourceId = id;
        this.navigate('source-details');
        
        try {
            const res = await fetch(`${API_BASE}/${id}`);
            const source = await res.json();
            
            document.getElementById('sd-title').innerText = source.name;
            document.getElementById('sd-status').className = `badge ${source.status}`;
            document.getElementById('sd-status').innerText = source.status.toUpperCase();
            document.getElementById('sd-url').innerText = source.url;
            document.getElementById('sd-interval').innerText = source.poll_interval;
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
        list.innerHTML = '<li>Validating...</li>';
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
                list.innerHTML += `<li class="valid">✓ URL is valid</li>`;
                list.innerHTML += `<li class="valid">✓ API is reachable (HTTP ${result.status_code})</li>`;
                list.innerHTML += `<li class="valid">✓ JSON response detected</li>`;
                
                if (result.detected_fields && Object.keys(result.detected_fields).length > 0) {
                    currentSchema = result.detected_fields;
                    document.getElementById('schema-detected').classList.remove('hidden');
                    const tbody = document.getElementById('schema-body');
                    tbody.innerHTML = '';
                    for (const [field, type] of Object.entries(result.detected_fields)) {
                        tbody.innerHTML += `<tr><td>${field}</td><td><span class="badge active">${type}</span></td></tr>`;
                    }
                }
                document.getElementById('btn-connect').classList.remove('hidden');
            } else {
                list.innerHTML += `<li class="invalid">✕ API validation failed</li>`;
                if (result.error) list.innerHTML += `<li>Reason: ${result.error}</li>`;
            }
        } catch (e) {
            list.innerHTML = `<li class="invalid">✕ Network error communicating with Control Plane</li>`;
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
                alert("Source Connected Successfully! Pipeline is initializing.");
                this.navigate('sources');
            } else {
                const err = await res.json();
                alert("Error: " + err.detail);
            }
        } catch (e) {
            alert("Failed to connect source.");
        }
    },
    
    async loadDropdowns(elementId) {
        const select = document.getElementById(elementId);
        if (!select) return;
        const currentVal = select.value;
        try {
            const res = await fetch(`${API_BASE}/`);
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            const sources = await res.json();
            
            select.innerHTML = '<option value="">Select a source...</option>';
            
            let sourcesArray = sources;
            if (!Array.isArray(sources)) {
                if (sources && sources.sources && Array.isArray(sources.sources)) {
                    sourcesArray = sources.sources;
                } else {
                    throw new Error("API did not return a valid sources array");
                }
            }
            
            sourcesArray.forEach(s => {
                select.innerHTML += `<option value="${s.id}">${s.name}</option>`;
            });
            if (currentVal) select.value = currentVal;
        } catch (e) {
            console.error(`Error loading dropdown ${elementId}:`, e);
            select.innerHTML = `<option value="">Error: ${e.message}</option>`;
        }
    },

    async loadAnalytics() {
        const id = document.getElementById('analytics-source-select').value;
        if (!id) {
            document.getElementById('analytics-content').classList.add('hidden');
            document.getElementById('analytics-empty').classList.remove('hidden');
            return;
        }
        
        document.getElementById('analytics-content').classList.remove('hidden');
        document.getElementById('analytics-empty').classList.add('hidden');
        
        try {
            const res = await fetch(`${API_BASE}/${id}/analytics`);
            const json = await res.json();
            
            // 1. Populate KPIs
            if (json.kpis) {
                document.getElementById('kpi-total-records').innerText = (json.kpis.total_records || 0).toLocaleString();
                document.getElementById('kpi-quality-rate').innerText = (json.kpis.quality_rate || 0).toFixed(1) + '%';
                document.getElementById('kpi-ingestion-rate').innerText = (json.kpis.ingestion_rate || 0) + ' /sec';
                
                if (json.kpis.freshness_seconds !== null && json.kpis.freshness_seconds !== undefined) {
                    const sec = json.kpis.freshness_seconds;
                    if (sec < 60) {
                        document.getElementById('kpi-freshness').innerText = `${sec} sec ago`;
                    } else if (sec < 3600) {
                        document.getElementById('kpi-freshness').innerText = `${Math.floor(sec / 60)} min ago`;
                    } else {
                        document.getElementById('kpi-freshness').innerText = `${Math.floor(sec / 3600)} hr ago`;
                    }
                } else {
                    document.getElementById('kpi-freshness').innerText = '-';
                }
            }
            
            // 2. Populate Insights
            const insightsList = document.getElementById('insights-list');
            insightsList.innerHTML = '';
            if (json.insights && json.insights.length > 0) {
                json.insights.forEach(insight => {
                    let icon = '💡';
                    if (insight.includes('increased')) icon = '↑';
                    if (insight.includes('decreased')) icon = '↓';
                    if (insight.includes('stable')) icon = '→';
                    if (insight.includes('anomalies')) icon = '⚠';
                    insightsList.innerHTML += `<li>${icon} ${insight}</li>`;
                });
            } else {
                insightsList.innerHTML = '<li>No insights available.</li>';
            }
            
            // 3. Populate Metric Summary
            const summaryGrid = document.getElementById('metric-summary-grid');
            summaryGrid.innerHTML = '';
            if (json.metrics_summary) {
                for (const [metric, stats] of Object.entries(json.metrics_summary)) {
                    summaryGrid.innerHTML += `
                        <div class="metric-summary-card">
                            <h4>${metric.charAt(0).toUpperCase() + metric.slice(1)}</h4>
                            <p>Average <span>${stats.avg}</span></p>
                            <p>Min <span>${stats.min}</span></p>
                            <p>Max <span>${stats.max}</span></p>
                            <p>Trend <span>${stats.trend.direction} (${stats.trend.percentage}%)</span></p>
                        </div>
                    `;
                }
            }
            
            const data = json.data || [];
            
            // 4. Update Charts
            const schema = json.schema || {};
            const numericFields = Object.keys(schema).filter(k => schema[k] === 'metric');
            
            const chartsGrid = document.getElementById('analytics-charts');
            
            numericFields.forEach(field => {
                if (!document.getElementById(`chart-${field}`)) {
                    chartsGrid.innerHTML += `
                        <div class="chart-container">
                            <h3>${field.charAt(0).toUpperCase() + field.slice(1)}</h3>
                            <canvas id="chart-${field}"></canvas>
                        </div>
                    `;
                }
            });
            
            const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
            
            numericFields.forEach(field => {
                const ctx = document.getElementById(`chart-${field}`);
                if (!ctx) return;
                
                const plotData = data.map(d => d.payload ? d.payload[field] : null);
                
                if (charts[field]) {
                    charts[field].data.labels = labels;
                    charts[field].data.datasets[0].data = plotData;
                    charts[field].update('none');
                } else {
                    charts[field] = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: field,
                                data: plotData,
                                borderColor: '#0000FF',
                                backgroundColor: 'rgba(0, 0, 255, 0.1)',
                                tension: 0.4,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            animation: false,
                            plugins: { 
                                legend: { display: false },
                                tooltip: {
                                    backgroundColor: '#0000FF',
                                    titleColor: '#F7F7FF',
                                    bodyColor: '#F7F7FF'
                                }
                            },
                            scales: {
                                x: {
                                    grid: { color: 'rgba(0, 0, 255, 0.08)' },
                                    ticks: { color: 'rgba(0, 0, 255, 0.65)', maxTicksLimit: 10 }
                                },
                                y: {
                                    grid: { color: 'rgba(0, 0, 255, 0.08)' },
                                    ticks: { color: 'rgba(0, 0, 255, 0.65)' }
                                }
                            }
                        }
                    });
                }
            });
            
            // 5. Update Latest Records
            const recent = [...data].reverse().slice(0, 10);
            
            // Fields to show in table
            const tableFields = Object.keys(schema);
            
            let thead = '<tr><th>Timestamp</th>';
            tableFields.forEach(f => {
                if (schema[f] === 'metric') {
                    thead += `<th>${f} 📊</th>`;
                } else if (schema[f] === 'identifier') {
                    thead += `<th>${f} 🔑</th>`;
                } else {
                    thead += `<th>${f}</th>`;
                }
            });
            thead += '</tr>';
            document.getElementById('records-head').innerHTML = thead;
            
            let tbody = '';
            recent.forEach(r => {
                tbody += `<tr><td>${new Date(r.timestamp).toLocaleString()}</td>`;
                tableFields.forEach(f => {
                    tbody += `<td>${r.payload && r.payload[f] !== undefined ? r.payload[f] : '-'}</td>`;
                });
                tbody += '</tr>';
            });
            document.getElementById('records-body').innerHTML = tbody;
            
        } catch (e) {
            console.error("Analytics load failed", e);
        }
    },
    
    async loadQuality() {
        const id = document.getElementById('quality-source-select').value;
        if (!id) {
            document.getElementById('quality-content').classList.add('hidden');
            document.getElementById('quality-empty').classList.remove('hidden');
            return;
        }
        
        document.getElementById('quality-content').classList.remove('hidden');
        document.getElementById('quality-empty').classList.add('hidden');
        
        const statusMsg = document.getElementById('quality-status-msg');
        const dataContainer = document.getElementById('quality-data-container');
        
        // Clear state and show loading
        statusMsg.innerText = 'Loading quality metrics...';
        statusMsg.classList.remove('hidden');
        dataContainer.classList.add('hidden');
        document.getElementById('dq-breakdown-title').classList.add('hidden');
        document.getElementById('dq-breakdown-card').classList.add('hidden');
        
        document.getElementById('dq-rate').innerText = '—';
        document.getElementById('dq-valid').innerText = '0';
        document.getElementById('dq-invalid').innerText = '0';
        
        try {
            const res = await fetch(`${API_BASE}/${id}/quality`);
            if (!res.ok) throw new Error('API Request Failed');
            const q = await res.json();
            
            statusMsg.classList.add('hidden');
            dataContainer.classList.remove('hidden');
            
            if (q.total_records === 0) {
                document.getElementById('dq-rate').innerText = '—';
                document.getElementById('dq-valid').innerText = '0';
                document.getElementById('dq-invalid').innerText = '0';
            } else {
                document.getElementById('dq-rate').innerText = q.quality_rate !== null ? (q.quality_rate.toFixed(1) + '%') : '—';
                document.getElementById('dq-valid').innerText = (q.valid_records || 0).toLocaleString();
                document.getElementById('dq-invalid').innerText = (q.invalid_records || 0).toLocaleString();
                
                // Show breakdown if there's any data
                document.getElementById('dq-breakdown-title').classList.remove('hidden');
                document.getElementById('dq-breakdown-card').classList.remove('hidden');
                document.getElementById('dq-nulls').innerText = (q.null_violations || 0).toLocaleString();
                document.getElementById('dq-ranges').innerText = (q.range_violations || 0).toLocaleString();
                document.getElementById('dq-formats').innerText = (q.format_violations || 0).toLocaleString();
            }
        } catch (e) {
            console.error(e);
            statusMsg.innerText = 'Unable to load quality metrics.';
            statusMsg.classList.remove('hidden');
            dataContainer.classList.add('hidden');
        }
    }
};

window.onload = () => app.init();

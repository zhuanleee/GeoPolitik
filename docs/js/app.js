/**
 * GeoPolitik — Game Theory Trading Intelligence Dashboard
 * Vanilla JS, single-file app following ORB-Platform pattern
 */

// ── Configuration ─────────────────────────────────────────────────────
const CONFIG = {
    // Update this after Modal deploy
    API_BASE: 'https://johnlee0625--geopol-api-fastapi-app.modal.run',
    CACHE_TTL: 5 * 60 * 1000, // 5 min cache
    AUTO_REFRESH: 10 * 60 * 1000, // 10 min auto-refresh
};

// ── State ─────────────────────────────────────────────────────────────
const state = {
    events: [],
    analyses: [],
    tradeIdeas: [],
    predictionMarkets: [],
    selectedEvent: null,
    selectedAnalysis: null,
    activeTab: localStorage.getItem('geopol_tab') || 'events',
    tradeFilter: 'all',
};

// ── Cache Layer ───────────────────────────────────────────────────────
const cache = new Map();

async function apiFetch(path, options = {}) {
    const url = `${CONFIG.API_BASE}${path}`;
    const cacheKey = url + JSON.stringify(options);

    // Check cache
    if (!options.noCache) {
        const cached = cache.get(cacheKey);
        if (cached && Date.now() - cached.ts < CONFIG.CACHE_TTL) {
            return cached.data;
        }
    }

    try {
        const resp = await fetch(url, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers },
        });
        if (!resp.ok) throw new Error(`API ${resp.status}: ${resp.statusText}`);
        const data = await resp.json();
        cache.set(cacheKey, { data, ts: Date.now() });
        updateApiStatus(true);
        return data;
    } catch (err) {
        console.error(`[GeoPolitik] API error: ${path}`, err);
        updateApiStatus(false);
        throw err;
    }
}

// ── UI Helpers ────────────────────────────────────────────────────────
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function updateApiStatus(online) {
    const dot = $('#apiStatus');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
}

function updateTimestamp() {
    $('#lastUpdated').textContent = `Updated ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' })} ET`;
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function truncate(str, len = 120) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
}

// ── Tab Router ────────────────────────────────────────────────────────
function showTab(tabName) {
    state.activeTab = tabName;
    localStorage.setItem('geopol_tab', tabName);

    $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    $$('.tab-content').forEach(tc => tc.classList.toggle('active', tc.id === `tab-${tabName}`));

    // Lazy-load tab data
    if (tabName === 'events' && state.events.length === 0) loadEvents();
    if (tabName === 'analysis') loadAnalysisList();
    if (tabName === 'trades') renderTrades();
    if (tabName === 'markets') loadPredictionMarkets();
}

// ── Events Tab ────────────────────────────────────────────────────────
async function loadEvents() {
    const list = $('#eventList');
    list.innerHTML = '<div class="loading">Fetching events...</div>';

    try {
        const data = await apiFetch('/events/latest?limit=50');
        state.events = data.events || [];
        renderEvents();
    } catch {
        // Try cached
        try {
            const data = await apiFetch('/events/cached?days=3&limit=50');
            state.events = data.events || [];
            renderEvents();
        } catch {
            list.innerHTML = '<div class="placeholder-text">Could not load events. Check API connection.</div>';
        }
    }
}

function renderEvents() {
    const list = $('#eventList');
    const regionFilter = $('#regionFilter').value;
    const searchTerm = $('#eventSearch').value.toLowerCase();

    let filtered = state.events;
    if (regionFilter !== 'all') {
        filtered = filtered.filter(e => e.region === regionFilter);
    }
    if (searchTerm) {
        filtered = filtered.filter(e =>
            e.title.toLowerCase().includes(searchTerm) ||
            (e.summary || '').toLowerCase().includes(searchTerm)
        );
    }

    if (filtered.length === 0) {
        list.innerHTML = '<div class="placeholder-text">No events match your filters</div>';
        return;
    }

    list.innerHTML = filtered.map(event => {
        const relevClass = event.relevance_score >= 50 ? 'high' : event.relevance_score >= 25 ? 'medium' : 'low';
        const selected = state.selectedEvent?.id === event.id ? 'selected' : '';
        return `
            <div class="event-card ${selected}" data-id="${event.id}">
                <div class="event-title">${escapeHtml(event.title)}</div>
                <div class="event-meta">
                    <span class="badge badge-region" data-region="${event.region}">${event.region}</span>
                    <span class="badge badge-relevance ${relevClass}">${Math.round(event.relevance_score)}</span>
                    <span class="event-time">${timeAgo(event.published_at)}</span>
                    ${event.actors?.length ? event.actors.slice(0, 3).map(a => `<span class="player-pill">${a}</span>`).join('') : ''}
                    <button class="btn btn-analyze" data-id="${event.id}">Analyze</button>
                </div>
            </div>
        `;
    }).join('');
}

function selectEvent(eventId) {
    state.selectedEvent = state.events.find(e => e.id === eventId) || null;
    renderEvents();
    renderQuickAnalysis();
}

function renderQuickAnalysis() {
    const panel = $('#quickAnalysis');
    const event = state.selectedEvent;

    if (!event) {
        panel.innerHTML = '<div class="placeholder-text">Select an event to view details</div>';
        return;
    }

    panel.innerHTML = `
        <div class="qa-topic">${escapeHtml(event.title)}</div>

        <div class="qa-section">
            <div class="qa-section-title">Summary</div>
            <p style="font-size:13px;color:var(--text-secondary);line-height:1.6">${escapeHtml(event.summary || 'No summary available')}</p>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Detected Actors</div>
            <div class="qa-players">
                ${(event.actors || []).map(a => `<span class="player-pill">${a}</span>`).join('') || '<span style="color:var(--text-muted)">None detected</span>'}
            </div>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Keywords</div>
            <div class="qa-players">
                ${(event.keywords || []).map(k => `<span class="player-pill" style="background:rgba(139,92,246,0.15);border-color:rgba(139,92,246,0.3);color:var(--color-accent)">${k}</span>`).join('') || '—'}
            </div>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Details</div>
            <div style="font-size:12px;color:var(--text-muted)">
                <div>Region: ${event.region}</div>
                <div>Relevance: ${Math.round(event.relevance_score)}/100</div>
                <div>Published: ${event.published_at ? new Date(event.published_at).toLocaleString('en-US', { timeZone: 'America/New_York' }) : '—'}</div>
                ${event.sources?.length ? `<div style="margin-top:8px"><a href="${event.sources[0]}" target="_blank" style="color:var(--text-accent)">Source →</a></div>` : ''}
            </div>
        </div>

        <div style="margin-top:16px">
            <button class="btn btn-primary" onclick="runAnalysis('${event.id}')" style="width:100%">
                Run Full Game Theory Analysis
            </button>
        </div>
    `;
}

// ── Analysis ──────────────────────────────────────────────────────────
async function runAnalysis(eventId) {
    const panel = eventId ? $('#quickAnalysis') : $('#analysisContent');
    panel.innerHTML = '<div class="loading">Running game theory analysis... (this may take 15-30 seconds)</div>';

    try {
        let url;
        if (eventId) {
            url = `/analysis/run?event_id=${eventId}`;
        } else {
            const topic = $('#customTopic').value;
            const actors = $('#customActors').value;
            if (!topic) return;
            url = `/analysis/run?topic=${encodeURIComponent(topic)}&actors=${encodeURIComponent(actors)}`;
        }

        const data = await apiFetch(url, { method: 'POST', noCache: true });
        state.selectedAnalysis = data;

        // Extract trade ideas
        if (data.trade_ideas?.length) {
            state.tradeIdeas = [...state.tradeIdeas, ...data.trade_ideas];
        }

        if (eventId) {
            renderQuickAnalysisResult(data);
        } else {
            renderDeepAnalysis(data);
        }

        // Refresh analysis list
        loadAnalysisList();
    } catch (err) {
        panel.innerHTML = `<div class="placeholder-text">Analysis failed: ${err.message}</div>`;
    }
}

function renderQuickAnalysisResult(analysis) {
    const panel = $('#quickAnalysis');
    panel.innerHTML = `
        <div class="qa-topic">${escapeHtml(analysis.topic)}</div>

        <div class="qa-section">
            <div class="qa-section-title">Incentive Convergence</div>
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <span class="badge badge-convergence ${analysis.incentive_convergence}">${analysis.incentive_convergence}</span>
                <span style="font-size:13px;color:var(--text-secondary)">${escapeHtml(analysis.convergence_direction)}</span>
            </div>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Players</div>
            <div class="qa-players">
                ${(analysis.players || []).map(p => `<span class="player-pill" title="${escapeHtml(p.dominant_strategy)}">${p.name}</span>`).join('')}
            </div>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Nash Equilibrium</div>
            <div class="qa-equilibrium">${escapeHtml(analysis.nash_equilibrium)}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Stability: ${analysis.equilibrium_stability}</div>
        </div>

        <div class="qa-section">
            <div class="qa-section-title">Scenarios</div>
            ${(analysis.scenarios || []).map(s => `
                <div class="qa-scenario-card">
                    <div class="qa-scenario-header">
                        <span class="qa-scenario-title">${escapeHtml(s.title)}</span>
                        <span class="qa-scenario-prob">${s.probability}%</span>
                    </div>
                    <div class="prob-bar"><div class="prob-bar-fill" style="width:${s.probability}%"></div></div>
                    <div class="qa-scenario-desc">${escapeHtml(s.description)}</div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Timeline: ~${s.timeline_days} days</div>
                </div>
            `).join('')}
        </div>

        ${analysis.trade_ideas?.length ? `
        <div class="qa-section">
            <div class="qa-section-title">Trade Ideas</div>
            ${analysis.trade_ideas.map(t => `
                <div class="qa-scenario-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                        <span class="badge badge-conviction ${t.conviction}">${t.conviction}</span>
                        <span class="direction-${t.direction}" style="font-weight:600;font-size:12px">${t.direction.toUpperCase()}</span>
                    </div>
                    <div style="margin-bottom:4px">
                        <span style="font-size:12px;color:var(--text-muted)">${t.structure}</span>
                        <span style="font-size:11px;color:var(--text-muted);margin-left:8px">DTE: ${t.suggested_dte}</span>
                    </div>
                    <div class="trade-assets">${t.assets.map(a => `<span class="trade-asset">${a}</span>`).join('')}</div>
                    <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;line-height:1.5">${escapeHtml(t.rationale)}</div>
                </div>
            `).join('')}
        </div>` : ''}

        <div style="margin-top:12px">
            <button class="btn" onclick="showTab('analysis');renderDeepAnalysis(state.selectedAnalysis)" style="width:100%">
                View Full Analysis →
            </button>
        </div>
    `;
}

async function loadAnalysisList() {
    try {
        const data = await apiFetch('/analysis/latest/list?limit=20');
        state.analyses = data.analyses || [];
        const sel = $('#analysisSelector');
        sel.innerHTML = '<option value="">Select an analysis...</option>' +
            state.analyses.map(a =>
                `<option value="${a.id}">[${a.convergence}] ${escapeHtml(a.topic)} (${timeAgo(a.analyzed_at)})</option>`
            ).join('');
    } catch { /* silent */ }
}

async function loadAnalysisById(id) {
    if (!id) return;
    const panel = $('#analysisContent');
    panel.innerHTML = '<div class="loading">Loading analysis...</div>';
    try {
        const data = await apiFetch(`/analysis/${id}`);
        state.selectedAnalysis = data;
        renderDeepAnalysis(data);
    } catch (err) {
        panel.innerHTML = `<div class="placeholder-text">Failed to load: ${err.message}</div>`;
    }
}

function renderDeepAnalysis(analysis) {
    if (!analysis) return;
    const panel = $('#analysisContent');

    panel.innerHTML = `
        <div class="analysis-grid">
            <!-- Players -->
            <div class="analysis-section full-width">
                <h3>Players & Strategies</h3>
                <div class="player-cards">
                    ${(analysis.players || []).map(p => `
                        <div class="player-card">
                            <div class="player-card-header">
                                <span class="player-name">${escapeHtml(p.name)}</span>
                                <span class="player-type">${p.type}</span>
                            </div>
                            <div class="player-detail"><strong>Objective:</strong> ${escapeHtml(p.primary_objective)}</div>
                            ${p.red_lines?.length ? `<div class="player-detail"><strong>Red lines:</strong> ${p.red_lines.map(r => escapeHtml(r)).join(', ')}</div>` : ''}
                            <div class="player-strategy">
                                <strong>Dominant Strategy:</strong> ${escapeHtml(p.dominant_strategy)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Convergence Gauge -->
            <div class="analysis-section">
                <h3>Incentive Convergence</h3>
                <div class="convergence-gauge">
                    <div class="gauge-value ${analysis.incentive_convergence}">${analysis.incentive_convergence}</div>
                    <div class="gauge-label">Equilibrium: ${analysis.equilibrium_stability}</div>
                    <div class="gauge-direction">"${escapeHtml(analysis.convergence_direction)}"</div>
                </div>
                <div class="qa-equilibrium" style="margin-top:16px">${escapeHtml(analysis.nash_equilibrium)}</div>
                <div style="font-size:12px;color:var(--text-muted);margin-top:8px">Confidence: ${analysis.confidence}/100</div>
            </div>

            <!-- Scenarios -->
            <div class="analysis-section">
                <h3>Scenarios</h3>
                <div class="scenario-cards">
                    ${(analysis.scenarios || []).map(s => `
                        <div class="qa-scenario-card">
                            <div class="qa-scenario-header">
                                <span class="qa-scenario-title">${escapeHtml(s.title)}</span>
                                <span class="qa-scenario-prob">${s.probability}%</span>
                            </div>
                            <div class="prob-bar"><div class="prob-bar-fill" style="width:${s.probability}%"></div></div>
                            <div class="qa-scenario-desc">${escapeHtml(s.description)}</div>
                            <div style="margin-top:8px;font-size:11px">
                                <div style="color:var(--text-muted)">Timeline: ~${s.timeline_days} days</div>
                                ${s.triggers?.length ? `<div style="color:var(--color-bullish);margin-top:4px">Triggers: ${s.triggers.map(t => escapeHtml(t)).join(' | ')}</div>` : ''}
                                ${s.invalidators?.length ? `<div style="color:var(--color-bearish);margin-top:2px">Invalidators: ${s.invalidators.map(i => escapeHtml(i)).join(' | ')}</div>` : ''}
                            </div>
                            ${s.market_impact ? `
                                <div style="margin-top:8px;font-size:11px;color:var(--text-secondary)">
                                    ${Object.entries(s.market_impact).map(([k, v]) => `<div><strong>${k}:</strong> ${escapeHtml(String(v))}</div>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Trade Ideas -->
            <div class="analysis-section full-width">
                <h3>Trade Ideas</h3>
                ${analysis.trade_ideas?.length ? `
                <table class="trades-table">
                    <thead>
                        <tr><th>Scenario</th><th>Conviction</th><th>Direction</th><th>Assets</th><th>Structure</th><th>DTE</th><th>Rationale</th></tr>
                    </thead>
                    <tbody>
                        ${analysis.trade_ideas.map(t => `
                            <tr>
                                <td>${escapeHtml(t.scenario_title)}</td>
                                <td><span class="badge badge-conviction ${t.conviction}">${t.conviction}</span></td>
                                <td><span class="direction-${t.direction}">${t.direction}</span></td>
                                <td><div class="trade-assets">${t.assets.map(a => `<span class="trade-asset">${a}</span>`).join('')}</div></td>
                                <td>${t.structure}</td>
                                <td style="font-family:var(--font-mono)">${t.suggested_dte}</td>
                                <td style="max-width:300px">${escapeHtml(t.rationale)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ` : '<div class="placeholder-text">No trade ideas generated</div>'}
            </div>

            <!-- Watch For + Uncertainties -->
            <div class="analysis-section">
                <h3>Watch For (Catalysts)</h3>
                <ul class="watch-list">
                    ${(analysis.watch_for || []).map(w => `<li>${escapeHtml(w)}</li>`).join('')}
                </ul>
            </div>
            <div class="analysis-section">
                <h3>Key Uncertainties</h3>
                <ul class="watch-list">
                    ${(analysis.key_uncertainties || []).map(u => `<li style="color:var(--color-neutral)">${escapeHtml(u)}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
}

// ── Trades Tab ────────────────────────────────────────────────────────
function renderTrades() {
    const tbody = $('#tradesBody');
    let trades = state.tradeIdeas;

    if (state.tradeFilter !== 'all') {
        trades = trades.filter(t => t.conviction === state.tradeFilter);
    }

    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="placeholder-text">No trade ideas yet. Run an analysis first.</td></tr>';
        return;
    }

    tbody.innerHTML = trades.map((t, i) => `
        <tr data-idx="${i}">
            <td>${escapeHtml(t.scenario_title)}</td>
            <td><span class="badge badge-conviction ${t.conviction}">${t.conviction}</span></td>
            <td><span class="direction-${t.direction}">${t.direction}</span></td>
            <td><div class="trade-assets">${t.assets.map(a => `<span class="trade-asset">${a}</span>`).join('')}</div></td>
            <td>${t.structure}</td>
            <td style="font-family:var(--font-mono)">${t.suggested_dte}</td>
            <td style="max-width:250px">${escapeHtml(truncate(t.rationale, 100))}</td>
        </tr>
    `).join('');
}

function showTradeDetail(idx) {
    const t = state.tradeIdeas[idx];
    if (!t) return;
    const detail = $('#tradeDetail');
    detail.classList.remove('hidden');
    detail.innerHTML = `
        <h3>${escapeHtml(t.scenario_title)}</h3>
        <div class="trade-detail-grid">
            <div class="trade-detail-section">
                <h4>Structure</h4>
                <p><strong>${t.structure}</strong> — ${t.direction.toUpperCase()}</p>
                <p>DTE: ${t.suggested_dte} days</p>
                <div class="trade-assets" style="margin-top:8px">${t.assets.map(a => `<span class="trade-asset">${a}</span>`).join('')}</div>
            </div>
            <div class="trade-detail-section">
                <h4>Rationale</h4>
                <p>${escapeHtml(t.rationale)}</p>
            </div>
            <div class="trade-detail-section">
                <h4>Entry Notes</h4>
                <p>${escapeHtml(t.entry_notes || 'No specific entry notes')}</p>
            </div>
            <div class="trade-detail-section">
                <h4>Risk Notes</h4>
                <p>${escapeHtml(t.risk_notes || 'Standard options risk applies')}</p>
            </div>
        </div>
    `;
}

// ── Prediction Markets Tab ────────────────────────────────────────────
async function loadPredictionMarkets() {
    const grid = $('#marketsGrid');
    grid.innerHTML = '<div class="loading">Fetching prediction markets...</div>';

    try {
        const data = await apiFetch('/prediction-markets?refresh=false');
        state.predictionMarkets = data.markets || [];
        renderPredictionMarkets();
    } catch {
        grid.innerHTML = '<div class="placeholder-text">Could not load prediction markets</div>';
    }
}

function renderPredictionMarkets() {
    const grid = $('#marketsGrid');
    if (state.predictionMarkets.length === 0) {
        grid.innerHTML = '<div class="placeholder-text">No geopolitical prediction markets found</div>';
        return;
    }

    grid.innerHTML = state.predictionMarkets.map(m => {
        const prob = Math.round((m.probability || 0) * 100);
        const probClass = prob >= 70 ? 'high' : prob >= 40 ? 'mid' : 'low';
        return `
            <div class="market-card">
                <div class="market-question">${escapeHtml(m.question)}</div>
                <div class="market-prob-row">
                    <span class="market-prob ${probClass}">${prob}%</span>
                    <span class="market-source">${m.source}</span>
                </div>
                <div class="prob-bar"><div class="prob-bar-fill" style="width:${prob}%;background:${prob >= 70 ? 'var(--color-bullish)' : prob >= 40 ? 'var(--color-neutral)' : 'var(--color-bearish)'}"></div></div>
                <div class="market-meta">
                    <span>Vol: ${m.volume ? '$' + Number(m.volume).toLocaleString() : '—'}</span>
                    ${m.end_date ? `<span>Ends: ${new Date(m.end_date).toLocaleDateString()}</span>` : ''}
                    ${m.url ? `<a href="${m.url}" target="_blank" style="color:var(--text-accent)">View →</a>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ── Utilities ─────────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(str).replace(/[&<>"']/g, c => map[c]);
}

// ── Event Delegation ──────────────────────────────────────────────────
document.addEventListener('click', e => {
    // Tab clicks
    if (e.target.classList.contains('tab')) {
        showTab(e.target.dataset.tab);
        return;
    }

    // Event card click (select)
    const eventCard = e.target.closest('.event-card');
    if (eventCard && !e.target.classList.contains('btn-analyze')) {
        selectEvent(eventCard.dataset.id);
        return;
    }

    // Analyze button on event card
    if (e.target.classList.contains('btn-analyze')) {
        e.stopPropagation();
        const id = e.target.dataset.id;
        selectEvent(id);
        runAnalysis(id);
        return;
    }

    // Filter pills (trades)
    if (e.target.closest('.filter-pills .pill')) {
        const pill = e.target.closest('.pill');
        $$('.filter-pills .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.tradeFilter = pill.dataset.filter;
        renderTrades();
        return;
    }

    // Trade row click
    const tradeRow = e.target.closest('.trades-table tbody tr');
    if (tradeRow && tradeRow.dataset.idx) {
        showTradeDetail(parseInt(tradeRow.dataset.idx));
        return;
    }
});

// ── Input Event Listeners ─────────────────────────────────────────────
$('#regionFilter')?.addEventListener('change', renderEvents);
$('#eventSearch')?.addEventListener('input', renderEvents);
$('#refreshBtn')?.addEventListener('click', () => {
    cache.clear();
    loadEvents();
    updateTimestamp();
});
$('#analysisSelector')?.addEventListener('change', e => {
    if (e.target.value) loadAnalysisById(e.target.value);
});
$('#runCustomAnalysis')?.addEventListener('click', () => runAnalysis(null));
$('#refreshMarkets')?.addEventListener('click', async () => {
    const grid = $('#marketsGrid');
    grid.innerHTML = '<div class="loading">Refreshing...</div>';
    try {
        const data = await apiFetch('/prediction-markets?refresh=true', { noCache: true });
        state.predictionMarkets = data.markets || [];
        renderPredictionMarkets();
    } catch {
        grid.innerHTML = '<div class="placeholder-text">Refresh failed</div>';
    }
});

// ── Dashboard Init ────────────────────────────────────────────────────
async function loadDashboard() {
    try {
        const data = await apiFetch('/dashboard');
        const m = data.metrics || {};
        $('#metricScenarios').textContent = m.active_scenarios || 0;
        $('#metricHighImpact').textContent = m.high_impact_events_today || 0;
        $('#metricConvergence').textContent = m.avg_convergence ? `${Math.round(m.avg_convergence)}%` : '—';
        $('#metricTrades').textContent = m.open_trade_ideas || 0;

        // Pre-populate state
        if (data.latest_events?.length) state.events = data.latest_events;
        if (data.latest_analyses?.length) state.analyses = data.latest_analyses;
        if (data.prediction_markets?.length) state.predictionMarkets = data.prediction_markets;

        updateTimestamp();
    } catch {
        // Dashboard may not exist yet, load events directly
        loadEvents();
    }
}

// ── Boot ──────────────────────────────────────────────────────────────
(function init() {
    showTab(state.activeTab);
    loadDashboard();

    // Auto-refresh
    setInterval(() => {
        cache.clear();
        loadDashboard();
    }, CONFIG.AUTO_REFRESH);
})();

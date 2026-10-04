// Jigawa Northwest Situation Room Application Logic
let metadata = null;
let currentTab = 'dashboard';
let currentAdmin = null;
let adminToken = localStorage.getItem('sr_admin_token') || null;
let allAgentsList = [];

// Initial bootstrap
document.addEventListener('DOMContentLoaded', async () => {
    await checkAdminAuth();
    await fetchMetadata();
    setupNavigation();
    initAdminLoginForm();
    initAgentRegistrationForm();
    initResultSubmissionForm();
    loadDashboardData();
    setupFilterListeners();
    setupFormCalculations();

    // Auto-refresh feeds every 10 seconds
    setInterval(() => {
        if (currentTab === 'dashboard') {
            loadDashboardData(true);
        } else if (currentTab === 'results') {
            fetchResultsTable();
        } else if (currentTab === 'admin-agents') {
            fetchAdminAgents();
        } else if (currentTab === 'incidents') {
            fetchIncidents();
        }
    }, 10000);
});

// ---------------- ADMIN AUTHENTICATION ----------------
async function checkAdminAuth() {
    if (!adminToken) {
        updateAdminUIState(false);
        return;
    }

    try {
        const res = await fetch('/api/admin/check', {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const data = await res.json();
        if (data.authenticated) {
            currentAdmin = data.admin;
            updateAdminUIState(true);
        } else {
            adminToken = null;
            localStorage.removeItem('sr_admin_token');
            updateAdminUIState(false);
        }
    } catch (e) {
        console.error("Auth check failed", e);
        updateAdminUIState(false);
    }
}

function updateAdminUIState(isAuthenticated) {
    const statusText = document.getElementById('adminStatusText');
    const loginBtn = document.getElementById('adminLoginBtn');
    const bannerUser = document.getElementById('adminBannerUser');

    const resultsLocked = document.getElementById('resultsAdminLocked');
    const resultsFormWrapper = document.getElementById('resultsAdminFormWrapper');
    const agentsLocked = document.getElementById('agentsAdminLocked');
    const agentsContent = document.getElementById('agentsAdminContent');

    if (isAuthenticated && currentAdmin) {
        if (statusText) {
            statusText.className = 'admin-lock-badge authenticated';
            statusText.innerHTML = `🛡️ Admin: ${currentAdmin.username}`;
        }
        if (loginBtn) {
            loginBtn.textContent = 'Logout';
            loginBtn.onclick = adminLogout;
            loginBtn.className = 'btn-secondary';
        }
        if (bannerUser) bannerUser.textContent = `${currentAdmin.full_name} (${currentAdmin.username})`;

        if (resultsLocked) resultsLocked.style.display = 'none';
        if (resultsFormWrapper) resultsFormWrapper.style.display = 'block';

        if (agentsLocked) agentsLocked.style.display = 'none';
        if (agentsContent) agentsContent.style.display = 'block';

        loadAgentsDropdown();
        fetchAdminAgents();
    } else {
        if (statusText) {
            statusText.className = 'admin-lock-badge locked';
            statusText.innerHTML = '🔒 Admin Restricted';
        }
        if (loginBtn) {
            loginBtn.textContent = 'Admin Login';
            loginBtn.onclick = () => openModal('adminLoginModal');
            loginBtn.className = 'btn-primary';
        }

        if (resultsLocked) resultsLocked.style.display = 'block';
        if (resultsFormWrapper) resultsFormWrapper.style.display = 'none';

        if (agentsLocked) agentsLocked.style.display = 'block';
        if (agentsContent) agentsContent.style.display = 'none';
    }
}

function initAdminLoginForm() {
    const form = document.getElementById('adminLoginForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('adminUsername').value.trim();
        const password = document.getElementById('adminPassword').value.trim();
        const alertEl = document.getElementById('adminLoginAlert');

        try {
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (data.success) {
                adminToken = data.token;
                currentAdmin = data.admin;
                localStorage.setItem('sr_admin_token', adminToken);
                updateAdminUIState(true);
                closeModal('adminLoginModal');
                form.reset();
                alertEl.innerHTML = '';
            } else {
                alertEl.innerHTML = `<div class="alert-box error">${data.message}</div>`;
            }
        } catch (err) {
            alertEl.innerHTML = `<div class="alert-box error">Admin server login error</div>`;
        }
    });
}

async function adminLogout() {
    if (adminToken) {
        try {
            await fetch('/api/admin/logout', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${adminToken}` }
            });
        } catch (e) {}
    }
    adminToken = null;
    currentAdmin = null;
    localStorage.removeItem('sr_admin_token');
    updateAdminUIState(false);
}

// ---------------- NAVIGATION & METADATA ----------------
async function fetchMetadata() {
    try {
        const res = await fetch('/api/metadata');
        metadata = await res.json();
        populateLgaSelects();
    } catch (err) {
        console.error("Failed to load metadata", err);
    }
}

function setupNavigation() {
    const tabs = document.querySelectorAll('.nav-tab-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            switchTab(target);
        });
    });
}

function switchTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.nav-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tabId);
    });

    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.style.display = panel.id === `view-${tabId}` ? 'block' : 'none';
    });

    if (tabId === 'dashboard') {
        loadDashboardData();
    } else if (tabId === 'results') {
        fetchResultsTable();
    } else if (tabId === 'admin-results') {
        checkAdminAuth();
        loadAgentsDropdown();
    } else if (tabId === 'admin-agents') {
        checkAdminAuth();
        fetchAdminAgents();
    } else if (tabId === 'incidents') {
        fetchIncidents();
    }
}

function populateLgaSelects() {
    if (!metadata || !metadata.lgas) return;
    const lgaSelects = document.querySelectorAll('.lga-select');
    lgaSelects.forEach(select => {
        const currentVal = select.value;
        select.innerHTML = '<option value="">-- Select LGA --</option>';
        Object.keys(metadata.lgas).sort().forEach(lga => {
            const opt = document.createElement('option');
            opt.value = lga;
            opt.textContent = lga;
            select.appendChild(opt);
        });
        if (currentVal) select.value = currentVal;
    });

    // Cascade for result entry
    setupLgaWardCascade('entryLga', 'entryWard');
    // Cascade for agent register
    setupLgaWardCascade('regLga', 'regWard');
}

function setupLgaWardCascade(lgaId, wardId) {
    const lgaEl = document.getElementById(lgaId);
    const wardEl = document.getElementById(wardId);
    if (!lgaEl || !wardEl) return;

    lgaEl.addEventListener('change', () => {
        const lga = lgaEl.value;
        wardEl.innerHTML = '<option value="">-- Select Ward --</option>';
        if (metadata.lgas[lga]) {
            metadata.lgas[lga].wards.forEach(w => {
                const opt = document.createElement('option');
                opt.value = w;
                opt.textContent = w;
                wardEl.appendChild(opt);
            });
        }
    });
}

// ---------------- DASHBOARD AGGREGATES & METRICS ----------------
async function loadDashboardData(silent = false) {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();
        const m = data.metrics;

        // Render KPI counters
        document.getElementById('kpiReportedPus').textContent = Number(m.reported_pus || 0).toLocaleString();
        document.getElementById('kpiAccredited').textContent = Number(m.total_accredited || 0).toLocaleString();
        document.getElementById('kpiValidVotes').textContent = Number(m.total_valid_votes || 0).toLocaleString();
        document.getElementById('kpiFlaggedPus').textContent = Number(m.flagged_count || 0).toLocaleString();

        // Render Leaderboard Standings
        renderLeaderboard(data.party_totals, m.total_valid_votes);

        // Render LGA Breakdown Cards/Table
        renderLgaSummary(data.lga_breakdown);

        // Render ticker if broadcasts exist
        loadBroadcasts();

        // Render latest incoming feed
        renderLatestFeed(data.latest_results);

        if (!silent) {
            document.getElementById('lastUpdatedTime').textContent = new Date().toLocaleTimeString();
        }
    } catch (err) {
        console.error("Error loading dashboard data", err);
    }
}

function renderLeaderboard(parties, totalValid) {
    const container = document.getElementById('leaderboardContainer');
    if (!container) return;

    if (!parties || parties.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted); padding:1rem;">Awaiting first electoral box returns...</div>';
        return;
    }

    let html = '';
    parties.forEach((p, idx) => {
        const pct = p.percentage || 0;
        const rankBadge = idx === 0 ? '<span style="background:gold; color:#000; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:800; margin-left:8px;">LEADING</span>' : '';
        html += `
            <div class="party-stand-card" style="border-top: 3px solid ${p.color};">
                <div class="party-top-row">
                    <div style="display:flex; align-items:center;">
                        <span class="party-badge" style="background:${p.color};">${p.code}</span>
                        ${rankBadge}
                    </div>
                    <div class="party-vote-count">${Number(p.votes).toLocaleString()}</div>
                </div>
                <div class="party-progress-track">
                    <div class="party-progress-fill" style="width: ${pct}%; background:${p.color};"></div>
                </div>
                <div class="party-pct-info">
                    <span>${p.name}</span>
                    <span style="font-weight:700; color:#fff;">${pct}%</span>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderLgaSummary(lgas) {
    const tbody = document.getElementById('lgaSummaryTableBody');
    if (!tbody) return;

    if (!lgas || lgas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No LGA returns aggregated yet</td></tr>';
        return;
    }

    let html = '';
    lgas.forEach(l => {
        html += `
            <tr>
                <td style="font-weight:700;">${l.lga}</td>
                <td><span style="color:#38bdf8; font-weight:700;">${l.reported_pus}</span></td>
                <td>${Number(l.accredited).toLocaleString()}</td>
                <td style="font-weight:700;">${Number(l.valid_votes).toLocaleString()}</td>
                <td style="color:#c084fc; font-weight:700;">${Number(l.adc || 0).toLocaleString()}</td>
                <td style="color:#0284c7; font-weight:700;">${Number(l.apc).toLocaleString()}</td>
                <td style="color:#16a34a; font-weight:700;">${Number(l.pdp).toLocaleString()}</td>
                <td style="color:#dc2626; font-weight:700;">${Number(l.nnpp).toLocaleString()}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function renderLatestFeed(results) {
    const list = document.getElementById('latestFeedList');
    if (!list) return;

    if (!results || results.length === 0) {
        list.innerHTML = '<div style="color:var(--text-muted); padding:1rem;">No recent returns received.</div>';
        return;
    }

    let html = '';
    results.forEach(r => {
        const isFlagged = r.status === 'FLAGGED';
        const badgeClass = isFlagged ? 'badge-status flagged' : 'badge-status verified';
        const borderStyle = isFlagged ? 'border-left: 3px solid #ef4444;' : 'border-left: 3px solid #10b981;';
        
        html += `
            <div style="background: rgba(30, 41, 59, 0.4); border-radius: var(--radius-sm); padding: 0.8rem; margin-bottom: 0.6rem; ${borderStyle}">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.25rem;">
                    <span style="font-weight:700; font-size:0.85rem; color:#fff;">${r.pu_code} - ${r.pu_name}</span>
                    <span class="${badgeClass}">${r.status}</span>
                </div>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:0.4rem;">
                    ${r.lga} LGA • Ward: ${r.ward} • Agent: ${r.agent_name} (${r.agent_party})
                </div>
                <div style="display:flex; gap:0.8rem; font-size:0.8rem; font-weight:600;">
                    <span style="color:#0284c7;">APC: ${r.apc_votes}</span>
                    <span style="color:#16a34a;">PDP: ${r.pdp_votes}</span>
                    <span style="color:#dc2626;">NNPP: ${r.nnpp_votes}</span>
                    <span style="color:var(--text-dim); margin-left:auto;">Total: ${r.total_votes}</span>
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

async function loadBroadcasts() {
    try {
        const res = await fetch('/api/broadcasts');
        const list = await res.json();
        if (list && list.length > 0) {
            const b = list[0];
            document.getElementById('tickerText').textContent = `[${b.priority}] ${b.title}: ${b.content}`;
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------------- RESULTS DATABASE TAB ----------------
async function fetchResultsTable() {
    const lga = document.getElementById('filterLga')?.value || '';
    const status = document.getElementById('filterStatus')?.value || '';
    const search = document.getElementById('filterSearch')?.value || '';

    const params = new URLSearchParams();
    if (lga) params.append('lga', lga);
    if (status) params.append('status', status);
    if (search) params.append('search', search);

    try {
        const res = await fetch(`/api/results?${params.toString()}`);
        const data = await res.json();
        const tbody = document.getElementById('resultsTableBody');
        if (!tbody) return;

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No polling unit submissions found matching filter.</td></tr>';
            return;
        }

        let html = '';
        data.forEach(r => {
            const badgeClass = r.status === 'FLAGGED' ? 'badge-status flagged' : 'badge-status verified';
            const flags = r.flags ? JSON.parse(r.flags) : [];
            const flagNotice = flags.length > 0 ? `<div style="font-size:0.7rem; color:#f87171; margin-top:4px;">⚠️ ${flags.join('; ')}</div>` : '';

            html += `
                <tr>
                    <td style="font-weight:700; color:#38bdf8;">${r.pu_code}</td>
                    <td>
                        <div style="font-weight:600; color:#fff;">${r.pu_name}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted);">${r.lga} > ${r.ward}</div>
                        ${flagNotice}
                    </td>
                    <td>${Number(r.accredited_voters).toLocaleString()}</td>
                    <td><strong>${Number(r.valid_votes).toLocaleString()}</strong></td>
                    <td style="color:#c084fc; font-weight:700;">${r.adc_votes || 0}</td>
                    <td style="color:#0284c7; font-weight:700;">${r.apc_votes}</td>
                    <td style="color:#16a34a; font-weight:700;">${r.pdp_votes}</td>
                    <td style="color:#dc2626; font-weight:700;">${r.nnpp_votes}</td>
                    <td>
                        <div style="font-size:0.8rem; font-weight:600;">${r.agent_name}</div>
                        <div style="font-size:0.7rem; color:var(--text-dim);">${r.agent_phone} <span class="party-badge" style="background:#9333ea; font-size:0.65rem; padding:1px 6px;">ADC Agent</span></div>
                    </td>
                    <td><span class="${badgeClass}">${r.status}</span></td>
                    <td>
                        <button class="btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="viewResultDetail('${encodeURIComponent(JSON.stringify(r))}')">Inspect</button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    } catch (err) {
        console.error("Error loading results table", err);
    }
}

function setupFilterListeners() {
    const lgaFilter = document.getElementById('filterLga');
    const statusFilter = document.getElementById('filterStatus');
    const searchFilter = document.getElementById('filterSearch');

    if (lgaFilter) lgaFilter.addEventListener('change', fetchResultsTable);
    if (statusFilter) statusFilter.addEventListener('change', fetchResultsTable);
    if (searchFilter) {
        searchFilter.addEventListener('input', () => {
            clearTimeout(window.searchTimeout);
            window.searchTimeout = setTimeout(fetchResultsTable, 300);
        });
    }
}

// ---------------- ADMIN: PARTY AGENT DIRECTORY & REGISTRATION ----------------
async function fetchAdminAgents() {
    try {
        const res = await fetch('/api/agents');
        allAgentsList = await res.json();
        const tbody = document.getElementById('adminAgentsTableBody');
        if (!tbody) return;

        if (allAgentsList.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No party agents accredited yet.</td></tr>';
            return;
        }

        let html = '';
        allAgentsList.forEach(ag => {
            html += `
                <tr>
                    <td style="font-weight:700; color:#fff;">${ag.full_name}</td>
                    <td><span class="party-badge" style="background:${getPartyColor(ag.party)}; font-size:0.75rem;">${ag.party}</span></td>
                    <td><code>${ag.phone}</code></td>
                    <td>${ag.lga}</td>
                    <td>${ag.ward}</td>
                    <td style="font-weight:600; color:#38bdf8;">${ag.pu_code}</td>
                    <td>${ag.pu_name}</td>
                    <td>
                        <button class="btn-primary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="selectAgentForBoxResult(${ag.id})">Enter Result</button>
                        <button class="btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem; margin-left:4px; color:#ef4444;" onclick="deleteAgent(${ag.id})">Remove</button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    } catch (e) {
        console.error("Error loading admin agents", e);
    }
}

function getPartyColor(party) {
    const map = {
        'APC': '#0284c7',
        'PDP': '#16a34a',
        'NNPP': '#dc2626',
        'LP': '#ea580c',
        'ADC': '#9333ea',
        'PRP': '#e11d48'
    };
    return map[party] || '#64748b';
}

async function loadAgentsDropdown() {
    try {
        const res = await fetch('/api/agents');
        allAgentsList = await res.json();
        const select = document.getElementById('entryAgentSelect');
        if (!select) return;

        select.innerHTML = '<option value="">-- Choose Accredited ADC Agent --</option>';
        allAgentsList.forEach(ag => {
            const opt = document.createElement('option');
            opt.value = ag.id;
            opt.textContent = `${ag.full_name} [ADC Agent] - PU: ${ag.pu_code} (${ag.lga} LGA)`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error(e);
    }
}

function onAdminSelectAgent() {
    const selId = document.getElementById('entryAgentSelect').value;
    if (!selId) return;
    const agent = allAgentsList.find(a => a.id == selId);
    if (!agent) return;

    fillResultFormWithAgent(agent);
}

function selectAgentForBoxResult(agentId) {
    const agent = allAgentsList.find(a => a.id == agentId);
    if (!agent) return;
    switchTab('admin-results');
    setTimeout(() => {
        document.getElementById('entryAgentSelect').value = agent.id;
        fillResultFormWithAgent(agent);
    }, 100);
}

function fillResultFormWithAgent(agent) {
    document.getElementById('entryAgentName').value = agent.full_name;
    document.getElementById('entryAgentPhone').value = agent.phone;
    document.getElementById('entryAgentParty').value = 'ADC';

    document.getElementById('entryLga').value = agent.lga;
    const wardSelect = document.getElementById('entryWard');
    wardSelect.innerHTML = `<option value="${agent.ward}">${agent.ward}</option>`;
    wardSelect.value = agent.ward;

    document.getElementById('entryPuCode').value = agent.pu_code;
    document.getElementById('entryPuName').value = agent.pu_name;
}

function initAgentRegistrationForm() {
    const form = document.getElementById('registerAgentForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!adminToken) {
            alert("Only authenticated Admins can accredit party agents.");
            return;
        }

        const payload = {
            full_name: document.getElementById('regName').value.trim(),
            phone: document.getElementById('regPhone').value.trim(),
            party: document.getElementById('regParty').value,
            pin: document.getElementById('regPin').value.trim(),
            lga: document.getElementById('regLga').value,
            ward: document.getElementById('regWard').value,
            pu_code: document.getElementById('regPuCode').value.trim(),
            pu_name: document.getElementById('regPuName').value.trim()
        };

        const regAlert = document.getElementById('regAlert');
        regAlert.innerHTML = `<div class="alert-box warning">Registering accredited agent...</div>`;

        try {
            const res = await fetch('/api/admin/agent/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${adminToken}`
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                regAlert.innerHTML = `<div class="alert-box success">${data.message}</div>`;
                form.reset();
                setTimeout(() => {
                    closeModal('registerAgentModal');
                    regAlert.innerHTML = '';
                    fetchAdminAgents();
                    loadAgentsDropdown();
                }, 1200);
            } else {
                regAlert.innerHTML = `<div class="alert-box error">${data.message}</div>`;
            }
        } catch (err) {
            regAlert.innerHTML = `<div class="alert-box error">Server connection error accrediting agent.</div>`;
        }
    });
}

async function deleteAgent(id) {
    if (!adminToken) return;
    if (!confirm("Are you sure you want to remove this accredited party agent?")) return;

    try {
        const res = await fetch('/api/agent/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminToken}`
            },
            body: JSON.stringify({ id })
        });
        const data = await res.json();
        if (data.success) {
            fetchAdminAgents();
            loadAgentsDropdown();
        } else {
            alert(data.message);
        }
    } catch (e) {
        alert("Failed to remove agent.");
    }
}

// ---------------- ADMIN-ONLY RESULT SUBMISSION ----------------
function initResultSubmissionForm() {
    const form = document.getElementById('resultSubmissionForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const alertEl = document.getElementById('submissionAlert');

        if (!adminToken) {
            alertEl.innerHTML = `<div class="alert-box error">Permission Denied: Please log in as an Admin to submit results.</div>`;
            return;
        }

        alertEl.innerHTML = `<div class="alert-box warning">Admin verification & auditing in progress...</div>`;

        const payload = {
            pu_code: document.getElementById('entryPuCode').value.trim(),
            pu_name: document.getElementById('entryPuName').value.trim(),
            lga: document.getElementById('entryLga').value,
            ward: document.getElementById('entryWard').value,
            registered_voters: parseInt(document.getElementById('entryRegVoters').value) || 0,
            accredited_voters: parseInt(document.getElementById('entryAccredited').value) || 0,
            ballots_issued: parseInt(document.getElementById('entryIssued').value) || 0,
            unused_ballots: parseInt(document.getElementById('entryUnused').value) || 0,
            spoiled_ballots: parseInt(document.getElementById('entrySpoiled').value) || 0,
            rejected_ballots: parseInt(document.getElementById('entryRejected').value) || 0,
            apc_votes: parseInt(document.getElementById('voteApc').value) || 0,
            pdp_votes: parseInt(document.getElementById('votePdp').value) || 0,
            nnpp_votes: parseInt(document.getElementById('voteNnpp').value) || 0,
            lp_votes: parseInt(document.getElementById('voteLp').value) || 0,
            adc_votes: parseInt(document.getElementById('voteAdc').value) || 0,
            prp_votes: parseInt(document.getElementById('votePrp').value) || 0,
            other_votes: parseInt(document.getElementById('voteOther').value) || 0,
            agent_name: document.getElementById('entryAgentName').value.trim(),
            agent_phone: document.getElementById('entryAgentPhone').value.trim(),
            agent_party: document.getElementById('entryAgentParty').value,
            incident_report: document.getElementById('entryIncidents').value.trim()
        };

        const photoInput = document.getElementById('entryEc8aPhoto');
        if (photoInput && photoInput.files && photoInput.files[0]) {
            const reader = new FileReader();
            reader.onload = async () => {
                payload.ec8a_photo = reader.result;
                sendAdminResultPayload(payload, alertEl);
            };
            reader.readAsDataURL(photoInput.files[0]);
        } else {
            sendAdminResultPayload(payload, alertEl);
        }
    });
}

async function sendAdminResultPayload(payload, alertEl) {
    try {
        const res = await fetch('/api/results/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminToken}`
            },
            body: JSON.stringify(payload)
        });
        const resp = await res.json();
        if (resp.success) {
            let msg = `✅ ${resp.message}`;
            if (resp.flags && resp.flags.length > 0) {
                msg += `<div style="margin-top:0.5rem; font-weight:700; color:#ef4444;">⚠️ Notice: Form marked as FLAGGED: ${resp.flags.join(', ')}</div>`;
                alertEl.innerHTML = `<div class="alert-box error">${msg}</div>`;
            } else {
                alertEl.innerHTML = `<div class="alert-box success">${msg} Valid: ${resp.valid_votes} | Total Cast: ${resp.total_votes}</div>`;
            }
            loadDashboardData(true);
        } else {
            alertEl.innerHTML = `<div class="alert-box error">Submission Failed: ${resp.message}</div>`;
        }
    } catch (err) {
        alertEl.innerHTML = `<div class="alert-box error">Network error submitting result to situation room.</div>`;
    }
}

function setupFormCalculations() {
    const voteInputs = ['voteApc', 'votePdp', 'voteNnpp', 'voteLp', 'voteAdc', 'votePrp', 'voteOther'];
    voteInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', calculateVoteTotals);
        }
    });

    const rej = document.getElementById('entryRejected');
    if (rej) rej.addEventListener('input', calculateVoteTotals);

    const acc = document.getElementById('entryAccredited');
    if (acc) acc.addEventListener('input', calculateVoteTotals);
}

function calculateVoteTotals() {
    const voteInputs = ['voteApc', 'votePdp', 'voteNnpp', 'voteLp', 'voteAdc', 'votePrp', 'voteOther'];
    let valid = 0;
    voteInputs.forEach(id => {
        const val = parseInt(document.getElementById(id)?.value) || 0;
        valid += val;
    });

    const rejected = parseInt(document.getElementById('entryRejected')?.value) || 0;
    const total = valid + rejected;

    const calcValid = document.getElementById('calcValidVotes');
    const calcTotal = document.getElementById('calcTotalVotes');
    if (calcValid) calcValid.textContent = valid.toLocaleString();
    if (calcTotal) calcTotal.textContent = total.toLocaleString();

    const acc = parseInt(document.getElementById('entryAccredited')?.value) || 0;
    const warnEl = document.getElementById('calcWarning');
    if (warnEl) {
        if (acc > 0 && total > acc) {
            warnEl.style.display = 'block';
            warnEl.textContent = `⚠️ Over-Voting Alert: Total votes (${total}) exceeds accredited voters (${acc})!`;
        } else {
            warnEl.style.display = 'none';
        }
    }
}

// ---------------- INCIDENT REPORTING ----------------
async function fetchIncidents() {
    try {
        const res = await fetch('/api/incidents');
        const list = await res.json();
        const container = document.getElementById('incidentCardsList');
        if (!container) return;

        if (list.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted); padding:1.5rem;">No active security or logistics incidents reported.</div>';
            return;
        }

        let html = '';
        list.forEach(inc => {
            const sevColor = inc.severity === 'CRITICAL' ? '#ef4444' : (inc.severity === 'HIGH' ? '#f97316' : '#f59e0b');
            html += `
                <div style="background:rgba(30, 41, 59, 0.6); border:1px solid var(--border-color); border-left:4px solid ${sevColor}; border-radius:var(--radius-md); padding:1rem; margin-bottom:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <span style="font-weight:700; color:#fff; font-size:0.95rem;">${inc.incident_type} - [${inc.pu_code}] ${inc.lga} LGA</span>
                        <span style="background:${sevColor}22; color:${sevColor}; border:1px solid ${sevColor}55; padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:700;">${inc.severity}</span>
                    </div>
                    <p style="color:var(--text-main); font-size:0.875rem; margin-bottom:0.5rem;">${inc.description}</p>
                    <div style="font-size:0.75rem; color:var(--text-muted); display:flex; justify-content:space-between;">
                        <span>Reported by: ${inc.agent_name} (${inc.agent_phone})</span>
                        <span>${inc.reported_at}</span>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error(e);
    }
}

async function submitIncidentForm(e) {
    e.preventDefault();
    const payload = {
        lga: document.getElementById('incLga').value,
        ward: document.getElementById('incWard').value,
        pu_code: document.getElementById('incPuCode').value,
        agent_name: document.getElementById('incAgentName').value,
        agent_phone: document.getElementById('incAgentPhone').value,
        incident_type: document.getElementById('incType').value,
        severity: document.getElementById('incSeverity').value,
        description: document.getElementById('incDesc').value
    };

    try {
        const res = await fetch('/api/incidents/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resp = await res.json();
        if (resp.success) {
            alert("Distress report logged into Situation Room Triage.");
            closeModal('incidentModal');
            fetchIncidents();
        }
    } catch (e) {
        alert("Failed to send incident report.");
    }
}

// ---------------- RESULT DETAIL MODAL ----------------
function viewResultDetail(jsonStr) {
    const r = JSON.parse(decodeURIComponent(jsonStr));
    const modal = document.getElementById('detailModal');
    const content = document.getElementById('detailModalBody');

    const flags = r.flags ? JSON.parse(r.flags) : [];
    let flagAlert = '';
    if (flags.length > 0) {
        flagAlert = `<div class="alert-box error" style="margin-bottom:1rem;">
            <strong>Discrepancies Detected:</strong>
            <ul style="margin-left:1.25rem; margin-top:0.25rem;">
                ${flags.map(f => `<li>${f}</li>`).join('')}
            </ul>
        </div>`;
    }

    content.innerHTML = `
        <div style="margin-bottom:1rem;">
            <h3 style="color:#fff; font-size:1.25rem;">Polling Unit: ${r.pu_code}</h3>
            <p style="color:var(--text-muted); font-size:0.85rem;">${r.pu_name} • ${r.ward} Ward, ${r.lga} LGA</p>
        </div>
        ${flagAlert}
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-bottom:1.25rem; background:rgba(30, 41, 59, 0.4); padding:1rem; border-radius:var(--radius-sm);">
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Registered Voters:</span> <strong style="color:#fff;">${r.registered_voters}</strong></div>
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Accredited Voters:</span> <strong style="color:#fff;">${r.accredited_voters}</strong></div>
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Ballots Issued:</span> <strong style="color:#fff;">${r.ballots_issued}</strong></div>
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Rejected Ballots:</span> <strong style="color:#ef4444;">${r.rejected_ballots}</strong></div>
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Valid Votes:</span> <strong style="color:#10b981;">${r.valid_votes}</strong></div>
            <div><span style="color:var(--text-muted); font-size:0.8rem;">Total Votes Cast:</span> <strong style="color:#fff;">${r.total_votes}</strong></div>
        </div>

        <h4 style="color:#fff; margin-bottom:0.5rem; font-size:0.95rem;">Party Scorecard</h4>
        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:0.5rem; margin-bottom:1.25rem;">
            <div style="background:rgba(2, 132, 199, 0.15); border:1px solid #0284c7; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#38bdf8;">APC</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.apc_votes}</div>
            </div>
            <div style="background:rgba(22, 163, 74, 0.15); border:1px solid #16a34a; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#4ade80;">PDP</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.pdp_votes}</div>
            </div>
            <div style="background:rgba(220, 38, 38, 0.15); border:1px solid #dc2626; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#f87171;">NNPP</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.nnpp_votes}</div>
            </div>
            <div style="background:rgba(234, 88, 12, 0.15); border:1px solid #ea580c; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#fb923c;">LP</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.lp_votes}</div>
            </div>
            <div style="background:rgba(147, 51, 234, 0.15); border:1px solid #9333ea; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#c084fc;">ADC</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.adc_votes}</div>
            </div>
            <div style="background:rgba(225, 29, 72, 0.15); border:1px solid #e11d48; padding:0.5rem; border-radius:var(--radius-sm); text-align:center;">
                <div style="font-weight:700; color:#fb7185;">PRP</div>
                <div style="font-size:1.1rem; font-weight:800; color:#fff;">${r.prp_votes}</div>
            </div>
        </div>

        <div style="font-size:0.85rem; color:var(--text-muted); border-top:1px solid var(--border-color); padding-top:0.75rem;">
            <div><strong>Submitting Agent:</strong> ${r.agent_name} (${r.agent_phone}) - Party: ${r.agent_party}</div>
            <div><strong>Authenticated by:</strong> Admin (${r.submitted_by_admin || 'System'})</div>
            <div><strong>Submission Time:</strong> ${r.submitted_at}</div>
            ${r.incident_report ? `<div style="margin-top:0.5rem;"><strong>Admin/Agent Remarks:</strong> ${r.incident_report}</div>` : ''}
        </div>
    `;

    modal.classList.add('show');
}

function openModal(id) {
    document.getElementById(id).classList.add('show');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('show');
}

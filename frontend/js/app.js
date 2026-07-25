let platformModeReady = false;
// Onelap2Strava Web App Frontend Logic

const API_BASE = "";
let currentUser = null;
let currentAuthMode = "login";
let currentStravaMode = "cookie";

// Globally bind setStravaMode to window
window.setStravaMode = function(mode) {
    currentStravaMode = mode;
    
    // Reset all tabs
    const btnIds = ['strava-mode-btn-platform', 'strava-mode-btn-cookie', 'strava-mode-btn-api'];
    btnIds.forEach(id => {
        const btn = document.getElementById(id);
        if(!btn) return;
        btn.className = 'px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 text-slate-400 hover:text-white w-full sm:w-auto';
    });

    // Active tab style
    const activeBtn = document.getElementById(`strava-mode-btn-${mode}`);
    if(activeBtn) {
        activeBtn.className = 'px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 bg-orange-500/20 text-orange-400 border border-orange-500/40 w-full sm:w-auto';
    }

    // Toggle Sections
    document.getElementById('strava-section-platform').classList.add('hidden');
    document.getElementById('strava-section-cookie').classList.add('hidden');
    document.getElementById('strava-section-api').classList.add('hidden');

    if (mode === 'platform') {
        document.getElementById('strava-section-platform').classList.remove('hidden');
    } else if (mode === 'cookie') {
        document.getElementById('strava-section-cookie').classList.remove('hidden');
    } else {
        document.getElementById('strava-section-api').classList.remove('hidden');
    }
}

async function autoExchangeRefreshToken() {
    if (!localStorage.getItem("token")) {
        openAuthModal();
        return;
    }

    const client_id = document.getElementById("cfg-strava-client-id").value;
    const client_secret = document.getElementById("cfg-strava-client-secret").value;
    const code = document.getElementById("api-auth-code-input").value;

    if (!client_id || !client_secret || !code) {
        showToast("请填入 Client ID、Client Secret 及 第一步授权获取的 Code", "error");
        return;
    }

    showToast("正在通过后台向 Strava 换取 Refresh Token...", "info");

    try {
        const res = await fetch(`${API_BASE}/api/config/exchange-strava-token`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ client_id, client_secret, code })
        });
        if (res.ok) {
            const data = await res.json();
            document.getElementById("cfg-strava-refresh-token").value = data.refresh_token;
            showToast(data.message || "生成成功！", "success");
        } else {
            const err = await res.json();
            showToast(err.detail || "换取 Refresh Token 失败", "error");
        }
    } catch (e) {
        showToast("换取请求发送错误", "error");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    switchTab("dashboard");
});

// Toast Notification System
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-enter p-4 rounded-xl border text-xs font-medium shadow-xl flex items-center gap-3 pointer-events-auto transition-all ${
        type === "success" 
            ? "bg-slate-900 border-emerald-500/30 text-emerald-400" 
            : type === "error" 
            ? "bg-slate-900 border-red-500/30 text-red-400" 
            : "bg-slate-900 border-orange-500/30 text-orange-400"
    }`;

    const icon = type === "success" ? "fa-circle-check" : type === "error" ? "fa-circle-exclamation" : "fa-info-circle";
    toast.innerHTML = `<i class="fa-solid ${icon} text-base shrink-0"></i><span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".nav-tab").forEach(el => el.classList.remove("active"));

    const targetTab = document.getElementById(`tab-${tabId}`);
    const targetBtn = document.getElementById(`nav-${tabId}-btn`);

    if (targetTab) targetTab.classList.remove("hidden");
    if (targetBtn) targetBtn.classList.add("active");

    if (tabId === "dashboard") loadDashboardData();
    if (tabId === "config") loadUserConfig();
    if (tabId === "logs") loadActivityLogs();
}

// Authentication Check
async function checkAuth() {
    const token = localStorage.getItem("token");
    const headerName = document.getElementById("user-display-name");
    const authBtnText = document.getElementById("auth-btn-text");

    if (!token) {
        currentUser = null;
        if (headerName) headerName.innerText = "未登录";
        if (authBtnText) authBtnText.innerText = "登录 / 注册";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            if (headerName) headerName.innerText = `用户: ${currentUser.username}`;
            if (authBtnText) authBtnText.innerText = "退出登录";
        } else {
            logout();
        }
    } catch (e) {
        console.error("Auth check error:", e);
    }
}

function openAuthModal() {
    if (currentUser) {
        logout();
        return;
    }
    document.getElementById("auth-modal").classList.remove("hidden");
}

function closeAuthModal() {
    document.getElementById("auth-modal").classList.add("hidden");
}

function toggleAuthMode() {
    currentAuthMode = currentAuthMode === "login" ? "register" : "login";
    const title = document.getElementById("auth-modal-title");
    const subtitle = document.getElementById("auth-modal-subtitle");
    const submitBtn = document.getElementById("auth-submit-btn");
    const emailGroup = document.getElementById("auth-email-group");
    const toggleBtn = document.getElementById("auth-toggle-btn");
    const toggleText = document.getElementById("auth-toggle-text");

    if (currentAuthMode === "register") {
        title.innerText = "创建新账号";
        subtitle.innerText = "注册后开启专属多端骑行数据自动同步";
        submitBtn.innerText = "注册账号";
        emailGroup.classList.remove("hidden");
        toggleBtn.innerText = "直接登录";
        toggleText.innerText = "已有账号？";
    } else {
        title.innerText = "用户登录";
        subtitle.innerText = "登录 Onelap2Strava 平台以管理您的数据同步";
        submitBtn.innerText = "登录";
        emailGroup.classList.add("hidden");
        toggleBtn.innerText = "立即注册";
        toggleText.innerText = "还没有账号？";
    }
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    const username = document.getElementById("auth-username").value;
    const password = document.getElementById("auth-password").value;
    const email = document.getElementById("auth-email").value;

    if (currentAuthMode === "register") {
        try {
            const res = await fetch(`${API_BASE}/api/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password, email })
            });
            if (res.ok) {
                showToast("注册成功！请登录", "success");
                toggleAuthMode();
            } else {
                const err = await res.json();
                showToast(err.detail || "注册失败", "error");
            }
        } catch (e) {
            showToast("请求失败，请检查网络", "error");
        }
    } else {
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            const res = await fetch(`${API_BASE}/api/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem("token", data.access_token);
                showToast("登录成功！", "success");
                closeAuthModal();
                checkAuth();
                loadDashboardData();
            } else {
                const err = await res.json();
                showToast(err.detail || "登录失败，账号或密码错误", "error");
            }
        } catch (e) {
            showToast("登录请求失败", "error");
        }
    }
}

function logout() {
    localStorage.removeItem("token");
    currentUser = null;
    checkAuth();
    showToast("已退出登录", "info");
}

function getAuthHeaders() {
    const token = localStorage.getItem("token");
    return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

async function loadDashboardData() {
    if (!localStorage.getItem("token")) return;

    try {
        const res = await fetch(`${API_BASE}/api/sync/summary`, { headers: getAuthHeaders() });
        if (res.ok) {
            const summary = await res.json();
            document.getElementById("stat-total-synced").innerText = summary.total_synced || 0;
            
            const cookieBadge = document.getElementById("stat-cookie-status-badge");
            const cookieIcon = document.getElementById("stat-cookie-icon");
            if (summary.cookie_status === "valid") {
                cookieBadge.innerText = "有效 (Valid)";
                cookieBadge.className = "text-xs font-bold px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                cookieIcon.className = "w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold";
            } else if (summary.cookie_status === "expired") {
                cookieBadge.innerText = "已失效 (Expired)";
                cookieBadge.className = "text-xs font-bold px-2.5 py-1 rounded-md bg-red-500/10 text-red-400 border border-red-500/20";
                cookieIcon.className = "w-10 h-10 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-center font-bold";
            } else {
                cookieBadge.innerText = "未测试/自定义模式";
                cookieBadge.className = "text-xs font-bold px-2.5 py-1 rounded-md bg-slate-800 text-slate-200 border border-slate-700";
            }

            const autoSyncSpan = document.getElementById("stat-auto-sync");
            if (autoSyncSpan) {
                if (summary.auto_sync_enabled) {
                    autoSyncSpan.innerText = `已开启 (${summary.sync_interval_hours || 6}h)`;
                    autoSyncSpan.className = "text-base font-extrabold text-emerald-400";
                } else {
                    autoSyncSpan.innerText = "已禁用 (Disabled)";
                    autoSyncSpan.className = "text-base font-extrabold text-slate-400";
                }
            }

            document.getElementById("stat-last-sync").innerText = summary.last_sync_at ? new Date(summary.last_sync_at).toLocaleString() : "从未执行";
        }

        const actRes = await fetch(`${API_BASE}/api/logs/activities?limit=5`, { headers: getAuthHeaders() });
        if (actRes.ok) {
            const activities = await actRes.json();
            const tbody = document.getElementById("dashboard-recent-tbody");
            if (activities.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-slate-400 font-medium">暂无活动记录，请点击“立即手动同步”</td></tr>`;
            } else {
                tbody.innerHTML = activities.map(a => `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                        <td class="py-3 px-4 font-medium text-white">${a.title}</td>
                        <td class="py-3 px-4 font-mono text-slate-400">${a.onelap_activity_id}</td>
                        <td class="py-3 px-4 font-mono text-orange-400">${a.strava_activity_id || '--'}</td>
                        <td class="py-3 px-4">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                                a.sync_status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                a.sync_status === 'FAILED' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-slate-800 text-slate-400'
                            }">${a.sync_status}</span>
                        </td>
                        <td class="py-3 px-4 text-slate-300 text-[11px]">${a.synced_at ? new Date(a.synced_at).toLocaleString() : '--'}</td>
                    </tr>
                `).join("");
            }
        }
    } catch (e) {
        console.error("Error loading dashboard summary:", e);
    }
}

async function triggerManualSync() {
    if (!localStorage.getItem("token")) {
        openAuthModal();
        return;
    }

    const btn = document.getElementById("trigger-sync-btn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i><span>同步处理中...</span>`;

    try {
        const res = await fetch(`${API_BASE}/api/sync/trigger`, {
            method: "POST",
            headers: getAuthHeaders()
        });
        if (res.ok) {
            showToast("同步任务已在后台启动！请稍后刷新查看结果。", "success");
            setTimeout(loadDashboardData, 3000);
        } else {
            const err = await res.json();
            showToast(err.detail || "启动同步失败", "error");
        }
    } catch (e) {
        showToast("请求失败，请检查网络", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-rotate"></i><span>立即手动同步</span>`;
    }
}

async function loadUserConfig() {
    if (!localStorage.getItem("token")) return;

    try {
        const res = await fetch(`${API_BASE}/api/config`, { headers: getAuthHeaders() });
        if (res.ok) {
            const cfg = await res.json();
            if (cfg.onelap_username) document.getElementById("cfg-onelap-username").value = cfg.onelap_username;
            document.getElementById("cfg-auto-sync-toggle").checked = cfg.auto_sync_enabled;
            document.getElementById("cfg-sync-interval").value = cfg.sync_interval_hours || 6;
            
            if (cfg.strava_client_id) {
                document.getElementById("cfg-strava-client-id").value = cfg.strava_client_id;
            }

            if (cfg.strava_mode) {
                window.setStravaMode(cfg.strava_mode);
            }

            const athleteSpan = document.getElementById("stat-athlete-name");
            if (athleteSpan && cfg.strava_athlete_name) {
                athleteSpan.innerText = cfg.strava_athlete_name;
            }
        }
    } catch (e) {
        console.error("Error loading config:", e);
    }
}

async function saveUserConfig(silent = false) {
    if (!localStorage.getItem("token")) {
        openAuthModal();
        return;
    }

    const onelap_username = document.getElementById("cfg-onelap-username").value;
    const onelap_password = document.getElementById("cfg-onelap-password").value;
    const strava_cookie = document.getElementById("cfg-strava-cookie").value;
    const strava_client_id = document.getElementById("cfg-strava-client-id").value;
    const strava_client_secret = document.getElementById("cfg-strava-client-secret").value;
    const strava_refresh_token = document.getElementById("cfg-strava-refresh-token").value;
    const auto_sync_enabled = document.getElementById("cfg-auto-sync-toggle").checked;
    const sync_interval_hours = parseInt(document.getElementById("cfg-sync-interval").value);

    const payload = {
        onelap_username,
        strava_mode: currentStravaMode,
        auto_sync_enabled,
        sync_interval_hours
    };

    if (onelap_password) payload.onelap_password = onelap_password;
    if (strava_cookie) payload.strava_cookie = strava_cookie;
    if (strava_client_id) payload.strava_client_id = strava_client_id;
    if (strava_client_secret) payload.strava_client_secret = strava_client_secret;
    if (strava_refresh_token) payload.strava_refresh_token = strava_refresh_token;

    try {
        const res = await fetch(`${API_BASE}/api/config`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            if (!silent) showToast("账号与 Strava 配置已成功保存！", "success");
            if (silent) return true;
            loadUserConfig();
            loadDashboardData();
        } else {
            if (!silent) showToast("保存失败，请检查填写内容", "error");
            if (silent) return false;
        }
    } catch (e) {
        if (!silent) showToast("保存配置出错", "error");
        if (silent) return false;
    }
}

async function testOnelapCredentials() {
    if (!localStorage.getItem("token")) {
        openAuthModal();
        return;
    }
    showToast("正在测试顽鹿账号连接...", "info");
    const saved = await saveUserConfig(true);
    if (!saved) return;
    try {
        const res = await fetch(`${API_BASE}/api/config/test-onelap`, {
            method: "POST",
            headers: getAuthHeaders()
        });
        if (res.ok) {
            const data = await res.json();
            showToast(data.message || "顽鹿登录测试成功！", "success");
        } else {
            const err = await res.json();
            showToast(err.detail || "顽鹿登录测试失败", "error");
        }
    } catch (e) {
        showToast("测试请求错误", "error");
    }
}

async function testStravaCredential() {
    if (!localStorage.getItem("token")) {
        openAuthModal();
        return;
    }

    if (currentStravaMode === "cookie") {
        showToast("正在校验 Strava Session Cookie...", "info");
        const savedStrava = await saveUserConfig(true);
        if (!savedStrava) return;
        try {
            const res = await fetch(`${API_BASE}/api/config/test-strava`, {
                method: "POST",
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                showToast(data.message || "Strava Cookie 有效！", "success");
                loadDashboardData();
            } else {
                const err = await res.json();
                showToast(err.detail || "Strava Cookie 无效或已过期", "error");
            }
        } catch (e) {
            showToast("校验请求失败", "error");
        }
    } else {
        showToast("已设为 Strava API 模式，保存后可在手动同步时进行测试。", "info");
    }
}

async function loadActivityLogs() {
    if (!localStorage.getItem("token")) return;

    const statusFilter = document.getElementById("logs-status-filter").value;
    const url = `${API_BASE}/api/logs/activities?limit=50${statusFilter ? `&status=${statusFilter}` : ""}`;

    try {
        const res = await fetch(url, { headers: getAuthHeaders() });
        if (res.ok) {
            const activities = await res.json();
            const tbody = document.getElementById("logs-activity-tbody");
            if (activities.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-500">暂无相关同步记录</td></tr>`;
            } else {
                tbody.innerHTML = activities.map(a => `
                    <tr class="hover:bg-slate-800/40 transition-colors">
                        <td class="py-3 px-4 font-mono text-slate-400">${a.onelap_activity_id}</td>
                        <td class="py-3 px-4 font-medium text-white">${a.title}</td>
                        <td class="py-3 px-4 font-mono text-orange-400">${a.strava_activity_id || '--'}</td>
                        <td class="py-3 px-4">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                                a.sync_status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                a.sync_status === 'FAILED' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-slate-800 text-slate-400'
                            }">${a.sync_status}</span>
                        </td>
                        <td class="py-3 px-4 text-red-400/90 text-[11px] max-w-xs truncate">${a.error_message || '--'}</td>
                        <td class="py-3 px-4 text-slate-300 text-[11px]">${a.synced_at ? new Date(a.synced_at).toLocaleString() : '--'}</td>
                    </tr>
                `).join("");
            }
        }

        const msgRes = await fetch(`${API_BASE}/api/logs/messages?limit=50`, { headers: getAuthHeaders() });
        if (msgRes.ok) {
            const msgs = await msgRes.json();
            const consoleBox = document.getElementById("system-console-logs");
            if (msgs.length === 0) {
                consoleBox.innerHTML = `<div class="text-slate-400">[System] Console log ready...</div>`;
            } else {
                consoleBox.innerHTML = msgs.map(m => `
                    <div>
                        <span class="text-slate-400">[${new Date(m.timestamp).toLocaleTimeString()}]</span>
                        <span class="${m.level === 'ERROR' ? 'text-red-400 font-bold' : m.level === 'WARNING' ? 'text-amber-400' : 'text-emerald-400'}">[${m.level}]</span>
                        <span class="text-slate-300">${m.message}</span>
                    </div>
                `).join("");
            }
        }
    } catch (e) {
        console.error("Error loading activity logs:", e);
    }
}

function refreshLogs() {
    loadActivityLogs();
    showToast("日志已更新", "info");
}

window.startPlatformOAuth = function() {
    // Assuming backend endpoint /api/config gives us the client_id, but we can't easily get it securely unless we expose it.
    // Instead of frontend constructing the OAuth URL, we can ask backend to construct it, OR just redirect directly to backend which issues a 302 redirect.
    // Let's just fetch the client_id from a new endpoint, or we can hardcode the URL if we expose the client_id in config fetch.
    showToast("请求授权地址中...", "info");
    fetch('/api/config/oauth-url', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    }).then(res => res.json()).then(data => {
        if (data.url) {
            window.location.href = data.url;
        } else {
            showToast("平台未正确配置一键授权", "error");
        }
    }).catch(() => showToast("请求失败", "error"));
}

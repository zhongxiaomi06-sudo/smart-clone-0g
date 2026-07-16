/* ============================================================
   智慧分身 · 前端交互层
   保持原生架构 · GSAP 动效 · 午后工作室设计系统
   音效:WebAudio 实时合成,零音频资产
   ============================================================ */

const API_BASE = "/api/v1";
const APP_VERSION = "v1.4";
const APP_BUILT = "2026-07";

const state = {
  skills: [],
  tools: [],
};

const titles = {
  chat: { title: "Chat 中枢", sub: "本地优先 · 记忆检索 · Skill 调度", index: "之壹" },
  recordings: { title: "录音采集", sub: "原始音频仅本地 · 自动转写与提炼", index: "之贰" },
  memories: { title: "记忆仓库", sub: "脱敏结构化卡片 · 按时间倒序", index: "之叁" },
  story: { title: "今日故事", sub: "真实锚点 + 文学虚构 · 基于今日记忆", index: "之肆" },
  skills: { title: "Skill Registry", sub: "场景能力配置接入 · 不写进核心代码", index: "之伍" },
  tools: { title: "MCP 工具", sub: "默认关闭 · 需权限与审计策略", index: "之陆" },
  trust: { title: "授权与凭证", sub: "Token 授权 · 本地哈希凭证", index: "之柒" },
  settings: { title: "设置", sub: "隐私策略 · 模型配置 · 数据管理", index: "之捌" },
  audit: { title: "审计日志", sub: "记忆 · Skill · 工具 · 权限 · 凭证", index: "之玖" },
};

/* ===== GSAP 动效模块 ===== */
const gsapAnim = {
  reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  hasGsap: typeof gsap !== "undefined",

  panelTransition(fromPanel, toPanel) {
    if (!toPanel) return;
    if (this._panelTl) { this._panelTl.kill(); this._panelTl = null; }
    if (!this.hasGsap || this.reducedMotion) {
      if (fromPanel && fromPanel !== toPanel) fromPanel.classList.remove("is-active");
      toPanel.classList.add("is-active");
      return;
    }
    document.querySelectorAll(".tab-panel").forEach((p) => {
      if (p !== toPanel && p !== fromPanel) {
        p.classList.remove("is-active");
        gsap.set(p, { opacity: 1, y: 0 });
      }
    });
    const tl = gsap.timeline();
    if (fromPanel && fromPanel !== toPanel) {
      tl.to(fromPanel, { opacity: 0, y: -8, duration: 0.25, ease: "power2.out" });
      tl.add(() => {
        fromPanel.classList.remove("is-active");
        gsap.set(fromPanel, { opacity: 1, y: 0 });
        toPanel.classList.add("is-active");
      });
      tl.fromTo(toPanel, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
    } else {
      toPanel.classList.add("is-active");
      tl.fromTo(toPanel, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
    }
    this._panelTl = tl;
  },

  staggerItems(container, selector) {
    if (!container) return;
    const items = container.querySelectorAll(selector);
    if (!items.length) return;
    if (!this.hasGsap || this.reducedMotion) return;
    gsap.from(items, { opacity: 0, y: 14, duration: 0.38, stagger: 0.05, ease: "power2.out" });
  },

  buttonHover(elements) {
    if (!this.hasGsap || this.reducedMotion || !elements) return;
    elements.forEach((el) => {
      el.addEventListener("mouseenter", () => gsap.to(el, { scale: 1.02, duration: 0.18, ease: "power2.out" }));
      el.addEventListener("mouseleave", () => gsap.to(el, { scale: 1, duration: 0.18, ease: "power2.out" }));
      el.addEventListener("mousedown", () => gsap.to(el, { scale: 0.97, duration: 0.08 }));
      el.addEventListener("mouseup", () => gsap.to(el, { scale: 1.02, duration: 0.18, ease: "power2.out" }));
    });
  },

  navHover(elements) {
    if (!this.hasGsap || this.reducedMotion || !elements) return;
    elements.forEach((el) => {
      el.addEventListener("mouseenter", () => gsap.to(el, { x: 2, duration: 0.18, ease: "power2.out" }));
      el.addEventListener("mouseleave", () => gsap.to(el, { x: 0, duration: 0.18, ease: "power2.out" }));
    });
  },

  navActivate(element) {
    if (!this.hasGsap || this.reducedMotion || !element) return;
    gsap.fromTo(element, { scale: 0.97 }, { scale: 1, duration: 0.3, ease: "back.out(1.5)" });
  },

  showToast(element) {
    if (!this.hasGsap || this.reducedMotion) {
      element.style.opacity = 1;
      element.style.transform = "translateX(-50%) translateY(0)";
      return;
    }
    gsap.fromTo(element, { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "back.out(1.5)" });
  },

  hideToast(element) {
    if (!this.hasGsap || this.reducedMotion) {
      element.style.opacity = 0;
      element.style.transform = "translateX(-50%) translateY(20px)";
      return;
    }
    gsap.to(element, { y: 20, opacity: 0, duration: 0.22, ease: "power2.in" });
  },

  formSubmitFeedback(button) {
    if (!this.hasGsap || this.reducedMotion || !button) return;
    const tl = gsap.timeline();
    tl.to(button, { scale: 0.96, duration: 0.08 });
    tl.to(button, { scale: 1, duration: 0.2, ease: "back.out(2)" });
  },

  resultFadeIn(element) {
    if (!element) return;
    if (!this.hasGsap || this.reducedMotion) return;
    gsap.fromTo(element, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.32, ease: "power2.out" });
  },

  errorShake(element) {
    if (!element) return;
    if (!this.hasGsap || this.reducedMotion) return;
    gsap.fromTo(element, { x: 0 }, { keyframes: [{ x: -4 }, { x: 4 }, { x: -2 }, { x: 2 }, { x: 0 }], duration: 0.35, ease: "power2.inOut" });
  },
};

const elements = {};
const recorder = {
  mediaRecorder: null,
  chunks: [],
  blob: null,
  stream: null,
  timerId: null,
  startedAt: 0,
};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  titles.chat.sub = `${greeting()}，先检索记忆，再按需调用 Skill`;
  elements.viewSub.textContent = titles.chat.sub;
  bindNavigation();
  bindForms();
  restoreApiKey();
  initHoverInteractions();
  SoundFX.init();
  ThemeStore.init();
  Sunlight.init();
  CursorDot.init();
  StatusLine.init();
  CmdK.init();
  DebugPanel.init();
  Heatmap.init();
  refreshAll();
});

function cacheElements() {
  elements.toast = document.querySelector("#toast");
  elements.healthStatus = document.querySelector("#health-status");
  elements.requestStatus = document.querySelector("#request-status");
  elements.viewTitle = document.querySelector("#view-title");
  elements.viewSub = document.querySelector("#view-sub");
  elements.viewIndex = document.querySelector("#view-index");
  elements.apiKey = document.querySelector("#api-key");
  elements.chatSkill = document.querySelector("#chat-skill");
  elements.recordToggle = document.querySelector("#record-toggle");
  elements.recordUpload = document.querySelector("#record-upload");
  elements.recordStatus = document.querySelector("#record-status");
  elements.recordTimer = document.querySelector("#record-timer");
  elements.recordPreview = document.querySelector("#record-preview");
  elements.recorderHint = document.querySelector("#recorder-hint");
  elements.recorderBox = document.querySelector("#recorder-box");
  elements.recorderWaveform = document.querySelector("#recorder-waveform");
  elements.recBtnLabel = document.querySelector("#rec-btn-label");
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
}

/* 切换页签:导航点击与 ⌘K 共用 */
function activateTab(tab) {
  const button = document.querySelector(`.nav-item[data-tab="${tab}"]`);
  const currentPanel = document.querySelector(".tab-panel.is-active");
  const targetPanel = document.querySelector(`#tab-${tab}`);
  if (!button || !targetPanel || currentPanel === targetPanel) return;

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("is-active", item === button);
  });

  const info = titles[tab] || { title: "智慧分身", sub: "", index: "—" };
  elements.viewTitle.textContent = info.title;
  elements.viewSub.textContent = info.sub;
  elements.viewIndex.textContent = info.index;

  SoundFX.play("swish"); /* 页面转化 · 翻纸声 */
  gsapAnim.navActivate(button);
  gsapAnim.panelTransition(currentPanel, targetPanel);

  if (tab === "audit") loadAudit();
  if (tab === "recordings") loadRecordings();
  if (tab === "memories") Heatmap.refresh();
}

/* 时间感知问候 */
function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "夜深了";
  if (h < 9) return "早上好";
  if (h < 12) return "上午好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  if (h < 23) return "晚上好";
  return "夜深了";
}

function initHoverInteractions() {
  gsapAnim.buttonHover(document.querySelectorAll(".btn"));
  gsapAnim.navHover(document.querySelectorAll(".nav-item"));
}

function bindForms() {
  document.querySelector("#save-api-key").addEventListener("click", () => {
    localStorage.setItem("smart-avatar-api-key", elements.apiKey.value.trim());
    showToast("API Key 已保存到当前浏览器。");
  });

  document.querySelector("#chat-form").addEventListener("submit", submitChat);
  document.querySelector("#memory-form").addEventListener("submit", submitMemory);
  document.querySelector("#permission-form").addEventListener("submit", submitPermission);
  document.querySelector("#credential-form").addEventListener("submit", submitCredential);

  if (elements.recordToggle) elements.recordToggle.addEventListener("click", toggleRecording);
  if (elements.recordUpload) elements.recordUpload.addEventListener("click", uploadCapturedRecording);

  const uploadForm = document.querySelector("#recording-upload-form");
  if (uploadForm) uploadForm.addEventListener("submit", submitRecordingFile);

  const storyForm = document.querySelector("#story-form");
  if (storyForm) storyForm.addEventListener("submit", submitStory);

  const extractForm = document.querySelector("#memory-extract-form");
  if (extractForm) extractForm.addEventListener("submit", submitExtract);

  const clearBtn = document.querySelector("#clear-memories");
  if (clearBtn) clearBtn.addEventListener("click", clearAllMemories);
}

function restoreApiKey() {
  elements.apiKey.value = localStorage.getItem("smart-avatar-api-key") || "";
}

async function refreshAll() {
  await Promise.allSettled([
    loadHealth(),
    loadSkills(),
    loadTools(),
    loadMemories(),
    loadRecordings(),
    loadCredentials(),
    loadAudit(),
    loadConfig(),
  ]);
}

/* ===== API ===== */
const stats = { requests: 0, lastRequestId: "", healthMs: null, startedAt: Date.now() };

async function apiFetch(path, options = {}) {
  setRequestStatus("请求中");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  // API Key（可选）
  const apiKey = elements.apiKey.value.trim();
  if (apiKey) headers["x-api-key"] = apiKey;

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  const requestId = response.headers.get("x-request-id");
  stats.requests += 1;
  if (requestId) stats.lastRequestId = requestId.slice(0, 8);
  setRequestStatus(requestId ? `请求 ${requestId.slice(0, 8)}` : "完成");
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = data?.error?.message || `请求失败：${response.status}`;
    throw new Error(message);
  }
  return data;
}

async function loadHealth() {
  try {
    const t0 = performance.now();
    const response = await fetch("/health");
    const data = await response.json();
    stats.healthMs = Math.round(performance.now() - t0);
    const ok = data.status === "ok";
    elements.healthStatus.textContent = ok ? "服务正常" : "服务异常";
    elements.healthStatus.dataset.state = ok ? "ok" : "error";
  } catch (error) {
    elements.healthStatus.textContent = "服务异常";
    elements.healthStatus.dataset.state = "error";
  }
}

async function loadConfig() {
  try {
    const cfg = await apiFetch("/config", { method: "GET" });
    setFieldValue("#model-provider", cfg.model?.provider || "—");
    setFieldValue("#model-default", cfg.model?.default_model || "—");
    setFieldValue("#transcribe-provider", cfg.transcription?.provider || "—");
    setFieldValue("#privacy-skill-confirm", cfg.privacy?.require_skill_confirmation ? "是" : "否");
    setFieldValue("#privacy-raw-memory", cfg.privacy?.allow_raw_memory_to_tools ? "是" : "否");
    setFieldValue("#privacy-audit-tools", cfg.privacy?.audit_all_tool_calls ? "是" : "否");
  } catch (error) {
    // 配置加载失败不影响其他功能
  }
}

function setFieldValue(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.value = value;
}

async function loadMemories() {
  try {
    const memories = await apiFetch("/memories?limit=20", { method: "GET" });
    renderMemories(memories);
  } catch (error) {
    renderEmpty("#memory-list", error.message);
  }
}

async function loadSkills() {
  try {
    state.skills = await apiFetch("/skills", { method: "GET" });
    renderSkills(state.skills);
    renderSkillSelect(state.skills);
  } catch (error) {
    renderEmpty("#skill-list", error.message);
  }
}

async function loadTools() {
  try {
    state.tools = await apiFetch("/tools", { method: "GET" });
    renderTools(state.tools);
  } catch (error) {
    renderEmpty("#tool-list", error.message);
  }
}

async function loadAudit() {
  try {
    const audit = await apiFetch("/audit?limit=30", { method: "GET" });
    renderAudit(audit);
  } catch (error) {
    renderEmpty("#audit-list", error.message);
  }
}

async function loadCredentials() {
  try {
    const credentials = await apiFetch("/credentials?limit=20", { method: "GET" });
    renderCredentials(credentials);
  } catch (error) {
    renderEmpty("#credential-list", error.message);
  }
}

/* ===== Chat ===== */
async function submitChat(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  const payload = {
    message: document.querySelector("#chat-message").value.trim(),
    skill_name: valueOrNull(document.querySelector("#chat-skill").value),
    permission_token: valueOrNull(document.querySelector("#chat-token").value),
    user_confirmed: document.querySelector("#chat-confirmed").checked,
    limit: 8,
  };
  try {
    const data = await apiFetch("/chat", { method: "POST", body: JSON.stringify(payload) });
    renderChatResult(data);
    gsapAnim.resultFadeIn(document.querySelector("#chat-result"));
    SoundFX.play("chime");
    await Promise.allSettled([loadAudit(), loadCredentials()]);
  } catch (error) {
    renderText("#chat-result", error.message, true);
    gsapAnim.errorShake(document.querySelector("#chat-result"));
  }
}

function renderChatResult(data) {
  const result = document.querySelector("#chat-result");
  result.classList.remove("empty-state");
  result.style.color = "";

  const answer = data.answer || "";
  const skill = data.skill_result;
  const citations = data.citations || [];

  const skillHtml = skill
    ? `<div class="chat-result-skill">
        <div class="chat-result-skill-label">Skill 状态</div>
        <div class="chat-result-skill-status">${escapeHtml(skill.status || "—")}</div>
        <div class="chat-result-skill-audit">审计 ID：${escapeHtml(skill.audit_id || "无")}</div>
      </div>`
    : "";

  const citationsHtml = citations.length
    ? `<div class="chat-result-citations">
        <div class="chat-result-citations-label">引用来源</div>
        <ol class="chat-result-citations-list">
          ${citations.map((item, i) => `
            <li class="chat-result-citation">
              <span class="chat-result-citation-marker">${i + 1}</span>
              <span class="chat-result-citation-body">
                <span class="chat-result-citation-source">${escapeHtml(item.source_id || "")}</span>
                ${item.summary ? `<span class="chat-result-citation-summary">${escapeHtml(item.summary)}</span>` : ""}
              </span>
            </li>
          `).join("")}
        </ol>
      </div>`
    : "";

  result.innerHTML = `<div class="chat-result-answer">${escapeHtml(answer)}</div>${skillHtml}${citationsHtml}`;
}

/* ===== 记忆 ===== */
async function submitMemory(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  const emotionLabel = document.querySelector("#memory-emotion").value.trim();
  const payload = {
    event_summary: document.querySelector("#memory-summary").value.trim(),
    time_range: valueOrNull(document.querySelector("#memory-time").value),
    emotion: emotionLabel ? { label: emotionLabel, intensity: null } : null,
    insight: valueOrNull(document.querySelector("#memory-insight").value),
    tags: splitList(document.querySelector("#memory-tags").value),
    personality_signals: splitList(document.querySelector("#memory-signals").value),
  };
  try {
    await apiFetch("/memories", { method: "POST", body: JSON.stringify(payload) });
    event.target.reset();
    showToast("记忆已写入。");
    await Promise.allSettled([loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

function renderMemories(memories) {
  const target = document.querySelector("#memory-list");
  target.innerHTML = "";
  if (!memories.length) {
    renderEmpty("#memory-list", "暂无记忆。");
    return;
  }
  memories.forEach((memory) => {
    const item = document.createElement("article");
    item.className = "list-item";
    const emotionHtml = memory.emotion
      ? `<div class="memory-emotion">情绪：${escapeHtml(memory.emotion.label)}</div>`
      : "";
    item.innerHTML = `
      <header class="memory-header">
        <h4>${escapeHtml(memory.time_range || "未标注时间")}</h4>
        <span class="memory-id">${escapeHtml(memory.id)}</span>
      </header>
      <p class="memory-summary">${escapeHtml(memory.event_summary)}</p>
      ${emotionHtml}
      ${memory.insight ? `<div class="memory-insight">${escapeHtml(memory.insight)}</div>` : ""}
      <div class="memory-chips">
        ${renderChipGroup("标签", memory.tags || [])}
        ${renderChipGroup("性格", memory.personality_signals || [], "tag-accent")}
      </div>
      <div class="memory-actions">
        <button class="btn btn-secondary" type="button" data-action="delete">删除</button>
      </div>
    `;
    item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteMemory(memory.id));
    target.append(item);
  });
  gsapAnim.staggerItems(target, ".list-item");
  gsapAnim.buttonHover(target.querySelectorAll(".btn"));
}

async function deleteMemory(memoryId) {
  if (!confirm("确认删除这条记忆卡片？此操作不可撤销。")) return;
  try {
    await apiFetch(`/memories/${encodeURIComponent(memoryId)}`, { method: "DELETE" });
    showToast("记忆已删除。");
    await Promise.allSettled([loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

/* ===== Skill / Tool 表格 ===== */
function renderSkills(skills) {
  const rows = skills.map((skill) => `
    <tr>
      <td>
        <div class="skill-name">
          <span class="skill-name-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.085.706 1.698v.014c0 .613-.236 1.228-.706 1.698l-1.611 1.611a.984.984 0 0 1-.837.289c-.322-.049-.648.059-.878.289l-1.568 1.568c-.47.47-1.228.47-1.698 0l-1.568-1.568a1.001 1.001 0 0 0-.878-.289c-.322.049-.648-.059-.878-.289l-1.568-1.568c-.47-.47-.47-1.229 0-1.698l1.568-1.568c.23-.23.338-.556.289-.878-.049-.322.059-.648.289-.878l1.611-1.611c.47-.47 1.228-.47 1.698 0l1.568 1.568c.23.23.556.338.878.289z"/></svg>
          </span>
          <div class="skill-name-text">
            <strong>${escapeHtml(skill.display_name)}</strong>
            <span class="meta-line">${escapeHtml(skill.name)}</span>
          </div>
        </div>
      </td>
      <td>${escapeHtml(skill.description)}</td>
      <td><div class="chip-cell">${renderTags(skill.permissions || [])}</div></td>
      <td><div class="chip-cell">${renderTags(skill.triggers || [])}</div></td>
    </tr>
  `);
  renderTable("#skill-list", ["名称", "说明", "权限", "触发词"], rows, "暂无 Skill。");
}

function renderTools(tools) {
  const rows = tools.map((tool) => `
    <tr>
      <td>
        <div class="skill-name">
          <span class="skill-name-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v6"/><path d="M15 2v6"/><path d="M6 8h12v3a6 6 0 0 1-12 0V8z"/><path d="M12 17v5"/></svg>
          </span>
          <div class="skill-name-text">
            <strong>${escapeHtml(tool.display_name)}</strong>
            <span class="meta-line">${escapeHtml(tool.name)}</span>
          </div>
        </div>
      </td>
      <td>${escapeHtml(tool.description)}</td>
      <td><span class="status-indicator ${tool.enabled ? "is-enabled" : "is-disabled"}">${tool.enabled ? "已启用" : "已关闭"}</span></td>
      <td><div class="chip-cell">${renderTags(tool.permissions || [])}</div></td>
    </tr>
  `);
  renderTable("#tool-list", ["名称", "说明", "状态", "权限"], rows, "暂无工具。");
}

/* ===== 审计时间线 ===== */
function renderAudit(events) {
  const target = document.querySelector("#audit-list");
  target.innerHTML = "";
  if (!events.length) {
    renderEmpty("#audit-list", "暂无审计日志。");
    return;
  }
  events.forEach((event) => {
    const item = document.createElement("article");
    item.className = "list-item audit-entry";
    item.innerHTML = `
      <div class="audit-timeline">
        <div class="audit-time">
          <span class="audit-dot" aria-hidden="true"></span>
          <span class="audit-time-text">${escapeHtml(event.created_at || "")}</span>
        </div>
        <div class="audit-content">
          <div class="audit-header">
            <span class="audit-badge ${getAuditBadgeClass(event.event_type)}">${escapeHtml(event.event_type)}</span>
            <span class="audit-id">${escapeHtml(event.id || "")}</span>
          </div>
          <div class="audit-target"><strong>target:</strong> ${escapeHtml(event.target || "—")}</div>
          <details class="audit-payload">
            <summary>Payload</summary>
            <pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>
          </details>
        </div>
      </div>
    `;
    target.append(item);
  });
  gsapAnim.staggerItems(target, ".list-item");
}

/* ===== 凭证 ===== */
function renderCredentials(credentials) {
  const target = document.querySelector("#credential-list");
  target.innerHTML = "";
  if (!credentials.length) {
    renderEmpty("#credential-list", "暂无凭证。");
    return;
  }
  credentials.forEach((credential) => {
    const item = document.createElement("article");
    item.className = "list-item credential-item";
    item.innerHTML = `
      <header>
        <h4>${escapeHtml(credential.subject_type)} / ${escapeHtml(credential.subject_id)}</h4>
        <span class="status-pill ${credential.anchor_status === "verified" ? "" : "muted"}">${escapeHtml(credential.anchor_status)}</span>
      </header>
      <div class="credential-digest">${escapeHtml(credential.digest || "")}</div>
    `;
    target.append(item);
  });
  gsapAnim.staggerItems(target, ".list-item");
}

/* ===== 授权 ===== */
async function submitPermission(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  const payload = {
    target: document.querySelector("#permission-target").value.trim(),
    scope: splitList(document.querySelector("#permission-scope").value),
  };
  const resultBox = document.querySelector("#permission-result");
  try {
    const data = await apiFetch("/permissions/grants", { method: "POST", body: JSON.stringify(payload) });
    resultBox.classList.remove("empty-state");
    resultBox.style.color = "";
    resultBox.innerHTML = `
      <div class="permission-result-label">授权 Token</div>
      <div class="permission-token-block">${escapeHtml(data.id)}</div>
      <div class="permission-result-hint">已自动填入 Chat 的权限 Token 输入框。</div>
    `;
    gsapAnim.resultFadeIn(resultBox);
    document.querySelector("#chat-token").value = data.id;
    showToast("授权已创建。");
    await loadAudit();
  } catch (error) {
    resultBox.classList.remove("empty-state");
    resultBox.innerHTML = `<p style="color: var(--rose); margin: 0;">${escapeHtml(error.message)}</p>`;
    gsapAnim.errorShake(resultBox);
  }
}

async function submitCredential(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  let payloadContent;
  try {
    payloadContent = JSON.parse(document.querySelector("#credential-payload").value);
  } catch (error) {
    showToast("凭证内容必须是合法 JSON。");
    return;
  }
  const payload = {
    subject_type: document.querySelector("#credential-type").value.trim(),
    subject_id: document.querySelector("#credential-id").value.trim(),
    payload: payloadContent,
    metadata: { source: "web_console" },
  };
  try {
    await apiFetch("/credentials/hash", { method: "POST", body: JSON.stringify(payload) });
    event.target.reset();
    document.querySelector("#credential-type").value = "memory";
    showToast("本地哈希凭证已生成。");
    await Promise.allSettled([loadCredentials(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

/* ===== 渲染辅助 ===== */
function renderSkillSelect(skills) {
  elements.chatSkill.innerHTML = '<option value="">自动判断</option>';
  skills.forEach((skill) => {
    const option = document.createElement("option");
    option.value = skill.name;
    option.textContent = skill.display_name;
    elements.chatSkill.append(option);
  });
}

function renderTable(selector, headers, rows, emptyText) {
  const target = document.querySelector(selector);
  if (!rows.length) {
    renderEmpty(selector, emptyText);
    return;
  }
  target.innerHTML = `
    <table class="table">
      <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.join("")}</tbody>
    </table>
  `;
}

function renderEmpty(selector, text) {
  const target = document.querySelector(selector);
  target.innerHTML = `<div class="empty-state-box">
    <div class="empty-state-icon">${getEmptyIcon(selector)}</div>
    <div class="empty-state-text">${escapeHtml(text)}</div>
  </div>`;
}

function getEmptyIcon(selector) {
  const icons = {
    "#memory-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    "#recording-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>',
    "#audit-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    "#credential-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "#skill-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/></svg>',
    "#tool-list": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
  };
  return icons[selector] || '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="9"/></svg>';
}

function renderText(selector, text, isError = false) {
  const target = document.querySelector(selector);
  target.classList.toggle("empty-state", false);
  target.style.color = isError ? "var(--rose)" : "inherit";
  target.textContent = text;
}

function renderTags(values) {
  return values.map((v) => `<span class="tag">${escapeHtml(v)}</span>`).join("");
}

function renderChipGroup(label, values, variant = "") {
  if (!values || !values.length) return "";
  const chips = values.map((v) => `<span class="tag ${variant}">${escapeHtml(v)}</span>`).join("");
  return `<div class="chip-group"><span class="chip-label">${escapeHtml(label)}</span>${chips}</div>`;
}

function getAuditBadgeClass(eventType) {
  if (!eventType) return "audit-badge-default";
  const type = eventType.toLowerCase();
  if (type.includes("memory")) return "audit-badge-memory";
  if (type.includes("skill")) return "audit-badge-skill";
  if (type.includes("tool")) return "audit-badge-tool";
  if (type.includes("permission") || type.includes("grant")) return "audit-badge-permission";
  if (type.includes("credential")) return "audit-badge-credential";
  if (type.includes("recording") || type.includes("transcri")) return "audit-badge-recording";
  return "audit-badge-default";
}

function splitList(value) {
  return value.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
}

function valueOrNull(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function setRequestStatus(text) {
  elements.requestStatus.textContent = text;
}

function showToast(message) {
  elements.toast.textContent = message;
  window.clearTimeout(showToast.timer);
  gsapAnim.showToast(elements.toast);
  showToast.timer = window.setTimeout(() => {
    gsapAnim.hideToast(elements.toast);
  }, 3200);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* ===== 录音采集 ===== */
function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = String(Math.floor(total / 60)).padStart(2, "0");
  const secs = String(total % 60).padStart(2, "0");
  return `${minutes}:${secs}`;
}

async function toggleRecording() {
  if (recorder.mediaRecorder && recorder.mediaRecorder.state === "recording") {
    recorder.mediaRecorder.stop();
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast("当前浏览器不支持录音采集。");
    return;
  }
  try {
    recorder.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    showToast("麦克风授权失败：" + error.message);
    return;
  }
  recorder.chunks = [];
  recorder.blob = null;
  const mimeType = pickSupportedMimeType();
  recorder.mediaRecorder = new MediaRecorder(recorder.stream, mimeType ? { mimeType } : undefined);
  recorder.mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data && event.data.size > 0) recorder.chunks.push(event.data);
  });
  recorder.mediaRecorder.addEventListener("stop", () => {
    const type = recorder.mediaRecorder.mimeType || mimeType || "audio/webm";
    recorder.blob = new Blob(recorder.chunks, { type });
    elements.recordPreview.src = URL.createObjectURL(recorder.blob);
    elements.recordPreview.hidden = false;
    elements.recordUpload.disabled = false;
    setRecordStatus("已停止", false);
    stopTimer();
    if (recorder.stream) {
      recorder.stream.getTracks().forEach((track) => track.stop());
      recorder.stream = null;
    }
  });
  recorder.mediaRecorder.start();
  recorder.startedAt = Date.now();
  if (elements.recBtnLabel) elements.recBtnLabel.textContent = "停止录音";
  elements.recordUpload.disabled = true;
  elements.recordPreview.hidden = true;
  setRecordStatus("录音中", true);
  startTimer();
  elements.recorderHint.textContent = "正在录音。再次点击按钮可停止，然后上传转写。";
}

function pickSupportedMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return "";
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

function startTimer() {
  stopTimer();
  recorder.timerId = window.setInterval(() => {
    elements.recordTimer.textContent = formatDuration((Date.now() - recorder.startedAt) / 1000);
  }, 500);
}

function stopTimer() {
  if (recorder.timerId) {
    window.clearInterval(recorder.timerId);
    recorder.timerId = null;
  }
}

function setRecordStatus(text, active) {
  elements.recordStatus.textContent = text;
  elements.recordStatus.dataset.state = active ? "recording" : "idle";
  if (elements.recorderBox) {
    elements.recorderBox.classList.toggle("is-recording", active);
  }
  if (elements.recorderWaveform) {
    elements.recorderWaveform.hidden = !active;
  }
}

async function uploadCapturedRecording() {
  if (!recorder.blob) {
    showToast("没有可上传的录音。");
    return;
  }
  const duration = (Date.now() - recorder.startedAt) / 1000;
  const file = new File([recorder.blob], `recording-${Date.now()}.webm`, { type: recorder.blob.type });
  await uploadRecordingFile(file, duration);
  recorder.blob = null;
  recorder.chunks = [];
  elements.recordUpload.disabled = true;
  elements.recordPreview.hidden = true;
  if (elements.recBtnLabel) elements.recBtnLabel.textContent = "开始录音";
  elements.recorderHint.textContent = "点击录音按钮授权麦克风。全天可分段录制多次，每段独立转写并入库。";
}

async function submitRecordingFile(event) {
  event.preventDefault();
  const input = document.querySelector("#recording-file");
  const file = input.files && input.files[0];
  if (!file) {
    showToast("请先选择音频文件。");
    return;
  }
  await uploadRecordingFile(file, null);
  input.value = "";
}

async function uploadRecordingFile(file, durationSeconds) {
  const formData = new FormData();
  formData.append("file", file);
  if (durationSeconds !== null && durationSeconds !== undefined) {
    formData.append("recorded_at", new Date().toISOString());
  }
  setRequestStatus("上传中");
  try {
    const headers = {};
    // API Key（可选）
    const apiKey = elements.apiKey.value.trim();
    if (apiKey) headers["x-api-key"] = apiKey;
    const response = await fetch(`${API_BASE}/recordings`, { method: "POST", headers, body: formData });

    const requestId = response.headers.get("x-request-id");
    setRequestStatus(requestId ? `请求 ${requestId.slice(0, 8)}` : "完成");
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) throw new Error(data?.error?.message || `上传失败：${response.status}`);
    showToast("录音已上传，转写与提炼已完成。");
    await Promise.allSettled([loadRecordings(), loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

async function loadRecordings() {
  try {
    const recordings = await apiFetch("/recordings?limit=50", { method: "GET" });
    renderRecordings(recordings);
  } catch (error) {
    renderEmpty("#recording-list", error.message);
  }
}

async function transcribeRecording(recordingId) {
  try {
    await apiFetch(`/recordings/${encodeURIComponent(recordingId)}/transcribe`, {
      method: "POST",
      body: JSON.stringify({ language: "zh", auto_extract: true }),
    });
    showToast("转写已重新执行。");
    await Promise.allSettled([loadRecordings(), loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

async function extractRecordingMemories(recordingId) {
  try {
    await apiFetch(`/recordings/${encodeURIComponent(recordingId)}/extract`, {
      method: "POST",
      body: JSON.stringify({ max_cards: 5 }),
    });
    showToast("已从转写文本提炼记忆卡片。");
    await Promise.allSettled([loadRecordings(), loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteRecording(recordingId) {
  if (!confirm("确认删除该录音？原始音频与转写记录将被移除（已生成的记忆卡片保留）。")) return;
  try {
    await apiFetch(`/recordings/${encodeURIComponent(recordingId)}`, { method: "DELETE" });
    showToast("录音已删除。");
    await Promise.allSettled([loadRecordings(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

function renderRecordings(recordings) {
  const target = document.querySelector("#recording-list");
  target.innerHTML = "";
  if (!recordings.length) {
    renderEmpty("#recording-list", "暂无录音。点击左侧开始记录一天。");
    return;
  }
  recordings.forEach((recording) => {
    const item = document.createElement("article");
    item.className = "list-item recording-item";
    const status = recording.transcript_status || "pending";
    const statusText = { pending: "待转写", running: "转写中", completed: "已转写", failed: "转写失败" }[status] || status;
    const statusClass = {
      completed: "recording-status-completed",
      pending: "recording-status-pending",
      running: "recording-status-running",
      failed: "recording-status-failed",
    }[status] || "recording-status-pending";
    const transcriptBlock = recording.transcript
      ? `<details class="recording-transcript"><summary>转写文本</summary><p>${escapeHtml(recording.transcript)}</p></details>`
      : "";
    const memoryIds = (recording.extracted_memory_ids || []).map((id) => `<span class="tag">${escapeHtml(id)}</span>`).join("");
    item.innerHTML = `
      <header>
        <div>
          <h4>${escapeHtml(recording.file_name)}</h4>
          <span class="meta-line">${escapeHtml(recording.recorded_at)} · ${formatBytes(recording.size_bytes)}</span>
        </div>
      </header>
      <div class="tag-row">
        <span class="status-pill ${statusClass}">${escapeHtml(statusText)}</span>
        ${recording.transcript_provider ? `<span class="tag">${escapeHtml(recording.transcript_provider)}</span>` : ""}
      </div>
      ${transcriptBlock}
      ${recording.transcript_error ? `<p class="muted-text">错误：${escapeHtml(recording.transcript_error)}</p>` : ""}
      ${memoryIds ? `<div class="meta-line">已提炼记忆：</div><div class="tag-row">${memoryIds}</div>` : ""}
      <div class="recording-actions">
        <button class="btn btn-secondary" type="button" data-action="transcribe">重新转写</button>
        <button class="btn btn-secondary" type="button" data-action="extract">提炼记忆</button>
        <button class="btn btn-danger" type="button" data-action="delete">删除</button>
      </div>
    `;
    item.querySelector('[data-action="transcribe"]').addEventListener("click", () => transcribeRecording(recording.id));
    item.querySelector('[data-action="extract"]').addEventListener("click", () => extractRecordingMemories(recording.id));
    item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteRecording(recording.id));
    target.append(item);
  });
  gsapAnim.staggerItems(target, ".list-item");
  gsapAnim.buttonHover(target.querySelectorAll(".btn"));
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

/* ===== 今日故事 ===== */
async function submitStory(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  const prompt = document.querySelector("#story-prompt")?.value.trim() || "生成今日故事";
  const confirmed = document.querySelector("#story-confirmed")?.checked || false;
  const resultBox = document.querySelector("#story-result");
  resultBox.classList.remove("empty-state");
  resultBox.innerHTML = '<p class="muted-text">正在生成故事...</p>';
  try {
    const payload = { user_intent: prompt, user_confirmed: confirmed, memory_query: { query: prompt, limit: 10 } };
    const data = await apiFetch("/skills/daily_story/run", { method: "POST", body: JSON.stringify(payload) });
    renderStoryResult(data);
    gsapAnim.resultFadeIn(resultBox);
    SoundFX.play("chime");
    await loadAudit();
  } catch (error) {
    resultBox.innerHTML = `<p style="color: var(--rose)">${escapeHtml(error.message)}</p>`;
    gsapAnim.errorShake(resultBox);
  }
}

function renderStoryResult(data) {
  const resultBox = document.querySelector("#story-result");
  resultBox.classList.remove("empty-state");

  if (data.status === "permission_required") {
    resultBox.innerHTML = `
      <p>这个 Skill 需要授权才能读取记忆。请勾选「本次确认授权」后重试。</p>
      <p class="muted-text">缺少权限：${escapeHtml((data.missing_permissions || []).join(", "))}</p>
    `;
    return;
  }

  const output = data.result?.model_output || "";
  const memoryIds = (data.used_context || []).map((c) => c.source_id);
  const sections = parseStorySections(output);

  resultBox.innerHTML = `
    <div class="story-section">
      <h4>${escapeHtml(sections.title || "今日故事")}</h4>
    </div>
    <div class="story-section">
      <h5>故事</h5>
      <div class="story-body">${escapeHtml(sections.story || output || "暂无故事内容。")}</div>
    </div>
    <div class="story-section story-anchors">
      <h5>今日真实锚点</h5>
      <ul>${(sections.real_anchors || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("") || "<li>暂无</li>"}</ul>
    </div>
    <div class="story-section story-fiction">
      <h5>文学虚构元素</h5>
      <ul>${(sections.fictional_elements || []).map((f) => `<li>${escapeHtml(f)}</li>`).join("") || "<li>暂无</li>"}</ul>
    </div>
    <div class="story-section">
      <h5>今日性格侧面</h5>
      <p>${escapeHtml(sections.personality || "暂无")}</p>
    </div>
    <div class="story-section">
      <h5>续写钩子</h5>
      <p>${escapeHtml(sections.hook || "暂无")}</p>
    </div>
    ${memoryIds.length ? `<div class="meta-line">引用记忆：${memoryIds.map((id) => `<span class="tag">${escapeHtml(id)}</span>`).join("")}</div>` : ""}
    <div class="meta-line">审计 ID：${escapeHtml(data.audit_id || "无")}</div>
  `;
}

function parseStorySections(text) {
  const sections = { title: "", story: "", real_anchors: [], fictional_elements: [], personality: "", hook: "" };
  if (!text) return sections;
  const titleMatch = text.match(/^#\s*(.+)$/m);
  if (titleMatch) sections.title = titleMatch[1].trim();
  const storyMatch = text.match(/##\s*故事\s*\n([\s\S]*?)(?=##\s|$)/);
  if (storyMatch) sections.story = storyMatch[1].trim();
  const anchorMatch = text.match(/##\s*今日真实锚点\s*\n([\s\S]*?)(?=##\s|$)/);
  if (anchorMatch) sections.real_anchors = anchorMatch[1].split("\n").map((l) => l.replace(/^[-*]\s*/, "").trim()).filter(Boolean);
  const fictionMatch = text.match(/##\s*文学虚构元素\s*\n([\s\S]*?)(?=##\s|$)/);
  if (fictionMatch) sections.fictional_elements = fictionMatch[1].split("\n").map((l) => l.replace(/^[-*]\s*/, "").trim()).filter(Boolean);
  const personalityMatch = text.match(/##\s*今日性格侧面\s*\n([\s\S]*?)(?=##\s|$)/);
  if (personalityMatch) sections.personality = personalityMatch[1].trim();
  const hookMatch = text.match(/##\s*续写钩子\s*\n([\s\S]*?)(?=##\s|$)/);
  if (hookMatch) sections.hook = hookMatch[1].trim();
  return sections;
}

/* ===== 文本提炼 ===== */
async function submitExtract(event) {
  event.preventDefault();
  const submitButton = event.submitter || event.target.querySelector('button[type="submit"]');
  gsapAnim.formSubmitFeedback(submitButton);
  const text = document.querySelector("#extract-text")?.value.trim();
  if (!text) {
    showToast("请输入要提炼的文本内容。");
    return;
  }
  const resultBox = document.querySelector("#extract-result");
  resultBox.classList.remove("empty-state");
  resultBox.innerHTML = '<p class="muted-text">正在提炼...</p>';
  try {
    const data = await apiFetch("/memories/extract", { method: "POST", body: JSON.stringify({ text: text, max_cards: 5 }) });
    if (data.memory_cards && data.memory_cards.length) {
      resultBox.innerHTML = `<p>已提炼 ${data.memory_cards.length} 张记忆卡片：</p>` +
        data.memory_cards.map((card) =>
          `<div class="list-item"><p>${escapeHtml(card.event_summary)}</p>${card.insight ? `<p class="muted-text">${escapeHtml(card.insight)}</p>` : ""}</div>`
        ).join("");
    } else {
      resultBox.innerHTML = `<p class="muted-text">${escapeHtml(data.error || "未能从文本中提炼记忆卡片。")}</p>`;
    }
    gsapAnim.resultFadeIn(resultBox);
    await Promise.allSettled([loadMemories(), loadAudit()]);
  } catch (error) {
    resultBox.innerHTML = `<p style="color: var(--rose)">${escapeHtml(error.message)}</p>`;
    gsapAnim.errorShake(resultBox);
  }
}

/* ===== 清除所有记忆 ===== */
async function clearAllMemories() {
  if (!confirm("确认清除所有记忆卡片？此操作不可撤销！录音和审计日志不受影响。")) return;
  try {
    const data = await apiFetch("/memories", { method: "DELETE" });
    showToast(`已清除 ${data.deleted_count} 条记忆。`);
    await Promise.allSettled([loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

/* ============================================================
   音效系统 · WebAudio 实时合成(零音频资产)
   规则:首个 gesture 前静默 / hover 节流 200ms /
        prefers-reduced-motion = 全局静音 / 开关存 localStorage
   ============================================================ */
const SoundFX = {
  ctx: null,
  enabled: true,
  reduced: false,
  lastHoverAt: 0,
  _lastHoverEl: null,
  _noiseBuf: null,

  init() {
    this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    try {
      this.enabled = localStorage.getItem("smart-avatar-sound") !== "off";
    } catch (e) {}
    this.toggleBtn = document.querySelector("#sound-toggle");
    this.toggleBtn?.addEventListener("click", () => this.toggle());
    this.updateIcon();

    /* 卡片 hover · 木质轻扣(节流 200ms) */
    document.addEventListener("mouseover", (event) => {
      if (!this.enabled || this.reduced) return;
      const now = performance.now();
      if (now - this.lastHoverAt < 200) return;
      const hit = event.target.closest(".btn, .list-item, .heatmap-cell, .cmdk-item, .rec-btn");
      if (!hit || hit === this._lastHoverEl) return;
      this._lastHoverEl = hit;
      this.lastHoverAt = now;
      this.play("hover");
    });

    /* 点击 · 软橡胶 tap(页签切换走 swish,不叠加) */
    document.addEventListener("click", (event) => {
      if (!this.enabled || this.reduced) return;
      if (event.target.closest(".nav-item, #sound-toggle, #theme-toggle, #cmdk-open")) return;
      if (event.target.closest(".btn, .btn-mini")) this.play("tap");
    });
  },

  toggle() {
    this.enabled = !this.enabled;
    try {
      localStorage.setItem("smart-avatar-sound", this.enabled ? "on" : "off");
    } catch (e) {}
    this.updateIcon();
    if (this.enabled) this.play("theme"); /* 按下即试听 */
  },

  updateIcon() {
    if (!this.toggleBtn) return;
    const on = this.enabled && !this.reduced;
    this.toggleBtn.querySelector(".icon-sound-on").hidden = !on;
    this.toggleBtn.querySelector(".icon-sound-off").hidden = on;
  },

  ensureCtx() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      this.ctx = new AC();
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  },

  play(name) {
    if (!this.enabled || this.reduced) return;
    const ctx = this.ensureCtx();
    if (!ctx) return;
    const recipe = this.recipes[name];
    if (recipe) recipe.call(this, ctx);
  },

  _noiseBuffer(ctx) {
    if (this._noiseBuf) return this._noiseBuf;
    const len = ctx.sampleRate;
    const buffer = ctx.createBuffer(1, len, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    this._noiseBuf = buffer;
    return buffer;
  },

  _tone(ctx, { freq, freqEnd, dur, type = "sine", vol = 0.2, delay = 0 }) {
    const t = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    if (freqEnd) osc.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    gain.gain.setValueAtTime(vol, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  },

  _noise(ctx, { dur, vol = 0.2, delay = 0, freq = 1200, freqEnd, q = 1.2 }) {
    const t = ctx.currentTime + delay;
    const src = ctx.createBufferSource();
    src.buffer = this._noiseBuffer(ctx);
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(freq, t);
    if (freqEnd) filter.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    filter.Q.value = q;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(vol, t + dur * 0.3);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(filter).connect(gain).connect(ctx.destination);
    src.start(t);
    src.stop(t + dur + 0.02);
  },

  recipes: {
    /* 木质轻扣 ~80ms · 0.12 */
    hover(ctx) {
      this._tone(ctx, { freq: 190, freqEnd: 120, dur: 0.08, type: "triangle", vol: 0.12 });
    },
    /* 软橡胶 tap · 0.22 */
    tap(ctx) {
      this._tone(ctx, { freq: 150, freqEnd: 88, dur: 0.11, vol: 0.22 });
    },
    /* 页面转化 · 翻纸 swish ~300ms · 0.28(全站签名音效) */
    swish(ctx) {
      this._noise(ctx, { dur: 0.3, vol: 0.28, freq: 900, freqEnd: 2600, q: 1.1 });
    },
    /* 台灯开关 click · 0.30 */
    theme(ctx) {
      this._tone(ctx, { freq: 1800, dur: 0.014, type: "square", vol: 0.18 });
      this._tone(ctx, { freq: 900, dur: 0.03, type: "square", vol: 0.3, delay: 0.045 });
    },
    /* ⌘K 开 · 机械 blip · 0.20 */
    cmdkOpen(ctx) {
      this._tone(ctx, { freq: 700, freqEnd: 1400, dur: 0.055, type: "square", vol: 0.2 });
    },
    /* ⌘K 关 · pop · 0.20 */
    cmdkClose(ctx) {
      this._tone(ctx, { freq: 320, freqEnd: 160, dur: 0.07, vol: 0.2 });
    },
    /* 生成完成 · 极轻风铃 · 0.12 */
    chime(ctx) {
      this._tone(ctx, { freq: 1568, dur: 0.5, vol: 0.12 });
      this._tone(ctx, { freq: 2093, dur: 0.6, vol: 0.09, delay: 0.07 });
    },
  },
};

/* ============================================================
   主题 · 日间 / 夜晚台灯
   ============================================================ */
const ThemeStore = {
  key: "smart-avatar-theme",

  init() {
    this.btn = document.querySelector("#theme-toggle");
    this.syncIcon();
    this.btn?.addEventListener("click", () => {
      this.set(this.current() === "dark" ? "light" : "dark");
      SoundFX.play("theme");
    });
  },

  current() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  },

  set(theme) {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(this.key, theme);
    } catch (e) {}
    this.syncIcon();
  },

  syncIcon() {
    if (!this.btn) return;
    const dark = this.current() === "dark";
    this.btn.querySelector(".icon-sun").hidden = dark;
    this.btn.querySelector(".icon-moon").hidden = !dark;
  },
};

/* ============================================================
   SunlightCanvas · 3–4 团奶油/杏色/陶土慢速光斑
   像下午四点穿窗帘的阳光 · 躺在留白里
   ============================================================ */
const Sunlight = {
  blobs: [],
  raf: 0,

  init() {
    this.canvas = document.querySelector("#sunlight");
    if (!this.canvas) return;
    this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.ctx = this.canvas.getContext("2d");
    this.resize();
    window.addEventListener("resize", () => this.resize());

    const palette = [
      [250, 236, 205], /* 奶油 */
      [246, 216, 168], /* 杏 */
      [226, 165, 116], /* 陶土淡 */
      [248, 228, 190], /* 奶油杏 */
    ];
    for (let i = 0; i < 4; i++) {
      this.blobs.push({
        x: 0.12 + 0.76 * ((i * 41 + 13) % 100) / 100,
        y: 0.15 + 0.6 * ((i * 67 + 29) % 100) / 100,
        r: 0.3 + 0.14 * ((i * 53 + 7) % 100) / 100,
        c: palette[i],
        speed: 0.000014 + 0.000007 * i,
        phase: i * 1.7,
        drift: 0.05 + 0.02 * i,
      });
    }

    if (this.reduced) {
      this.draw(0); /* 静态渐变一帧 */
      return;
    }
    const loop = (t) => {
      if (!document.hidden) this.draw(t);
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  },

  resize() {
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = window.innerWidth * this.dpr;
    this.canvas.height = window.innerHeight * this.dpr;
  },

  draw(t) {
    const { ctx, canvas } = this;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const dark = document.documentElement.dataset.theme === "dark";
    for (const b of this.blobs) {
      const dx = Math.sin(t * b.speed + b.phase) * b.drift;
      const dy = Math.cos(t * b.speed * 0.8 + b.phase * 1.3) * b.drift * 0.7;
      const cx = (b.x + dx) * w;
      const cy = (b.y + dy) * h;
      const r = b.r * Math.min(w, h) * (1 + 0.06 * Math.sin(t * b.speed * 1.4 + b.phase));
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
      const [cr, cg, cb] = b.c;
      const alpha = dark ? 0.1 : 0.24;
      g.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
      g.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
    }
  },
};

/* ============================================================
   软点光标 · 12px 半透明暖橙,hover 温柔放大
   ============================================================ */
const CursorDot = {
  x: -100,
  y: -100,
  tx: -100,
  ty: -100,

  init() {
    this.el = document.querySelector("#cursor-dot");
    if (!this.el) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    this.el.hidden = false;
    document.addEventListener("mousemove", (e) => {
      this.tx = e.clientX;
      this.ty = e.clientY;
    });
    document.addEventListener("mouseover", (e) => {
      const interactive = e.target.closest("a, button, input, select, textarea, summary, .heatmap-cell, .cmdk-item");
      this.el.classList.toggle("is-hovering", !!interactive);
    });
    const loop = () => {
      this.x += (this.tx - this.x) * 0.18;
      this.y += (this.ty - this.y) * 0.18;
      this.el.style.transform = `translate(${this.x}px, ${this.y}px) translate(-50%, -50%)`;
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  },
};

/* ============================================================
   黑客位之叁 · 页脚状态行
   ============================================================ */
const StatusLine = {
  init() {
    this.el = document.querySelector("#status-line");
    if (!this.el) return;
    this.tick();
    setInterval(() => this.tick(), 30000);
  },

  tick() {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    this.el.textContent = `LOCAL ${hh}:${mm} · BUILT ${APP_BUILT} · ${APP_VERSION}`;
  },
};

/* ============================================================
   黑客位之壹 · ⌘K 命令面板(全站唯一终端)
   ============================================================ */
const CmdK = {
  commands: [],
  filtered: [],
  activeIndex: 0,

  init() {
    this.root = document.querySelector("#cmdk");
    this.input = document.querySelector("#cmdk-input");
    this.list = document.querySelector("#cmdk-list");
    if (!this.root || !this.input || !this.list) return;
    this.buildCommands();

    document.querySelector("#cmdk-open")?.addEventListener("click", () => this.open());
    this.root.querySelector("[data-cmdk-close]")?.addEventListener("click", () => this.close());
    this.input.addEventListener("input", () => {
      this.activeIndex = 0;
      this.render();
    });
    this.input.addEventListener("keydown", (e) => this.onKey(e));

    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        this.root.hidden ? this.open() : this.close();
      } else if (e.key === "Escape" && !this.root.hidden) {
        this.close();
      }
    });
  },

  buildCommands() {
    const nav = Object.keys(titles).map((tab) => ({
      label: `去「${titles[tab].title}」`,
      hint: titles[tab].index,
      kind: "PAGE",
      run: () => activateTab(tab),
    }));
    const actions = [
      { label: "写一条消息", kind: "ACTION", run: () => { activateTab("chat"); focusSoon("#chat-message"); } },
      { label: "新增一条记忆", kind: "ACTION", run: () => { activateTab("memories"); focusSoon("#memory-summary"); } },
      { label: "生成今日故事", kind: "ACTION", run: () => { activateTab("story"); focusSoon("#story-prompt"); } },
      { label: "开始 / 停止录音", kind: "ACTION", run: () => { activateTab("recordings"); setTimeout(() => elements.recordToggle?.click(), 400); } },
      { label: "切换主题(日间 / 夜晚台灯)", kind: "ACTION", run: () => document.querySelector("#theme-toggle")?.click() },
      { label: "切换音效", kind: "ACTION", run: () => document.querySelector("#sound-toggle")?.click() },
      { label: "导出全部数据", kind: "ACTION", run: () => { window.location.href = "/api/v1/export"; } },
      { label: "打开调试面板", kind: "ACTION", run: () => DebugPanel.toggle(true) },
    ];
    this.commands = [...nav, ...actions];
  },

  open() {
    this.root.hidden = false;
    this.input.value = "";
    this.activeIndex = 0;
    this.render();
    SoundFX.play("cmdkOpen");
    setTimeout(() => this.input.focus(), 30);
  },

  close() {
    if (this.root.hidden) return;
    this.root.hidden = true;
    SoundFX.play("cmdkClose");
  },

  onKey(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this.move(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this.move(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = this.filtered[this.activeIndex];
      if (cmd) {
        this.close();
        cmd.run();
      }
    }
  },

  move(delta) {
    if (!this.filtered.length) return;
    this.activeIndex = (this.activeIndex + delta + this.filtered.length) % this.filtered.length;
    this.render();
  },

  match(query, text) {
    /* 子序列模糊匹配 */
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    let qi = 0;
    for (let i = 0; i < t.length && qi < q.length; i++) {
      if (t[i] === q[qi]) qi++;
    }
    return qi === q.length;
  },

  render() {
    const q = this.input.value.trim();
    this.filtered = q ? this.commands.filter((c) => this.match(q, c.label)) : this.commands;
    if (this.activeIndex >= this.filtered.length) this.activeIndex = 0;
    if (!this.filtered.length) {
      this.list.innerHTML = `<li class="cmdk-empty">没有匹配的命令</li>`;
      return;
    }
    this.list.innerHTML = this.filtered
      .map(
        (c, i) => `
      <li class="cmdk-item ${i === this.activeIndex ? "is-active" : ""}" role="option" data-index="${i}">
        <span>${escapeHtml(c.label)}</span>
        <span class="cmdk-item-kind">${escapeHtml(c.hint || c.kind)}</span>
      </li>`
      )
      .join("");
    this.list.querySelectorAll(".cmdk-item").forEach((item) => {
      item.addEventListener("click", () => {
        const cmd = this.filtered[Number(item.dataset.index)];
        if (cmd) {
          this.close();
          cmd.run();
        }
      });
      item.addEventListener("mousemove", () => {
        const idx = Number(item.dataset.index);
        if (idx !== this.activeIndex) {
          this.activeIndex = idx;
          this.render();
        }
      });
    });
    this.list.querySelector(".cmdk-item.is-active")?.scrollIntoView({ block: "nearest" });
  },
};

/* ============================================================
   黑客位之肆 · 调试面板(按 ` 开合)
   ============================================================ */
const DebugPanel = {
  init() {
    this.root = document.querySelector("#debug-panel");
    this.content = document.querySelector("#debug-content");
    if (!this.root || !this.content) return;
    document.querySelector("#debug-close")?.addEventListener("click", () => this.toggle(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "`" && !e.metaKey && !e.ctrlKey && !isTyping(e)) {
        e.preventDefault();
        this.toggle(this.root.hidden);
      }
    });
    setInterval(() => {
      if (!this.root.hidden) this.render();
    }, 1000);
  },

  toggle(show) {
    this.root.hidden = !show;
    if (show) {
      this.render();
      SoundFX.play("cmdkOpen");
    }
  },

  render() {
    const up = Math.floor((Date.now() - stats.startedAt) / 1000);
    const upText = up < 60 ? `${up}s` : `${Math.floor(up / 60)}m ${up % 60}s`;
    let mem = "n/a";
    if (performance.memory) mem = `${(performance.memory.usedJSHeapSize / 1048576).toFixed(1)} MB`;
    const lines = [
      `BUILT   ${APP_BUILT} · ${APP_VERSION}`,
      `UPTIME  ${upText}`,
      `REQS    ${stats.requests}${stats.lastRequestId ? ` · last ${stats.lastRequestId}` : ""}`,
      `HEALTH  ${stats.healthMs !== null ? `${stats.healthMs}ms` : "—"}`,
      `MEM     ${mem}`,
      `THEME   ${ThemeStore.current()} · SOUND ${SoundFX.enabled && !SoundFX.reduced ? "on" : "off"}`,
      `VIEW    ${window.innerWidth}×${window.innerHeight} · DPR ${window.devicePixelRatio || 1}`,
    ];
    this.content.textContent = lines.join("\n");
  },
};

/* ============================================================
   黑客位之贰 · 一年的日常(暖橙五档热力图)
   真实记忆/录音聚合 · 空库时固定 seed 示例(禁渲染时随机)
   ============================================================ */
const Heatmap = {
  DAYS: 364,

  init() {
    this.el = document.querySelector("#heatmap");
    this.note = document.querySelector("#heatmap-note");
    if (!this.el) return;
    this.refresh();
  },

  async refresh() {
    if (!this.el) return;
    let counts = null;
    try {
      const [memories, recordings] = await Promise.all([
        apiFetch("/memories?limit=500", { method: "GET" }),
        apiFetch("/recordings?limit=200", { method: "GET" }),
      ]);
      counts = this.aggregate(memories, recordings);
    } catch (error) {
      counts = null;
    }
    if (!counts || counts.total === 0) {
      counts = this.seededDemo();
      this.note.textContent = "示例密度 · 写入第一条记忆后,这里会长出你的日常";
    } else {
      this.note.textContent = `过去一年,共 ${counts.total} 条记忆与录音`;
    }
    this.render(counts.byDay);
  },

  aggregate(memories, recordings) {
    const byDay = {};
    let total = 0;
    const add = (stamp) => {
      if (!stamp) return;
      const day = String(stamp).slice(0, 10);
      byDay[day] = (byDay[day] || 0) + 1;
      total += 1;
    };
    (memories || []).forEach((m) => add(m.created_at));
    (recordings || []).forEach((r) => add(r.recorded_at));
    return { byDay, total };
  },

  /* mulberry32 固定 seed 生成器:每次渲染结果一致 */
  seededDemo() {
    let seed = 20260716;
    const rand = () => {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const byDay = {};
    const today = new Date();
    for (let i = this.DAYS; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const key = toDayKey(d);
      const recency = 1 - i / this.DAYS;
      const weekday = d.getDay() > 0 && d.getDay() < 6 ? 0.22 : 0;
      if (rand() < 0.26 + recency * 0.38 + weekday) {
        byDay[key] = 1 + Math.floor(rand() * 4 * (0.4 + recency));
      }
    }
    return { byDay, total: Object.values(byDay).reduce((a, b) => a + b, 0) };
  },

  level(v) {
    if (!v) return 0;
    if (v === 1) return 1;
    if (v === 2) return 2;
    if (v <= 4) return 3;
    return 4;
  },

  render(byDay) {
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - (this.DAYS - 1));
    start.setDate(start.getDate() - start.getDay()); /* 对齐到周日 */
    const cells = [];
    const cursor = new Date(start);
    while (cursor <= today) {
      const key = toDayKey(cursor);
      const v = byDay[key] || 0;
      cells.push(`<span class="heatmap-cell" data-level="${this.level(v)}" title="${key} · ${v} 条"></span>`);
      cursor.setDate(cursor.getDate() + 1);
    }
    this.el.innerHTML = cells.join("");
  },
};

/* ===== 小工具 ===== */
function toDayKey(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function focusSoon(selector) {
  setTimeout(() => document.querySelector(selector)?.focus(), 400);
}

function isTyping(e) {
  return !!e.target.closest("input, textarea, select, [contenteditable]");
}

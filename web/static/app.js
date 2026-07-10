/* ============================================================
   智慧分身 · 前端交互层
   保持原生架构 · GSAP 动效 · 墨韵档案设计系统
   ============================================================ */

const API_BASE = "/api/v1";

const state = {
  skills: [],
  tools: [],
};

const titles = {
  chat: { title: "Chat 中枢", sub: "本地优先 · 记忆检索 · Skill 调度", index: "01" },
  recordings: { title: "录音采集", sub: "原始音频仅本地 · 自动转写与提炼", index: "02" },
  memories: { title: "记忆仓库", sub: "脱敏结构化卡片 · 按时间倒序", index: "03" },
  story: { title: "今日故事", sub: "真实锚点 + 文学虚构 · 基于今日记忆", index: "04" },
  skills: { title: "Skill Registry", sub: "场景能力配置接入 · 不写进核心代码", index: "05" },
  tools: { title: "MCP 工具", sub: "默认关闭 · 需权限与审计策略", index: "06" },
  trust: { title: "授权与凭证", sub: "Token 授权 · 本地哈希凭证", index: "07" },
  settings: { title: "设置", sub: "隐私策略 · 模型配置 · 数据管理", index: "08" },
  audit: { title: "审计日志", sub: "记忆 · Skill · 工具 · 权限 · 凭证", index: "09" },
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
  bindNavigation();
  bindForms();
  restoreApiKey();
  initHoverInteractions();
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
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      const currentPanel = document.querySelector(".tab-panel.is-active");
      const targetPanel = document.querySelector(`#tab-${tab}`);
      if (currentPanel === targetPanel) return;

      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.toggle("is-active", item === button);
      });

      const info = titles[tab] || { title: "智慧分身", sub: "", index: "—" };
      elements.viewTitle.textContent = info.title;
      elements.viewSub.textContent = info.sub;
      elements.viewIndex.textContent = info.index;

      gsapAnim.navActivate(button);
      gsapAnim.panelTransition(currentPanel, targetPanel);

      if (tab === "audit") loadAudit();
      if (tab === "recordings") loadRecordings();
    });
  });
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
async function apiFetch(path, options = {}) {
  setRequestStatus("请求中");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const apiKey = elements.apiKey.value.trim();
  if (apiKey) headers["x-api-key"] = apiKey;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const requestId = response.headers.get("x-request-id");
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
    const response = await fetch("/health");
    const data = await response.json();
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

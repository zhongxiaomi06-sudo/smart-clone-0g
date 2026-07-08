const API_BASE = "/api/v1";

const state = {
  skills: [],
  tools: [],
};

const titles = {
  chat: "Chat 中枢",
  recordings: "录音采集",
  memories: "记忆仓库",
  skills: "Skill Registry",
  tools: "MCP 工具",
  trust: "授权与凭证",
  audit: "审计日志",
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
  refreshAll();
});

function cacheElements() {
  elements.toast = document.querySelector("#toast");
  elements.healthStatus = document.querySelector("#health-status");
  elements.requestStatus = document.querySelector("#request-status");
  elements.viewTitle = document.querySelector("#view-title");
  elements.apiKey = document.querySelector("#api-key");
  elements.chatSkill = document.querySelector("#chat-skill");
  elements.recordToggle = document.querySelector("#record-toggle");
  elements.recordUpload = document.querySelector("#record-upload");
  elements.recordStatus = document.querySelector("#record-status");
  elements.recordTimer = document.querySelector("#record-timer");
  elements.recordPreview = document.querySelector("#record-preview");
  elements.recorderHint = document.querySelector("#recorder-hint");
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const tab = button.dataset.tab;
      document.querySelectorAll(".nav-item").forEach((item) => {
        item.classList.toggle("is-active", item === button);
      });
      document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === `tab-${tab}`);
      });
      elements.viewTitle.textContent = titles[tab] || "智慧分身";
      if (tab === "audit") {
        loadAudit();
      }
      if (tab === "recordings") {
        loadRecordings();
      }
    });
  });
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

  if (elements.recordToggle) {
    elements.recordToggle.addEventListener("click", toggleRecording);
  }
  if (elements.recordUpload) {
    elements.recordUpload.addEventListener("click", uploadCapturedRecording);
  }
  const uploadForm = document.querySelector("#recording-upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", submitRecordingFile);
  }
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
  ]);
}

async function apiFetch(path, options = {}) {
  setRequestStatus("请求中");
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const apiKey = elements.apiKey.value.trim();
  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
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
    elements.healthStatus.textContent = data.status === "ok" ? "服务正常" : "服务异常";
  } catch (error) {
    elements.healthStatus.textContent = "服务异常";
  }
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

async function submitChat(event) {
  event.preventDefault();
  const payload = {
    message: document.querySelector("#chat-message").value.trim(),
    skill_name: valueOrNull(document.querySelector("#chat-skill").value),
    permission_token: valueOrNull(document.querySelector("#chat-token").value),
    user_confirmed: document.querySelector("#chat-confirmed").checked,
    limit: 8,
  };
  try {
    const data = await apiFetch("/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderChatResult(data);
    await Promise.allSettled([loadAudit(), loadCredentials()]);
  } catch (error) {
    renderText("#chat-result", error.message, true);
  }
}

async function submitMemory(event) {
  event.preventDefault();
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
    await apiFetch("/memories", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    event.target.reset();
    showToast("记忆已写入。");
    await Promise.allSettled([loadMemories(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

async function submitPermission(event) {
  event.preventDefault();
  const payload = {
    target: document.querySelector("#permission-target").value.trim(),
    scope: splitList(document.querySelector("#permission-scope").value),
  };
  try {
    const data = await apiFetch("/permissions/grants", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderText("#permission-result", `Token: ${data.id}`);
    document.querySelector("#chat-token").value = data.id;
    showToast("授权已创建。");
    await loadAudit();
  } catch (error) {
    renderText("#permission-result", error.message, true);
  }
}

async function submitCredential(event) {
  event.preventDefault();
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
    await apiFetch("/credentials/hash", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    event.target.reset();
    document.querySelector("#credential-type").value = "memory";
    showToast("本地哈希凭证已生成。");
    await Promise.allSettled([loadCredentials(), loadAudit()]);
  } catch (error) {
    showToast(error.message);
  }
}

function renderSkillSelect(skills) {
  elements.chatSkill.innerHTML = '<option value="">自动判断</option>';
  skills.forEach((skill) => {
    const option = document.createElement("option");
    option.value = skill.name;
    option.textContent = skill.display_name;
    elements.chatSkill.append(option);
  });
}

function renderChatResult(data) {
  const result = document.querySelector("#chat-result");
  const citations = data.citations?.map((item) => `- ${item.source_id}: ${item.summary || ""}`);
  const skill = data.skill_result
    ? `\n\nSkill 状态：${data.skill_result.status}\n审计 ID：${data.skill_result.audit_id || "无"}`
    : "";
  result.classList.remove("empty-state");
  result.textContent = `${data.answer}${skill}\n\n引用：\n${citations?.join("\n") || "无"}`;
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
    item.innerHTML = `
      <header>
        <h4>${escapeHtml(memory.time_range || "未标注时间")}</h4>
        <span class="meta-line">${escapeHtml(memory.id)}</span>
      </header>
      <p>${escapeHtml(memory.event_summary)}</p>
      ${memory.insight ? `<p class="muted-text">${escapeHtml(memory.insight)}</p>` : ""}
      <div class="tag-row">${renderTags(memory.tags || [])}${renderTags(memory.personality_signals || [])}</div>
    `;
    target.append(item);
  });
}

function renderSkills(skills) {
  const rows = skills.map((skill) => `
    <tr>
      <td><strong>${escapeHtml(skill.display_name)}</strong><div class="meta-line">${escapeHtml(skill.name)}</div></td>
      <td>${escapeHtml(skill.description)}</td>
      <td>${renderTags(skill.permissions || [])}</td>
      <td>${renderTags(skill.triggers || [])}</td>
    </tr>
  `);
  renderTable("#skill-list", ["名称", "说明", "权限", "触发词"], rows, "暂无 Skill。");
}

function renderTools(tools) {
  const rows = tools.map((tool) => `
    <tr>
      <td><strong>${escapeHtml(tool.display_name)}</strong><div class="meta-line">${escapeHtml(tool.name)}</div></td>
      <td>${escapeHtml(tool.description)}</td>
      <td>${tool.enabled ? "已启用" : "已关闭"}</td>
      <td>${renderTags(tool.permissions || [])}</td>
    </tr>
  `);
  renderTable("#tool-list", ["名称", "说明", "状态", "权限"], rows, "暂无工具。");
}

function renderAudit(events) {
  const target = document.querySelector("#audit-list");
  target.innerHTML = "";
  if (!events.length) {
    renderEmpty("#audit-list", "暂无审计日志。");
    return;
  }
  events.forEach((event) => {
    const item = document.createElement("article");
    item.className = "list-item";
    item.innerHTML = `
      <header>
        <h4>${escapeHtml(event.event_type)}</h4>
        <span class="meta-line">${escapeHtml(event.created_at)}</span>
      </header>
      <div class="meta-line">target=${escapeHtml(event.target)} · id=${escapeHtml(event.id)}</div>
      <pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>
    `;
    target.append(item);
  });
}

function renderCredentials(credentials) {
  const target = document.querySelector("#credential-list");
  target.innerHTML = "";
  if (!credentials.length) {
    renderEmpty("#credential-list", "暂无凭证。");
    return;
  }
  credentials.forEach((credential) => {
    const item = document.createElement("article");
    item.className = "list-item";
    item.innerHTML = `
      <header>
        <h4>${escapeHtml(credential.subject_type)} / ${escapeHtml(credential.subject_id)}</h4>
        <span class="meta-line">${escapeHtml(credential.anchor_status)}</span>
      </header>
      <div class="meta-line">${escapeHtml(credential.digest)}</div>
    `;
    target.append(item);
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
      <thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
      <tbody>${rows.join("")}</tbody>
    </table>
  `;
}

function renderEmpty(selector, text) {
  const target = document.querySelector(selector);
  target.innerHTML = `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function renderText(selector, text, isError = false) {
  const target = document.querySelector(selector);
  target.classList.toggle("empty-state", false);
  target.style.color = isError ? "var(--danger)" : "inherit";
  target.textContent = text;
}

function renderTags(values) {
  return values.map((value) => `<span class="tag">${escapeHtml(value)}</span>`).join("");
}

function splitList(value) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
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
  elements.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.remove("is-visible");
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

// ---- 录音采集与全天语音记忆存储 ----
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
    showToast("麦克风授权失败:" + error.message);
    return;
  }
  recorder.chunks = [];
  recorder.blob = null;
  const mimeType = pickSupportedMimeType();
  recorder.mediaRecorder = new MediaRecorder(recorder.stream, mimeType ? { mimeType } : undefined);
  recorder.mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data && event.data.size > 0) {
      recorder.chunks.push(event.data);
    }
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
  elements.recordToggle.textContent = "停止录音";
  elements.recordUpload.disabled = true;
  elements.recordPreview.hidden = true;
  setRecordStatus("录音中", true);
  startTimer();
  elements.recorderHint.textContent = "正在录音。再次点击按钮可停止,然后上传转写。";
}

function pickSupportedMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
    return "";
  }
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
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
  elements.recordStatus.classList.toggle("muted", !active);
}

async function uploadCapturedRecording() {
  if (!recorder.blob) {
    showToast("没有可上传的录音。");
    return;
  }
  const duration = (Date.now() - recorder.startedAt) / 1000;
  const file = new File([recorder.blob], `recording-${Date.now()}.webm`, {
    type: recorder.blob.type,
  });
  await uploadRecordingFile(file, duration);
  recorder.blob = null;
  recorder.chunks = [];
  elements.recordUpload.disabled = true;
  elements.recordPreview.hidden = true;
  elements.recordToggle.textContent = "开始录音";
  elements.recorderHint.textContent = "点击「开始录音」授权麦克风。全天可分段录制多次,每段会独立转写并入库。";
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
    if (apiKey) {
      headers["x-api-key"] = apiKey;
    }
    const response = await fetch(`${API_BASE}/recordings`, {
      method: "POST",
      headers,
      body: formData,
    });
    const requestId = response.headers.get("x-request-id");
    setRequestStatus(requestId ? `请求 ${requestId.slice(0, 8)}` : "完成");
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      throw new Error(data?.error?.message || `上传失败:${response.status}`);
    }
    showToast("录音已上传,转写与提炼已完成。");
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
  if (!confirm("确认删除该录音?原始音频与转写记录将被移除(已生成的记忆卡片保留)。")) {
    return;
  }
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
    renderEmpty("#recording-list", "暂无录音。点击左侧「录音采集」开始记录一天。");
    return;
  }
  recordings.forEach((recording) => {
    const item = document.createElement("article");
    item.className = "list-item recording-item";
    const status = recording.transcript_status || "pending";
    const statusText = {
      pending: "待转写",
      running: "转写中",
      completed: "已转写",
      failed: "转写失败",
    }[status] || status;
    const transcriptBlock = recording.transcript
      ? `<details class="recording-transcript"><summary>转写文本</summary><p>${escapeHtml(recording.transcript)}</p></details>`
      : "";
    const memoryIds = (recording.extracted_memory_ids || [])
      .map((id) => `<span class="tag">${escapeHtml(id)}</span>`)
      .join("");
    item.innerHTML = `
      <header>
        <h4>${escapeHtml(recording.file_name)}</h4>
        <span class="meta-line">${escapeHtml(recording.recorded_at)} · ${formatBytes(recording.size_bytes)}</span>
      </header>
      <div class="tag-row">
        <span class="status-pill ${status === "completed" ? "" : "muted"}">${escapeHtml(statusText)}</span>
        ${recording.transcript_provider ? `<span class="tag">${escapeHtml(recording.transcript_provider)}</span>` : ""}
      </div>
      ${transcriptBlock}
      ${recording.transcript_error ? `<p class="muted-text">错误:${escapeHtml(recording.transcript_error)}</p>` : ""}
      ${memoryIds ? `<div class="meta-line">已提炼记忆:</div><div class="tag-row">${memoryIds}</div>` : ""}
      <div class="recording-actions">
        <button class="button button-secondary" type="button" data-action="transcribe">重新转写</button>
        <button class="button button-secondary" type="button" data-action="extract">提炼记忆</button>
        <button class="button button-danger" type="button" data-action="delete">删除</button>
      </div>
    `;
    item.querySelector('[data-action="transcribe"]').addEventListener("click", () => {
      transcribeRecording(recording.id);
    });
    item.querySelector('[data-action="extract"]').addEventListener("click", () => {
      extractRecordingMemories(recording.id);
    });
    item.querySelector('[data-action="delete"]').addEventListener("click", () => {
      deleteRecording(recording.id);
    });
    target.append(item);
  });
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


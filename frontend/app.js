(() => {
  "use strict";

  const STORAGE = {
    session: "autocraft_session",
    apiKey: "autocraft_api_key",
    apiBase: "autocraft_api_base",
    theme: "autocraft_theme",
    view: "autocraft_view",
  };

  const VIEW_META = {
    chat: {
      eyebrow: "Build workspace",
      title: "Agent chat",
      description: "Turn an idea into an actionable software plan.",
    },
    team: {
      eyebrow: "Multi-agent workflow",
      title: "Agent team",
      description: "Combine specialist agents into a focused delivery pipeline.",
    },
    test: {
      eyebrow: "Quality workspace",
      title: "Test lab",
      description: "Plan and execute safe pytest runs before changes ship.",
    },
    plugins: {
      eyebrow: "Capability catalog",
      title: "Plugins",
      description: "Extend AutoCraft with focused tools for your workflow.",
    },
    settings: {
      eyebrow: "Workspace controls",
      title: "Settings",
      description: "Manage appearance, API access, and runtime diagnostics.",
    },
  };

  const state = {
    sessionId: localStorage.getItem(STORAGE.session) || null,
    apiKey: localStorage.getItem(STORAGE.apiKey) || "",
    apiBase: (localStorage.getItem(STORAGE.apiBase) || "").replace(/\/$/, ""),
    theme: localStorage.getItem(STORAGE.theme) || "system",
    currentView: "chat",
    health: null,
    plugins: [],
    roles: [],
    chatAbort: null,
    pluginsLoaded: false,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  function apiUrl(path) {
    return `${state.apiBase || ""}${path}`;
  }

  function headers() {
    const result = { "Content-Type": "application/json" };
    if (state.apiKey) result["X-API-Key"] = state.apiKey;
    return result;
  }

  function formatError(payload, fallback) {
    if (!payload) return fallback || "Request failed";
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
    }
    if (detail != null) return JSON.stringify(detail);
    return fallback || "Request failed";
  }

  async function api(path, options = {}) {
    const response = await fetch(apiUrl(path), {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(formatError(payload, response.statusText));
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function makeIcon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    use.setAttribute("href", `#icon-${name}`);
    svg.appendChild(use);
    return svg;
  }

  function prettyName(value) {
    return String(value || "")
      .replace(/[_-]+/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function initials(value) {
    const parts = prettyName(value).split(/\s+/).filter(Boolean);
    return (parts.length > 1 ? parts[0][0] + parts[1][0] : parts[0]?.slice(0, 2) || "AC").toUpperCase();
  }

  function currentTime() {
    return new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
  }

  async function copyText(text) {
    if (!text) return false;
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const copied = document.execCommand("copy");
      area.remove();
      return copied;
    }
  }

  function toast(message, type = "success") {
    const item = document.createElement("div");
    item.className = `toast${type === "error" ? " error" : ""}`;
    item.textContent = message;
    $("#toastRegion").appendChild(item);
    window.setTimeout(() => {
      item.classList.add("leaving");
      window.setTimeout(() => item.remove(), 220);
    }, 3200);
  }

  function scrollToEnd(container) {
    window.requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });
  }

  function addMessage(container, text, role = "bot", roleTag = "", options = {}) {
    const root = document.createElement("article");
    root.className = `msg ${role}`;

    if (role === "system") {
      const card = document.createElement("div");
      card.className = "message-card";
      card.textContent = text;
      root.appendChild(card);
      container.appendChild(root);
      scrollToEnd(container);
      return { root, body: card, copyButton: null };
    }

    const displayRole = role === "user" ? "You" : roleTag ? prettyName(roleTag) : "AutoCraft";
    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = role === "user" ? "You" : initials(displayRole);

    const content = document.createElement("div");
    content.className = "msg-content";
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const author = document.createElement("strong");
    author.textContent = displayRole;
    meta.appendChild(author);

    if (roleTag) {
      const tag = document.createElement("span");
      tag.className = "role-tag";
      tag.textContent = roleTag;
      meta.appendChild(tag);
    }

    const time = document.createElement("time");
    time.textContent = currentTime();
    meta.appendChild(time);

    const card = document.createElement("div");
    card.className = "message-card";
    const body = document.createElement("div");
    body.className = "message-body";
    body.textContent = text;
    if (options.pending) body.classList.add("typing-cursor");
    card.appendChild(body);

    content.append(meta, card);
    let copyButton = null;
    if (role !== "user") {
      copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.className = "copy-message";
      copyButton.append(makeIcon("copy"), document.createTextNode("Copy"));
      copyButton.hidden = Boolean(options.pending);
      copyButton.addEventListener("click", async () => {
        const copied = await copyText(body.textContent);
        toast(copied ? "Response copied" : "Could not copy response", copied ? "success" : "error");
      });
      content.appendChild(copyButton);
    }

    root.append(avatar, content);
    container.appendChild(root);
    scrollToEnd(container);
    return { root, body, copyButton };
  }

  function updateMessage(handle, text, { streaming = false, error = false } = {}) {
    handle.body.textContent = text;
    handle.body.classList.toggle("typing-cursor", streaming);
    handle.root.classList.toggle("error", error);
    if (handle.copyButton) handle.copyButton.hidden = streaming || !text;
    scrollToEnd(handle.root.parentElement);
  }

  function setButtonLoading(button, loading, activeLabel) {
    const label = $("span", button);
    if (label && !button.dataset.defaultLabel) button.dataset.defaultLabel = label.textContent;
    button.disabled = loading;
    button.classList.toggle("loading", loading);
    if (label) label.textContent = loading ? activeLabel : button.dataset.defaultLabel;
  }

  /* Theme */
  const colorScheme = window.matchMedia("(prefers-color-scheme: light)");

  function resolvedTheme(choice = state.theme) {
    return choice === "system" ? (colorScheme.matches ? "light" : "dark") : choice;
  }

  function applyTheme(choice, persist = true) {
    state.theme = ["system", "dark", "light"].includes(choice) ? choice : "system";
    const resolved = resolvedTheme();
    document.documentElement.dataset.theme = resolved;
    const themeSelect = $("#themeSelect");
    if (themeSelect) themeSelect.value = state.theme;
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.content = resolved === "light" ? "#f5f7fb" : "#090c12";
    $("#themeToggle").setAttribute(
      "aria-label",
      resolved === "dark" ? "Switch to light theme" : "Switch to dark theme"
    );
    if (persist) localStorage.setItem(STORAGE.theme, state.theme);
  }

  colorScheme.addEventListener?.("change", () => {
    if (state.theme === "system") applyTheme("system", false);
  });

  $("#themeToggle").addEventListener("click", () => {
    applyTheme(resolvedTheme() === "dark" ? "light" : "dark");
  });

  /* Navigation and mobile menu */
  function closeSidebar() {
    $("#sidebar").classList.remove("open");
    $("#mobileOverlay").hidden = true;
    $("#mobileMenuBtn").setAttribute("aria-expanded", "false");
  }

  function openSidebar() {
    $("#sidebar").classList.add("open");
    $("#mobileOverlay").hidden = false;
    $("#mobileMenuBtn").setAttribute("aria-expanded", "true");
  }

  function showView(name, updateHash = true) {
    if (!VIEW_META[name]) name = "chat";
    state.currentView = name;
    localStorage.setItem(STORAGE.view, name);

    $$(".view").forEach((view) => {
      view.classList.toggle("active", view.dataset.view === name);
    });
    $$(".nav-item").forEach((button) => {
      const active = button.dataset.view === name;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });

    const meta = VIEW_META[name];
    $("#viewEyebrow").textContent = meta.eyebrow;
    $("#viewTitle").textContent = meta.title;
    $("#viewDescription").textContent = meta.description;
    document.title = `${meta.title} · AutoCraft`;

    if (updateHash && window.location.hash !== `#${name}`) {
      history.replaceState(null, "", `#${name}`);
    }
    if (name === "plugins" && !state.pluginsLoaded) loadPlugins();
    if (name === "team" && !state.roles.length) loadTeamRoles();
    closeSidebar();
  }

  $("#nav").addEventListener("click", (event) => {
    const button = event.target.closest(".nav-item");
    if (button) showView(button.dataset.view);
  });
  $("#mobileMenuBtn").addEventListener("click", openSidebar);
  $("#sidebarClose").addEventListener("click", closeSidebar);
  $("#mobileOverlay").addEventListener("click", closeSidebar);
  $("#connectionBadge").addEventListener("click", () => showView("settings"));

  window.addEventListener("hashchange", () => {
    const requested = window.location.hash.slice(1);
    if (VIEW_META[requested] && requested !== state.currentView) showView(requested, false);
  });

  /* Connection and provider state */
  function updateConnection(status, label, health = null) {
    $("#runtimeCard").dataset.status = status;
    $("#connectionBadge").dataset.status = status;
    $("#statusPill").textContent = label;
    $("#connectionText").textContent = status === "online" ? "Connected" : status === "offline" ? "Offline" : "Connecting";

    if (health) {
      $("#sidebarProvider").textContent = `${prettyName(health.provider || "unknown")} provider`;
      $("#healthStatusValue").textContent = prettyName(health.status || "unknown");
      $("#healthProviderValue").textContent = prettyName(health.provider || "unknown");
      $("#healthSessionsValue").textContent = String(health.sessions ?? "—");
      $("#healthAuthValue").textContent = health.auth_required ? "Required" : "Open";
    } else if (status === "offline") {
      $("#sidebarProvider").textContent = "Server unavailable";
      $("#healthStatusValue").textContent = "Offline";
    }
  }

  async function refreshHealth({ writeOutput = false } = {}) {
    try {
      const response = await fetch(apiUrl("/health"), { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(formatError(payload, response.statusText));
      state.health = payload;
      updateConnection("online", `${prettyName(payload.status)} · ${prettyName(payload.provider)}`, payload);
      if (writeOutput) $("#healthOut").textContent = JSON.stringify(payload, null, 2);
      return payload;
    } catch (error) {
      state.health = null;
      updateConnection("offline", "Runtime offline");
      if (writeOutput) $("#healthOut").textContent = `Connection failed\n${error.message || error}`;
      return null;
    }
  }

  async function loadProviders() {
    try {
      const payload = await api("/api/providers");
      for (const selector of ["#chatProvider", "#teamProvider", "#testProvider"]) {
        const select = $(selector);
        const selected = select.value;
        select.replaceChildren();
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = payload.default
          ? `Default · ${prettyName(payload.default)}`
          : "Default provider";
        select.appendChild(defaultOption);
        for (const provider of payload.providers || []) {
          const option = document.createElement("option");
          option.value = provider;
          option.textContent = prettyName(provider);
          select.appendChild(option);
        }
        select.value = [...select.options].some((option) => option.value === selected) ? selected : "";
      }
    } catch {
      // The settings view explains auth and connection failures when requested.
    }
  }

  /* Sessions and chat */
  const chatLog = $("#chatLog");
  const chatInput = $("#chatInput");
  const chatForm = $("#chatForm");
  const chatSend = $("#chatSend");

  function setSession(id) {
    state.sessionId = id || null;
    if (state.sessionId) localStorage.setItem(STORAGE.session, state.sessionId);
    else localStorage.removeItem(STORAGE.session);

    const shortId = state.sessionId ? state.sessionId.slice(0, 8) : "";
    $("#sessionPill").textContent = state.sessionId ? `Session ${shortId}…` : "No active session";
    $("#chatSessionLabel").textContent = state.sessionId ? `Session ${shortId}…` : "Fresh workspace";
  }

  function setChatEmpty(empty) {
    $("#chatEmpty").classList.toggle("hidden", !empty);
  }

  function resetSession() {
    if (state.chatAbort) state.chatAbort.abort();
    setSession(null);
    chatLog.replaceChildren();
    chatInput.value = "";
    chatInput.style.height = "auto";
    setChatEmpty(true);
    showView("chat");
    chatInput.focus();
  }

  async function restoreSession() {
    if (!state.sessionId) return;
    const restoringId = state.sessionId;
    try {
      const payload = await api(`/api/session/${restoringId}`);
      const history = payload.history || [];
      if (!history.length) return;
      // Do not overwrite a new session or messages created while history loaded.
      if (state.sessionId !== restoringId || chatLog.childElementCount) return;
      chatLog.replaceChildren();
      setChatEmpty(false);
      for (const entry of history) {
        addMessage(chatLog, entry.content || "", entry.role === "user" ? "user" : "bot");
      }
    } catch (error) {
      if (error.status === 400 || error.status === 404) setSession(null);
      toast(`Previous session could not be restored: ${error.message}`, "error");
    }
  }

  function parseSseEvent(block) {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return null;
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  async function streamChat(body, signal, onToken) {
    const response = await fetch(apiUrl("/api/chat/stream"), {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(formatError(payload, response.statusText));
    }

    if (!response.body) throw new Error("Streaming is not supported by this browser");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completed = null;

    const consume = (block) => {
      const event = parseSseEvent(block);
      if (!event) return;
      if (event.error) throw new Error(event.error);
      if (typeof event.token === "string") onToken(event.token);
      if (event.done) completed = event;
    };

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r\n/g, "\n");
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      blocks.forEach(consume);
      if (done) break;
    }
    if (buffer.trim()) consume(buffer);
    return completed || {};
  }

  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = `${Math.min(chatInput.scrollHeight, 180)}px`;
  });

  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!state.chatAbort) chatForm.requestSubmit();
    }
  });

  chatSend.addEventListener("click", (event) => {
    if (state.chatAbort) {
      event.preventDefault();
      state.chatAbort.abort();
    }
  });

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.chatAbort) return;
    const message = chatInput.value.trim();
    if (!message) return;

    setChatEmpty(false);
    addMessage(chatLog, message, "user");
    chatInput.value = "";
    chatInput.style.height = "auto";
    const reply = addMessage(chatLog, "Thinking…", "bot", "", { pending: true });
    let received = "";
    const controller = new AbortController();
    state.chatAbort = controller;
    chatSend.classList.add("streaming");
    chatSend.setAttribute("aria-label", "Stop response");

    try {
      const body = { message, session_id: state.sessionId };
      const provider = $("#chatProvider").value;
      if (provider) body.provider = provider;
      const completed = await streamChat(body, controller.signal, (token) => {
        received += token;
        updateMessage(reply, received, { streaming: true });
      });
      const finalText = received || completed.response || "No response returned.";
      updateMessage(reply, finalText);
      if (completed.session_id) setSession(completed.session_id);
    } catch (error) {
      if (error.name === "AbortError") {
        updateMessage(reply, received ? `${received}\n\nResponse stopped.` : "Response stopped.");
      } else {
        updateMessage(reply, `AutoCraft could not complete this request.\n${error.message}`, { error: true });
        toast(error.message || "Chat request failed", "error");
      }
    } finally {
      state.chatAbort = null;
      chatSend.classList.remove("streaming");
      chatSend.setAttribute("aria-label", "Send message");
      chatInput.focus();
    }
  });

  $$(".prompt-card").forEach((button) => {
    button.addEventListener("click", () => {
      chatInput.value = button.dataset.prompt || "";
      chatInput.dispatchEvent(new Event("input"));
      chatInput.focus();
    });
  });

  $("#newSessionBtn").addEventListener("click", () => {
    resetSession();
    toast("New build session ready");
  });

  $("#clearChatBtn").addEventListener("click", async () => {
    try {
      if (state.sessionId) {
        await api(`/api/session/${state.sessionId}/clear`, { method: "POST" });
      }
      chatLog.replaceChildren();
      setChatEmpty(true);
      toast("Chat history cleared");
    } catch (error) {
      toast(`Could not clear the session: ${error.message}`, "error");
    }
  });

  /* Team workspace */
  function pipelineRoles() {
    return $("#teamPipeline").value.split(",").map((role) => role.trim()).filter(Boolean);
  }

  function updatePipelinePreview() {
    const preview = $("#pipelinePreview");
    const roles = pipelineRoles();
    preview.replaceChildren();
    roles.forEach((role, index) => {
      const node = document.createElement("span");
      node.className = "pipeline-node";
      const number = document.createElement("b");
      number.textContent = String(index + 1).padStart(2, "0");
      node.append(number, document.createTextNode(prettyName(role)));
      preview.appendChild(node);
      if (index < roles.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "pipeline-arrow";
        arrow.textContent = "→";
        preview.appendChild(arrow);
      }
    });
    if (!roles.length) {
      const empty = document.createElement("span");
      empty.className = "pipeline-arrow";
      empty.textContent = "Add at least one role";
      preview.appendChild(empty);
    }
  }

  async function loadTeamRoles() {
    try {
      const payload = await api("/api/team/roles");
      state.roles = payload.roles || [];
      $("#roleCount").textContent = String(state.roles.length || 3);
      if (!$("#teamPipeline").value.trim() && payload.default_pipeline?.length) {
        $("#teamPipeline").value = payload.default_pipeline.join(", ");
      }
      updatePipelinePreview();
    } catch {
      updatePipelinePreview();
    }
  }

  $("#teamPipeline").addEventListener("input", updatePipelinePreview);

  $("#teamForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const goal = $("#teamGoal").value.trim();
    const pipeline = pipelineRoles();
    if (!goal || !pipeline.length) {
      toast("Add a goal and at least one pipeline role", "error");
      return;
    }

    const button = $("#teamRun");
    const log = $("#teamLog");
    log.replaceChildren();
    $("#teamEmpty").classList.add("hidden");
    $("#teamActivity").classList.add("active");
    setButtonLoading(button, true, "Team working…");

    try {
      const body = { goal, pipeline };
      const provider = $("#teamProvider").value;
      if (provider) body.provider = provider;
      const payload = await api("/api/team/run", {
        method: "POST",
        body: JSON.stringify(body),
      });
      for (const step of payload.steps || []) {
        addMessage(log, step.output || "No output returned.", "bot", step.role || "agent");
      }
      const lastOutput = payload.steps?.at(-1)?.output;
      if (payload.final && payload.final !== lastOutput) {
        addMessage(log, payload.final, "bot", "final");
      }
      if (!(payload.steps || []).length && !payload.final) {
        addMessage(log, "The team completed without returning output.", "system");
      }
      toast("Agent team completed its pipeline");
    } catch (error) {
      addMessage(log, `Team run failed: ${error.message}`, "system");
      toast(error.message || "Team run failed", "error");
    } finally {
      $("#teamActivity").classList.remove("active");
      setButtonLoading(button, false);
    }
  });

  /* Test lab */
  function formatTestResult(payload) {
    const sections = [];
    if (payload.plan) sections.push(`TEST PLAN\n${payload.plan}`);
    if (payload.command) sections.push(`COMMAND\n${payload.command}`);
    if (payload.command_output) sections.push(`OUTPUT\n${payload.command_output}`);
    if (payload.notes?.length) sections.push(`NOTES\n${payload.notes.join("\n")}`);
    return sections.join("\n\n") || "The test agent returned no details.";
  }

  $("#testForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const goal = $("#testGoal").value.trim();
    if (!goal) return;
    const button = $("#testRun");
    const log = $("#testLog");
    const badge = $("#testResultBadge");
    log.replaceChildren();
    $("#testEmpty").classList.add("hidden");
    badge.className = "result-badge neutral";
    badge.textContent = "Running";
    setButtonLoading(button, true, "Testing…");

    try {
      const body = { goal, execute: $("#testExecute").checked };
      const provider = $("#testProvider").value;
      if (provider) body.provider = provider;
      const payload = await api("/api/test/run", {
        method: "POST",
        body: JSON.stringify(body),
      });
      addMessage(log, formatTestResult(payload), "bot", "test report");
      if (payload.passed === true) {
        badge.className = "result-badge pass";
        badge.textContent = "Passed";
      } else if (payload.passed === false) {
        badge.className = "result-badge fail";
        badge.textContent = "Failed";
      } else {
        badge.className = "result-badge neutral";
        badge.textContent = "Plan ready";
      }
      toast(payload.passed === false ? "Test run finished with failures" : "Test run completed", payload.passed === false ? "error" : "success");
    } catch (error) {
      addMessage(log, `Test agent failed: ${error.message}`, "system");
      badge.className = "result-badge fail";
      badge.textContent = "Error";
      toast(error.message || "Test run failed", "error");
    } finally {
      setButtonLoading(button, false);
    }
  });

  /* Plugin catalog */
  function pluginMatches(plugin) {
    const query = $("#pluginSearch").value.trim().toLowerCase();
    const filter = $("#pluginFilter").value;
    const searchable = [plugin.name, plugin.description, plugin.author, ...(plugin.tags || [])].join(" ").toLowerCase();
    const matchesQuery = !query || searchable.includes(query);
    const matchesFilter = filter === "all"
      || (filter === "installed" && plugin.installed)
      || (filter === "enabled" && plugin.enabled)
      || (filter === "available" && !plugin.installed);
    return matchesQuery && matchesFilter;
  }

  function createPluginCard(plugin) {
    const card = document.createElement("article");
    card.className = "plugin-card";

    const head = document.createElement("div");
    head.className = "plugin-card-head";
    const logo = document.createElement("span");
    logo.className = "plugin-logo";
    logo.textContent = initials(plugin.name);
    const pluginState = document.createElement("span");
    pluginState.className = `plugin-state${plugin.enabled ? " enabled" : ""}`;
    const dot = document.createElement("span");
    dot.className = "status-dot";
    pluginState.append(dot, document.createTextNode(plugin.enabled ? "Enabled" : plugin.installed ? "Installed" : "Available"));
    head.append(logo, pluginState);

    const title = document.createElement("h3");
    title.textContent = prettyName(plugin.name);
    const description = document.createElement("p");
    description.textContent = plugin.description || "No description provided.";

    const meta = document.createElement("div");
    meta.className = "plugin-meta";
    const version = document.createElement("span");
    version.className = "tag";
    version.textContent = `v${plugin.version || "?"}`;
    meta.appendChild(version);
    for (const pluginTag of plugin.tags || []) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = pluginTag;
      meta.appendChild(tag);
    }

    const footer = document.createElement("div");
    footer.className = "plugin-footer";
    const author = document.createElement("span");
    author.className = "plugin-author";
    author.textContent = `by ${plugin.author || "autocraft"}`;
    const actions = document.createElement("div");
    actions.className = "plugin-actions";
    const action = document.createElement("button");
    action.type = "button";
    action.className = `btn ${plugin.installed ? "ghost" : "primary"} sm`;
    action.textContent = !plugin.installed ? "Install" : plugin.enabled ? "Disable" : "Enable";
    action.addEventListener("click", async () => {
      const operation = !plugin.installed ? "install" : plugin.enabled ? "disable" : "enable";
      action.disabled = true;
      try {
        await api(`/api/plugins/${operation}`, {
          method: "POST",
          body: JSON.stringify({ name: plugin.name }),
        });
        toast(`${prettyName(plugin.name)} ${operation === "disable" ? "disabled" : operation === "enable" ? "enabled" : "installed"}`);
        await loadPlugins();
      } catch (error) {
        toast(error.message || `Could not ${operation} plugin`, "error");
        action.disabled = false;
      }
    });
    actions.appendChild(action);
    footer.append(author, actions);
    card.append(head, title, description, meta, footer);
    return card;
  }

  function renderPlugins() {
    const grid = $("#pluginGrid");
    const filtered = state.plugins.filter(pluginMatches);
    grid.replaceChildren(...filtered.map(createPluginCard));
    $("#pluginCount").textContent = `${filtered.length} of ${state.plugins.length} plugin${state.plugins.length === 1 ? "" : "s"}`;
    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.className = "catalog-empty surface";
      empty.textContent = state.plugins.length ? "No plugins match this search." : "No plugins are available in this catalog.";
      grid.appendChild(empty);
    }
  }

  function renderPluginSkeletons() {
    const grid = $("#pluginGrid");
    grid.replaceChildren();
    for (let index = 0; index < 3; index += 1) {
      const skeleton = document.createElement("div");
      skeleton.className = "plugin-card skeleton";
      grid.appendChild(skeleton);
    }
  }

  async function loadPlugins() {
    state.pluginsLoaded = true;
    renderPluginSkeletons();
    $("#pluginCount").textContent = "Loading catalog…";
    try {
      const payload = await api("/api/plugins");
      state.plugins = payload.plugins || [];
      renderPlugins();
    } catch (error) {
      state.plugins = [];
      renderPlugins();
      $("#pluginCount").textContent = "Catalog unavailable";
      toast(error.message || "Could not load plugins", "error");
    }
  }

  $("#pluginSearch").addEventListener("input", renderPlugins);
  $("#pluginFilter").addEventListener("change", renderPlugins);
  $("#refreshPlugins").addEventListener("click", loadPlugins);

  /* Settings */
  $("#apiKeyInput").value = state.apiKey;
  $("#apiBaseInput").value = state.apiBase;
  $("#themeSelect").value = state.theme;

  $("#themeSelect").addEventListener("change", (event) => applyTheme(event.target.value));

  $("#toggleApiKey").addEventListener("click", () => {
    const input = $("#apiKeyInput");
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    $("#toggleApiKey").setAttribute("aria-label", showing ? "Show API key" : "Hide API key");
  });

  $("#settingsForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.apiKey = $("#apiKeyInput").value.trim();
    state.apiBase = $("#apiBaseInput").value.trim().replace(/\/$/, "");
    if (state.apiKey) localStorage.setItem(STORAGE.apiKey, state.apiKey);
    else localStorage.removeItem(STORAGE.apiKey);
    if (state.apiBase) localStorage.setItem(STORAGE.apiBase, state.apiBase);
    else localStorage.removeItem(STORAGE.apiBase);
    applyTheme($("#themeSelect").value);
    const health = await refreshHealth({ writeOutput: true });
    loadProviders();
    if (state.sessionId && !chatLog.childElementCount) restoreSession();
    state.pluginsLoaded = false;
    toast(health ? "Settings saved and connection verified" : "Settings saved, but the server is offline", health ? "success" : "error");
  });

  $("#pingBtn").addEventListener("click", async () => {
    const button = $("#pingBtn");
    setButtonLoading(button, true, "Testing…");
    const health = await refreshHealth({ writeOutput: true });
    toast(health ? "Runtime is healthy" : "Runtime could not be reached", health ? "success" : "error");
    setButtonLoading(button, false);
  });

  $("#copyHealthBtn").addEventListener("click", async () => {
    const copied = await copyText($("#healthOut").textContent);
    toast(copied ? "Diagnostics copied" : "Could not copy diagnostics", copied ? "success" : "error");
  });

  /* Keyboard shortcuts */
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const editing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target.isContentEditable;

    if (event.key === "Escape") {
      closeSidebar();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      showView("chat");
      chatInput.focus();
      return;
    }
    if (!editing && /^[1-5]$/.test(event.key)) {
      const view = Object.keys(VIEW_META)[Number(event.key) - 1];
      showView(view);
      return;
    }
    if (!editing && event.key.toLowerCase() === "n") {
      resetSession();
      toast("New build session ready");
    }
  });

  /* Boot */
  applyTheme(state.theme, false);
  setSession(state.sessionId);
  updatePipelinePreview();
  const initialView = VIEW_META[window.location.hash.slice(1)]
    ? window.location.hash.slice(1)
    : VIEW_META[localStorage.getItem(STORAGE.view)]
      ? localStorage.getItem(STORAGE.view)
      : "chat";
  showView(initialView, false);
  refreshHealth();
  loadProviders();
  restoreSession();
})();

(() => {
  "use strict";

  const STORAGE = {
    session: "autocraft_session",
    apiKey: "autocraft_api_key",
    apiBase: "autocraft_api_base",
  };

  const state = {
    sessionId: localStorage.getItem(STORAGE.session) || null,
    apiKey: localStorage.getItem(STORAGE.apiKey) || "",
    apiBase: (localStorage.getItem(STORAGE.apiBase) || "").replace(/\/$/, ""),
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  function apiUrl(path) {
    const base = state.apiBase || "";
    return `${base}${path}`;
  }

  function headers() {
    const h = { "Content-Type": "application/json" };
    if (state.apiKey) h["X-API-Key"] = state.apiKey;
    return h;
  }

  function formatError(j, statusText) {
    if (!j) return statusText || "Request failed";
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
    if (d != null) return JSON.stringify(d);
    return statusText || "Request failed";
  }

  async function api(path, options = {}) {
    const r = await fetch(apiUrl(path), {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(formatError(j, r.statusText));
    return j;
  }

  function addMsg(container, text, role, roleTag) {
    const d = document.createElement("div");
    d.className = `msg ${role}`;
    if (roleTag) {
      const tag = document.createElement("div");
      tag.className = "role-tag";
      tag.textContent = roleTag;
      d.appendChild(tag);
    }
    const body = document.createElement("div");
    body.textContent = text;
    d.appendChild(body);
    container.appendChild(d);
    container.scrollTop = container.scrollHeight;
  }

  function setSession(id) {
    state.sessionId = id;
    if (id) localStorage.setItem(STORAGE.session, id);
    else localStorage.removeItem(STORAGE.session);
    $("#sessionPill").textContent = id
      ? `session ${id.slice(0, 8)}…`
      : "no session";
  }

  function setStatus(text) {
    $("#statusPill").textContent = text;
  }

  /* Navigation */
  function showView(name) {
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
    $$(".nav-item").forEach((b) =>
      b.classList.toggle("active", b.dataset.view === name)
    );
    if (name === "plugins") loadPlugins();
  }

  $("#nav").addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-item");
    if (btn) showView(btn.dataset.view);
  });

  /* Providers */
  async function loadProviders() {
    try {
      const j = await api("/api/providers");
      const selects = ["#chatProvider", "#teamProvider", "#testProvider"];
      for (const sel of selects) {
        const el = $(sel);
        const current = el.value;
        el.innerHTML = '<option value="">Default provider</option>';
        for (const p of j.providers || []) {
          const opt = document.createElement("option");
          opt.value = p;
          opt.textContent = p + (p === j.default ? " (server default)" : "");
          el.appendChild(opt);
        }
        el.value = current;
      }
    } catch {
      /* auth may block; ignore */
    }
  }

  /* Health */
  async function refreshHealth() {
    try {
      const j = await fetch(apiUrl("/health")).then((r) => r.json());
      setStatus(
        `${j.status} · ${j.provider}${j.auth_required ? " · auth" : ""}`
      );
      return j;
    } catch {
      setStatus("offline");
      return null;
    }
  }

  /* Chat */
  const chatLog = $("#chatLog");
  const chatForm = $("#chatForm");
  const chatInput = $("#chatInput");
  const chatSend = $("#chatSend");

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.requestSubmit();
    }
  });

  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
  });

  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    chatInput.value = "";
    chatInput.style.height = "auto";
    addMsg(chatLog, message, "user");
    chatSend.disabled = true;
    try {
      const body = { message, session_id: state.sessionId };
      const prov = $("#chatProvider").value;
      if (prov) body.provider = prov;
      const j = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSession(j.session_id);
      addMsg(chatLog, j.response, "bot");
    } catch (err) {
      addMsg(chatLog, "Error: " + err.message, "system");
    } finally {
      chatSend.disabled = false;
      chatInput.focus();
    }
  });

  $("#clearChatBtn").addEventListener("click", async () => {
    if (state.sessionId) {
      try {
        await api(`/api/session/${state.sessionId}/clear`, { method: "POST" });
      } catch {
        /* ignore */
      }
    }
    chatLog.innerHTML = "";
    addMsg(chatLog, "Session cleared.", "system");
  });

  /* Team */
  $("#teamForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const goal = $("#teamGoal").value.trim();
    if (!goal) return;
    const log = $("#teamLog");
    addMsg(log, goal, "user");
    const btn = $("#teamRun");
    btn.disabled = true;
    try {
      const body = { goal };
      const pipe = $("#teamPipeline").value.trim();
      if (pipe) {
        body.pipeline = pipe.split(",").map((s) => s.trim()).filter(Boolean);
      }
      const prov = $("#teamProvider").value;
      if (prov) body.provider = prov;
      const j = await api("/api/team/run", {
        method: "POST",
        body: JSON.stringify(body),
      });
      for (const s of j.steps || []) {
        addMsg(log, s.output, "bot", s.role);
      }
      if (j.final) addMsg(log, j.final, "bot", "final");
    } catch (err) {
      addMsg(log, "Team error: " + err.message, "system");
    } finally {
      btn.disabled = false;
    }
  });

  /* Test */
  $("#testForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const goal = $("#testGoal").value.trim();
    if (!goal) return;
    const log = $("#testLog");
    addMsg(log, goal, "user");
    const btn = $("#testRun");
    btn.disabled = true;
    try {
      const body = {
        goal,
        execute: $("#testExecute").checked,
      };
      const prov = $("#testProvider").value;
      if (prov) body.provider = prov;
      const j = await api("/api/test/run", {
        method: "POST",
        body: JSON.stringify(body),
      });
      let text = j.plan || "";
      if (j.command) text += `\n\nCommand: ${j.command}`;
      if (j.command_output) text += `\n${j.command_output}`;
      if (j.passed != null) text += `\nPassed: ${j.passed}`;
      if (j.notes && j.notes.length) text += `\nNotes: ${j.notes.join("; ")}`;
      addMsg(log, text.trim(), "bot");
    } catch (err) {
      addMsg(log, "Test error: " + err.message, "system");
    } finally {
      btn.disabled = false;
    }
  });

  /* Plugins */
  async function loadPlugins() {
    const grid = $("#pluginGrid");
    grid.innerHTML = '<p class="muted">Loading…</p>';
    try {
      const j = await api("/api/plugins");
      grid.innerHTML = "";
      for (const p of j.plugins || []) {
        const card = document.createElement("div");
        card.className = "plugin-card";
        card.innerHTML = `
          <h3>${escapeHtml(p.name)}</h3>
          <p>${escapeHtml(p.description || "")}</p>
          <div class="plugin-meta">
            <span class="tag">v${escapeHtml(p.version || "?")}</span>
            ${p.installed ? '<span class="tag on">installed</span>' : ""}
            ${p.enabled ? '<span class="tag on">enabled</span>' : ""}
            ${(p.tags || []).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
          </div>
          <div class="plugin-actions"></div>
        `;
        const actions = card.querySelector(".plugin-actions");
        if (!p.installed) {
          actions.appendChild(
            actionBtn("Install", async () => {
              await api("/api/plugins/install", {
                method: "POST",
                body: JSON.stringify({ name: p.name }),
              });
              loadPlugins();
            })
          );
        } else {
          if (p.enabled) {
            actions.appendChild(
              actionBtn("Disable", async () => {
                await api("/api/plugins/disable", {
                  method: "POST",
                  body: JSON.stringify({ name: p.name }),
                });
                loadPlugins();
              })
            );
          } else {
            actions.appendChild(
              actionBtn("Enable", async () => {
                await api("/api/plugins/enable", {
                  method: "POST",
                  body: JSON.stringify({ name: p.name }),
                });
                loadPlugins();
              })
            );
          }
        }
        grid.appendChild(card);
      }
      if (!(j.plugins || []).length) {
        grid.innerHTML = '<p class="muted">No plugins in marketplace.</p>';
      }
    } catch (err) {
      grid.innerHTML = `<p class="muted">Error: ${escapeHtml(err.message)}</p>`;
    }
  }

  function actionBtn(label, fn) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn ghost sm";
    b.textContent = label;
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await fn();
      } catch (err) {
        alert(err.message);
      } finally {
        b.disabled = false;
      }
    });
    return b;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  $("#refreshPlugins").addEventListener("click", loadPlugins);

  /* Settings */
  $("#apiKeyInput").value = state.apiKey;
  $("#apiBaseInput").value = state.apiBase;

  $("#settingsForm").addEventListener("submit", (e) => {
    e.preventDefault();
    state.apiKey = $("#apiKeyInput").value.trim();
    state.apiBase = $("#apiBaseInput").value.trim().replace(/\/$/, "");
    if (state.apiKey) localStorage.setItem(STORAGE.apiKey, state.apiKey);
    else localStorage.removeItem(STORAGE.apiKey);
    if (state.apiBase) localStorage.setItem(STORAGE.apiBase, state.apiBase);
    else localStorage.removeItem(STORAGE.apiBase);
    addMsg($("#chatLog"), "Settings saved.", "system");
    refreshHealth();
    loadProviders();
  });

  $("#pingBtn").addEventListener("click", async () => {
    const out = $("#healthOut");
    out.textContent = "…";
    try {
      const j = await refreshHealth();
      out.textContent = j ? JSON.stringify(j, null, 2) : "offline";
    } catch (err) {
      out.textContent = String(err.message || err);
    }
  });

  /* Boot */
  if (state.sessionId) setSession(state.sessionId);
  addMsg(
    chatLog,
    "Ready. Use the sidebar for Team, Test agent, Plugins, and Settings.",
    "system"
  );
  refreshHealth();
  loadProviders();
})();

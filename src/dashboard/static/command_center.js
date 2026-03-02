/* Command Center UI */

(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const navBtn = $("nav-command-center-btn");
  const pipelineBtn = $("nav-pipeline-btn");
  const ideasBtn = $("nav-ideas-btn");
  const agentsBtn = $("nav-agents-btn");
  const workflowsBtn = $("nav-workflows-btn");

  const commandCenter = $("command-center-content");
  const pipelineContent = $("main-content");
  const ideasContent = $("ideas-content");
  const agentsContent = $("agents-content");
  const workflowsContent = $("workflows-content");

  const chatThread = $("cc-chat-thread");
  const chatInput = $("cc-chat-input");
  const sendBtn = $("cc-send-btn");
  const approvalToggle = $("cc-approval-toggle");
  const jobFilter = $("cc-job-filter");
  const jobList = $("cc-job-list");
  const detailTitle = $("cc-detail-title");
  const detailBody = $("cc-detail-body");
  const stopJobBtn = $("cc-stop-job-btn");
  const tabButtons = Array.from(document.querySelectorAll(".cc-tab"));
  const chips = Array.from(document.querySelectorAll(".cc-chip"));

  const state = {
    jobs: [],
    selectedJobId: null,
    activeTab: "timeline",
    ws: null,
    contextDefaults: null,
  };

  function hideAllContent() {
    if (pipelineContent) pipelineContent.style.display = "none";
    if (ideasContent) ideasContent.style.display = "none";
    if (agentsContent) agentsContent.style.display = "none";
    if (workflowsContent) workflowsContent.style.display = "none";
    if (commandCenter) commandCenter.style.display = "none";
  }

  function setNavActive(activeId) {
    [navBtn, pipelineBtn, ideasBtn, agentsBtn, workflowsBtn].forEach((btn) => {
      if (!btn) return;
      btn.className = "btn-secondary";
    });
    if (activeId) activeId.className = "btn-primary";
  }

  function activateCommandCenterView() {
    hideAllContent();
    if (commandCenter) commandCenter.style.display = "flex";
    setNavActive(navBtn);
  }

  if (navBtn) {
    navBtn.addEventListener("click", () => {
      activateCommandCenterView();
      refreshJobs();
    });
  }

  async function api(path, options = {}) {
    const res = await fetch(path, options);
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.error || data?.message || "Request failed";
      throw new Error(msg);
    }
    return data;
  }

  function appendChat(text, type = "system") {
    if (!chatThread) return;
    const el = document.createElement("div");
    el.className = `cc-bubble ${type}`;
    el.textContent = text;
    chatThread.appendChild(el);
    chatThread.scrollTop = chatThread.scrollHeight;
  }

  function shortText(input, max = 85) {
    if (!input) return "";
    return input.length > max ? `${input.slice(0, max - 1)}...` : input;
  }

  function statusColor(status) {
    if (status === "running") return "var(--accent-bright)";
    if (status === "queued") return "var(--amber)";
    if (status === "waiting_approval") return "var(--amber)";
    if (status === "failed") return "var(--red)";
    if (status === "completed") return "var(--green)";
    return "var(--text-muted)";
  }

  function renderJobs() {
    if (!jobList) return;
    const filter = jobFilter?.value || "all";
    const jobs = state.jobs.filter((j) => (filter === "all" ? true : j.status === filter));
    jobList.innerHTML = "";
    if (!jobs.length) {
      jobList.innerHTML = '<div class="cc-record">No jobs found.</div>';
      return;
    }

    jobs.forEach((job) => {
      const item = document.createElement("div");
      item.className = "cc-job-item";
      if (job.id === state.selectedJobId) item.classList.add("active");
      item.innerHTML = `
        <div class="cc-job-top">
          <span class="cc-job-id">${job.id}</span>
          <span class="cc-job-status" style="color:${statusColor(job.status)}">${job.status}</span>
        </div>
        <div class="cc-job-idea">${escapeHtml(shortText(job.idea))}</div>
      `;
      item.addEventListener("click", () => selectJob(job.id));
      jobList.appendChild(item);
    });
  }

  async function refreshJobs() {
    try {
      state.jobs = await api("/api/command-center/jobs");
      renderJobs();
      if (!state.selectedJobId && state.jobs.length) {
        await selectJob(state.jobs[0].id);
      }
    } catch (err) {
      appendChat(`Failed to load jobs: ${err.message}`, "error");
    }
  }

  async function selectJob(jobId) {
    state.selectedJobId = jobId;
    renderJobs();
    try {
      const job = await api(`/api/command-center/jobs/${jobId}`);
      detailTitle.textContent = `Job ${job.id} • ${job.status}`;
      await renderDetailTab();
    } catch (err) {
      appendChat(`Failed to load job ${jobId}: ${err.message}`, "error");
    }
  }

  async function renderDetailTab() {
    const jobId = state.selectedJobId;
    if (!jobId || !detailBody) return;

    if (state.activeTab === "timeline") {
      const events = await api(`/api/command-center/jobs/${jobId}/events`);
      detailBody.innerHTML = events
        .slice(-300)
        .map(
          (e) => `
            <div class="cc-record">
              <div class="cc-record-title">${new Date(e.created_at * 1000).toLocaleTimeString()} • ${escapeHtml(e.event_type)}${e.stage ? ` • ${escapeHtml(e.stage)}` : ""}</div>
              <pre>${escapeHtml(JSON.stringify(e.payload_json, null, 2))}</pre>
            </div>
          `
        )
        .join("");
      if (!events.length) detailBody.innerHTML = '<div class="cc-record">No events yet.</div>';
      return;
    }

    if (state.activeTab === "logs") {
      const logs = await api(`/api/command-center/jobs/${jobId}/logs`);
      detailBody.innerHTML = logs
        .slice(-400)
        .map(
          (l) => `
            <div class="cc-record">
              <div class="cc-record-title">${new Date(l.created_at * 1000).toLocaleTimeString()} • ${escapeHtml(l.level.toUpperCase())} • ${escapeHtml(l.source)}</div>
              <pre>${escapeHtml(l.message)}</pre>
            </div>
          `
        )
        .join("");
      if (!logs.length) detailBody.innerHTML = '<div class="cc-record">No logs yet.</div>';
      return;
    }

    if (state.activeTab === "artifacts") {
      const artifacts = await api(`/api/command-center/jobs/${jobId}/artifacts`);
      detailBody.innerHTML = artifacts
        .slice(-200)
        .map(
          (a) => `
            <div class="cc-record">
              <div class="cc-record-title">${escapeHtml(a.artifact_type)}${a.artifact_key ? ` • ${escapeHtml(a.artifact_key)}` : ""}</div>
              <pre>${escapeHtml(a.content_text)}</pre>
            </div>
          `
        )
        .join("");
      if (!artifacts.length) detailBody.innerHTML = '<div class="cc-record">No artifacts yet.</div>';
      return;
    }

    if (state.activeTab === "decisions") {
      const job = await api(`/api/command-center/jobs/${jobId}`);
      const decisions = job.decisions || [];
      detailBody.innerHTML = decisions
        .map((d) => {
          const pending = d.status === "pending";
          return `
            <div class="cc-record">
              <div class="cc-record-title">${escapeHtml(d.stage)} • ${escapeHtml(d.status)}</div>
              <pre>${escapeHtml(JSON.stringify(d.prompt_json || {}, null, 2))}</pre>
              ${pending ? `<button class="btn-primary cc-approve-btn" data-stage="${escapeHtml(d.stage)}">Approve</button>` : ""}
            </div>
          `;
        })
        .join("");
      if (!decisions.length) detailBody.innerHTML = '<div class="cc-record">No decisions recorded.</div>';

      Array.from(document.querySelectorAll(".cc-approve-btn")).forEach((btn) => {
        btn.addEventListener("click", async (ev) => {
          const stage = ev.currentTarget.getAttribute("data-stage");
          try {
            await api(`/api/command-center/jobs/${jobId}/approve`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ stage }),
            });
            appendChat(`Approved ${jobId} at ${stage}.`, "system");
            await renderDetailTab();
          } catch (err) {
            appendChat(`Failed to approve: ${err.message}`, "error");
          }
        });
      });
      return;
    }

    if (state.activeTab === "context") {
      const [globalCfg, jobCfg, usage, compactions, globalReasoning, jobReasoning, events] = await Promise.all([
        api("/api/command-center/settings/context"),
        api(`/api/command-center/jobs/${jobId}/context-settings`),
        api(`/api/command-center/jobs/${jobId}/context-state`),
        api(`/api/command-center/jobs/${jobId}/context-compactions`),
        api("/api/command-center/settings/reasoning"),
        api(`/api/command-center/jobs/${jobId}/reasoning-settings`),
        api(`/api/command-center/jobs/${jobId}/events`),
      ]);
      state.contextDefaults = globalCfg;
      const override = jobCfg.override || state.contextDefaults;
      const weights = override.priority_weights || {};
      const latestCompaction = compactions.length ? compactions[0] : null;
      const jobReasoningOverride = jobReasoning.override || globalReasoning;
      const candidateCount = events.filter((e) => e.event_type === "architect_candidate_generated").length;
      const tddIterations = events.filter((e) => e.event_type === "tdd_iteration_started").length;
      const thinkingCount = events.filter((e) => e.event_type === "reasoning_thinking").length;
      const criticEvent = [...events].reverse().find((e) => e.event_type === "critic_debate_completed");
      const budgetEvent = [...events].reverse().find((e) => e.event_type === "tdd_budget_exhausted");

      detailBody.innerHTML = `
        <div class="cc-record">
          <div class="cc-record-title">Reasoning Metrics</div>
          <pre>${escapeHtml(
            `Candidates generated: ${candidateCount}\n` +
            `Critic winner score: ${criticEvent?.payload_json?.winner_score ?? 0}\n` +
            `TDD iterations: ${tddIterations}\n` +
            `TDD budget used: ${budgetEvent?.payload_json?.budget_seconds ?? "n/a"}\n` +
            `Thinking traces: ${thinkingCount}`
          )}</pre>
        </div>
        <div class="cc-record">
          <div class="cc-record-title">Live Usage</div>
          <pre>${escapeHtml(
            `${usage.fill_percent}% / ${Math.round((usage.limit_tokens || 0) / 1000)}k tokens\\n` +
              `Estimated tokens: ${usage.estimated_tokens}\\n` +
              `Compactions: ${usage.compaction_count}\\n` +
              `Last compacted: ${usage.last_compacted_at ? new Date(usage.last_compacted_at * 1000).toLocaleString() : "never"}`
          )}</pre>
          ${
            latestCompaction
              ? `<pre>${escapeHtml(
                  `Last compaction before: ${latestCompaction.before_fill_percent}%\\n` +
                    `Last compaction after: ${latestCompaction.after_fill_percent}%\\n` +
                    `Summary chars: ${(latestCompaction.summary_text || "").length}`
                )}</pre>`
              : ""
          }
        </div>
        <div class="cc-record">
          <div class="cc-record-title">Global Defaults</div>
          ${renderContextConfigForm("global", globalCfg)}
          <button class="btn-primary" id="cc-save-global-context">Save Global Defaults</button>
        </div>
        <div class="cc-record">
          <div class="cc-record-title">Job Override (${escapeHtml(jobId)})</div>
          <label class="cc-toggle">
            <input type="checkbox" id="cc-use-global-context" ${jobCfg.use_global_defaults ? "checked" : ""} />
            <span>Use global defaults for this job</span>
          </label>
          ${renderContextConfigForm("job", override, jobCfg.use_global_defaults)}
          <button class="btn-primary" id="cc-save-job-context">Save Job Context</button>
        </div>
        <div class="cc-record">
          <div class="cc-record-title">Reasoning Defaults</div>
          ${renderReasoningConfigForm("global", globalReasoning)}
          <button class="btn-primary" id="cc-save-global-reasoning">Save Global Reasoning</button>
        </div>
        <div class="cc-record">
          <div class="cc-record-title">Job Reasoning (${escapeHtml(jobId)})</div>
          <label class="cc-toggle">
            <input type="checkbox" id="cc-use-global-reasoning" ${jobReasoning.use_global_defaults ? "checked" : ""} />
            <span>Use global defaults for this job</span>
          </label>
          ${renderReasoningConfigForm("job", jobReasoningOverride, jobReasoning.use_global_defaults)}
          <button class="btn-primary" id="cc-save-job-reasoning">Save Job Reasoning</button>
        </div>
      `;

      const useGlobalCheckbox = document.getElementById("cc-use-global-context");
      if (useGlobalCheckbox) {
        useGlobalCheckbox.addEventListener("change", () => {
          const disabled = useGlobalCheckbox.checked;
          Array.from(detailBody.querySelectorAll("[data-job-config]")).forEach((el) => {
            el.disabled = disabled;
          });
        });
      }

      const saveGlobalBtn = document.getElementById("cc-save-global-context");
      if (saveGlobalBtn) {
        saveGlobalBtn.addEventListener("click", async () => {
          try {
            const payload = gatherContextConfigValues("global");
            await api("/api/command-center/settings/context", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            appendChat("Saved global context defaults.", "system");
            await renderDetailTab();
          } catch (err) {
            appendChat(`Failed to save global context defaults: ${err.message}`, "error");
          }
        });
      }

      const saveJobBtn = document.getElementById("cc-save-job-context");
      if (saveJobBtn) {
        saveJobBtn.addEventListener("click", async () => {
          try {
            const useGlobal = Boolean(document.getElementById("cc-use-global-context")?.checked);
            const payload = {
              job_id: jobId,
              use_global_defaults: useGlobal,
              override: useGlobal ? null : gatherContextConfigValues("job"),
            };
            await api(`/api/command-center/jobs/${jobId}/context-settings`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            appendChat(`Saved context settings for ${jobId}.`, "system");
            await renderDetailTab();
          } catch (err) {
            appendChat(`Failed to save job context settings: ${err.message}`, "error");
          }
        });
      }

      const useGlobalReasoningCheckbox = document.getElementById("cc-use-global-reasoning");
      if (useGlobalReasoningCheckbox) {
        useGlobalReasoningCheckbox.addEventListener("change", () => {
          const disabled = useGlobalReasoningCheckbox.checked;
          Array.from(detailBody.querySelectorAll("[data-job-reasoning]")).forEach((el) => {
            el.disabled = disabled;
          });
        });
      }

      const saveGlobalReasoningBtn = document.getElementById("cc-save-global-reasoning");
      if (saveGlobalReasoningBtn) {
        saveGlobalReasoningBtn.addEventListener("click", async () => {
          try {
            const payload = gatherReasoningConfigValues("global");
            await api("/api/command-center/settings/reasoning", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            appendChat("Saved global reasoning defaults.", "system");
            await renderDetailTab();
          } catch (err) {
            appendChat(`Failed to save reasoning defaults: ${err.message}`, "error");
          }
        });
      }

      const saveJobReasoningBtn = document.getElementById("cc-save-job-reasoning");
      if (saveJobReasoningBtn) {
        saveJobReasoningBtn.addEventListener("click", async () => {
          try {
            const useGlobal = Boolean(document.getElementById("cc-use-global-reasoning")?.checked);
            const payload = {
              job_id: jobId,
              use_global_defaults: useGlobal,
              override: useGlobal ? null : gatherReasoningConfigValues("job"),
              launch_override: null,
            };
            await api(`/api/command-center/jobs/${jobId}/reasoning-settings`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            appendChat(`Saved reasoning settings for ${jobId}.`, "system");
            await renderDetailTab();
          } catch (err) {
            appendChat(`Failed to save job reasoning settings: ${err.message}`, "error");
          }
        });
      }
    }
  }

  function renderContextConfigForm(prefix, cfg, disabled = false) {
    const weights = cfg.priority_weights || {};
    const disableAttr = disabled ? "disabled" : "";
    return `
      <div class="cc-context-grid">
        <label>Limit (tk): <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-context-limit-tk" value="${cfg.context_limit_tk}" min="1" /></label>
        <label>Trigger (%): <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-trigger-fill" value="${cfg.trigger_fill_percent}" min="1" max="99" /></label>
        <label>Target (%): <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-target-fill" value="${cfg.target_fill_percent}" min="1" max="98" /></label>
        <label>Min Blocks: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-min-msg" value="${cfg.min_messages_to_compact}" min="1" /></label>
        <label>Cooldown Calls: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-cooldown" value="${cfg.cooldown_calls}" min="0" /></label>
        <label>Coding Priority: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-w-coding" value="${weights.coding_context}" min="0" max="100" /></label>
        <label>User Intent Priority: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-w-intent" value="${weights.user_intent}" min="0" max="100" /></label>
        <label>Timeline Priority: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-w-timeline" value="${weights.timeline_continuity}" min="0" max="100" /></label>
        <label>Open Risks Priority: <input ${disableAttr} data-${prefix}-config type="number" id="cc-${prefix}-w-risks" value="${weights.open_risks}" min="0" max="100" /></label>
      </div>
    `;
  }

  function gatherContextConfigValues(prefix) {
    const val = (id) => Number(document.getElementById(`cc-${prefix}-${id}`)?.value || 0);
    return {
      context_limit_tk: val("context-limit-tk"),
      trigger_fill_percent: val("trigger-fill"),
      target_fill_percent: val("target-fill"),
      min_messages_to_compact: val("min-msg"),
      cooldown_calls: val("cooldown"),
      priority_weights: {
        coding_context: val("w-coding"),
        user_intent: val("w-intent"),
        timeline_continuity: val("w-timeline"),
        open_risks: val("w-risks"),
      },
    };
  }

  function renderReasoningConfigForm(prefix, cfg, disabled = false) {
    const disableAttr = disabled ? "disabled" : "";
    const marker = prefix === "job" ? "data-job-reasoning" : "data-global-reasoning";
    return `
      <div class="cc-context-grid">
        <label>Enabled:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-enabled">
            <option value="true" ${cfg.enabled ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.enabled ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>Profile:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-profile">
            <option value="fast" ${cfg.profile === "fast" ? "selected" : ""}>fast</option>
            <option value="balanced" ${cfg.profile === "balanced" ? "selected" : ""}>balanced</option>
            <option value="deep" ${cfg.profile === "deep" ? "selected" : ""}>deep</option>
          </select>
        </label>
        <label>ToT Paths: <input ${disableAttr} ${marker} type="number" id="cc-${prefix}-reasoning-tot-paths" min="1" max="8" value="${cfg.architect_tot_paths}" /></label>
        <label>Parallel ToT:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-parallel">
            <option value="true" ${cfg.architect_tot_parallel ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.architect_tot_parallel ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>Critic:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-critic">
            <option value="true" ${cfg.critic_enabled ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.critic_enabled ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>TDD:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-tdd">
            <option value="true" ${cfg.tdd_enabled ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.tdd_enabled ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>TDD Split %: <input ${disableAttr} ${marker} type="number" id="cc-${prefix}-reasoning-tdd-split" min="0" max="100" value="${cfg.tdd_time_split_percent}" /></label>
        <label>TDD Iterations: <input ${disableAttr} ${marker} type="number" id="cc-${prefix}-reasoning-tdd-iterations" min="1" max="20" value="${cfg.tdd_max_iterations}" /></label>
        <label>TDD Fail Open:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-fail-open">
            <option value="true" ${cfg.tdd_fail_open ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.tdd_fail_open ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>Thinking Modules:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-thinking">
            <option value="true" ${cfg.thinking_modules_enabled ? "selected" : ""}>true</option>
            <option value="false" ${!cfg.thinking_modules_enabled ? "selected" : ""}>false</option>
          </select>
        </label>
        <label>Thinking Visibility:
          <select ${disableAttr} ${marker} id="cc-${prefix}-reasoning-thinking-visibility">
            <option value="logs" ${cfg.thinking_visibility === "logs" ? "selected" : ""}>logs</option>
            <option value="internal" ${cfg.thinking_visibility === "internal" ? "selected" : ""}>internal</option>
            <option value="off" ${cfg.thinking_visibility === "off" ? "selected" : ""}>off</option>
          </select>
        </label>
      </div>
    `;
  }

  function gatherReasoningConfigValues(prefix) {
    const get = (id) => document.getElementById(`cc-${prefix}-reasoning-${id}`);
    const asBool = (id) => String(get(id)?.value || "false") === "true";
    return {
      enabled: asBool("enabled"),
      profile: String(get("profile")?.value || "balanced"),
      architect_tot_paths: Number(get("tot-paths")?.value || 3),
      architect_tot_parallel: asBool("parallel"),
      critic_enabled: asBool("critic"),
      tdd_enabled: asBool("tdd"),
      tdd_time_split_percent: Number(get("tdd-split")?.value || 40),
      tdd_max_iterations: Number(get("tdd-iterations")?.value || 5),
      tdd_fail_open: asBool("fail-open"),
      thinking_modules_enabled: asBool("thinking"),
      thinking_visibility: String(get("thinking-visibility")?.value || "logs"),
    };
  }

  async function sendCommand(message) {
    const text = message.trim();
    if (!text) return;
    appendChat(text, "user");
    chatInput.value = "";

    let commandText = text;
    if (!text.startsWith("/")) {
      commandText = `/run --approval ${approvalToggle.checked ? "on" : "off"} ${text}`;
    }

    try {
      const response = await api("/api/command-center/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: commandText, active_job_id: state.selectedJobId }),
      });

      appendChat(response.ui_message, response.ok ? "system" : "error");
      if (response.target_job_id) {
        state.selectedJobId = response.target_job_id;
      }
      await refreshJobs();
      if (state.selectedJobId) await selectJob(state.selectedJobId);
    } catch (err) {
      appendChat(`Command failed: ${err.message}`, "error");
    }
  }

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    state.ws = new WebSocket(`${proto}://${location.host}/ws`);
    state.ws.onmessage = async (msg) => {
      try {
        const ev = JSON.parse(msg.data);
        handleWsEvent(ev);
      } catch (_) {
        // ignore malformed event
      }
    };
    state.ws.onclose = () => setTimeout(connectWs, 1500);
  }

  async function handleWsEvent(ev) {
    const type = ev.type;
    const payload = ev.payload || {};
    const jobId = ev.job_id || payload.job_id;
    if (!jobId) return;

    const interesting = new Set([
      "job_created",
      "job_queued",
      "job_started",
      "job_status_changed",
      "job_progress",
      "job_log",
      "job_decision_required",
      "job_decision_resolved",
      "job_stopped",
      "job_failed",
      "job_completed",
      "stage_start",
      "stage_complete",
      "stage_output",
      "code_generated",
      "review_result",
      "sandbox_result",
      "waiting_for_approval",
      "stage_approved",
      "build_complete",
      "build_started",
      "error",
      "context_usage_updated",
      "context_compaction_started",
      "context_compaction_completed",
      "context_compaction_failed",
      "reasoning_config_applied",
      "architect_candidate_generated",
      "critic_debate_completed",
      "tdd_iteration_started",
      "tdd_iteration_failed",
      "tdd_iteration_passed",
      "tdd_budget_exhausted",
      "tdd_test_generated",
      "reasoning_thinking",
    ]);
    if (!interesting.has(type)) return;

    if (type === "job_started") appendChat(`Job ${jobId} started.`, "system");
    if (type === "job_completed") appendChat(`Job ${jobId} completed.`, "system");
    if (type === "job_failed") appendChat(`Job ${jobId} failed: ${payload.message || "unknown error"}`, "error");
    if (type === "waiting_for_approval") appendChat(`Job ${jobId} waiting for approval at ${payload.stage}.`, "system");
    if (type === "context_compaction_completed") {
      appendChat(
        `Context compacted for ${jobId}: ${payload.before_fill_percent}% -> ${payload.after_fill_percent}%`,
        "system"
      );
    }

    await refreshJobs();
    if (!state.selectedJobId) state.selectedJobId = jobId;
    if (state.selectedJobId === jobId) {
      await renderDetailTab();
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", () => sendCommand(chatInput.value));
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
        ev.preventDefault();
        sendCommand(chatInput.value);
      }
    });
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd") || "";
      chatInput.value = cmd === "/logs" && state.selectedJobId ? `/logs ${state.selectedJobId}` : cmd;
      chatInput.focus();
    });
  });

  if (jobFilter) {
    jobFilter.addEventListener("change", renderJobs);
  }

  if (stopJobBtn) {
    stopJobBtn.addEventListener("click", async () => {
      if (!state.selectedJobId) return;
      try {
        await api(`/api/command-center/jobs/${state.selectedJobId}/stop`, { method: "POST" });
        appendChat(`Stop requested for ${state.selectedJobId}.`, "system");
        await refreshJobs();
        await renderDetailTab();
      } catch (err) {
        appendChat(`Failed to stop job: ${err.message}`, "error");
      }
    });
  }

  tabButtons.forEach((tab) => {
    tab.addEventListener("click", async () => {
      tabButtons.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      state.activeTab = tab.getAttribute("data-tab") || "timeline";
      await renderDetailTab();
    });
  });

  connectWs();
  refreshJobs();
})();

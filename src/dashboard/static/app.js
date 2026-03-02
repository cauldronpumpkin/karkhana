/* ── Karkhana Dashboard — WebSocket Client ───────────────── */

(function () {
    "use strict";

    // ── State ────────────────────────────────────────────────
    const state = {
        ws: null,
        connected: false,
        startTime: null,
        llmCalls: 0,
        generatedFiles: {},          // path -> code
        currentApprovalStage: null,
        currentApprovalData: null,
    };

    // ── Elements ─────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);
    const badge         = $("status-badge");
    const wsDot         = $("ws-dot");
    const llmCallsEl    = $("llm-calls");
    const elapsedEl     = $("elapsed-time");
    const liveFeed      = $("live-feed");
    const outputTitle   = $("output-title");
    const outputViewer  = $("output-viewer");
    const outputActions = $("output-actions");
    const approveBtn    = $("approve-btn");
    const editBtn       = $("edit-btn");
    const editorCt      = $("editor-container");
    const editTextarea  = $("edit-textarea");
    const saveEditBtn   = $("save-edit-btn");
    const cancelEditBtn = $("cancel-edit-btn");
    const emptyState    = $("empty-state");
    const fileTree      = $("file-tree");
    const filePreview   = $("file-preview");
    const fileCount     = $("file-count");
    const previewName   = $("preview-filename");
    const previewCode   = $("file-preview-code").querySelector("code");
    const backToTree    = $("back-to-tree-btn");
    const clearFeedBtn  = $("clear-feed-btn");
    const errorModal    = $("error-modal");
    const errorMessage  = $("error-message");
    const errorCode     = $("error-code");
    const newPipelineBtn = $("new-pipeline-btn");
    const stopPipelineBtn = $("stop-pipeline-btn");
    const pipelineModal  = $("pipeline-modal");
    const closePipelineBtn = $("close-pipeline-modal");
    const startFactoryBtn = $("start-factory-btn");
    const pipelineIdea   = $("pipeline-idea");
    const pipelineReasoningEnabled = $("pipeline-reasoning-enabled");
    const pipelineReasoningProfile = $("pipeline-reasoning-profile");
    const pipelineTotPaths = $("pipeline-tot-paths");
    const pipelineTotParallel = $("pipeline-tot-parallel");
    const pipelineCriticEnabled = $("pipeline-critic-enabled");
    const pipelineTddEnabled = $("pipeline-tdd-enabled");
    const pipelineTddSplit = $("pipeline-tdd-split");
    const pipelineTddIterations = $("pipeline-tdd-iterations");
    const pipelineThinkingEnabled = $("pipeline-thinking-enabled");
    const pipelineThinkingVisibility = $("pipeline-thinking-visibility");

    // ── Navigation & Agents ───────────────────────────────────
    const navCommandCenterBtn = $("nav-command-center-btn");
    const navPipelineBtn= $("nav-pipeline-btn");
    const navAgentsBtn  = $("nav-agents-btn");
    const mainContent   = $("main-content");
    const agentsContent = $("agents-content");
    const commandCenterContent = $("command-center-content");
    const templatesGrid = $("templates-grid");
    const newTemplateBtn= $("new-template-btn");
    
    // Template Modal
    const templateModal = $("template-modal");
    const closeTplBtn   = $("close-template-modal");
    const saveTplBtn    = $("save-template-btn");
    const tplName       = $("tpl-name");
    const tplSysPrompt  = $("tpl-sys-prompt");
    const tplUserPrompt = $("tpl-user-prompt");
    const tplTemp       = $("tpl-temp");
    
    // AI Generator elements
    const autoGenBtn    = $("auto-gen-btn");
    const tplRoleDesc   = $("tpl-role-desc");

    // Run Modal
    const runAgentModal = $("run-agent-modal");
    const closeRunBtn   = $("close-run-modal");
    const execAgentBtn  = $("execute-agent-btn");
    const runAgentName  = $("run-agent-name");
    const runAgentInput = $("run-agent-input");
    
    let currentRunAgentId = null;

    // ── WebSocket ────────────────────────────────────────────

    function connect() {
        const proto = location.protocol === "https:" ? "wss" : "ws";
        state.ws = new WebSocket(`${proto}://${location.host}/ws`);

        state.ws.onopen = () => {
            state.connected = true;
            wsDot.classList.add("connected");
            wsDot.title = "Connected";
        };

        state.ws.onclose = () => {
            state.connected = false;
            wsDot.classList.remove("connected");
            wsDot.title = "Disconnected";
            // Auto-reconnect after 2s
            setTimeout(connect, 2000);
        };

        state.ws.onerror = () => {
            state.ws.close();
        };

        state.ws.onmessage = (msg) => {
            try {
                const event = JSON.parse(msg.data);
                handleEvent(event);
            } catch (_) { /* ignore malformed */ }
        };
    }

    function send(action, extra = {}) {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ action, ...extra }));
        }
    }

    // ── Event handler ────────────────────────────────────────

    function handleEvent(ev) {
        const { type, payload, timestamp } = ev;

        switch (type) {
            case "stage_start":
                onStageStart(payload);
                break;
            case "stage_complete":
            case "stage_output":
                onStageComplete(payload);
                break;
            case "code_generated":
                onCodeGenerated(payload);
                break;
            case "review_result":
                onReviewResult(payload);
                break;
            case "sandbox_result":
                onSandboxResult(payload);
                break;
            case "waiting_for_approval":
                onWaitingForApproval(payload);
                break;
            case "stage_approved":
                onStageApproved(payload);
                break;
            case "error":
                onError(payload);
                break;
            case "build_complete":
                onBuildComplete(payload);
                break;
            case "build_started":
                onBuildStarted(payload);
                break;
            default:
                break;
        }

        // Always add to live feed (except pong)
        if (type !== "pong") {
            addFeedItem(type, payload, timestamp);
        }

        // Track LLM calls
        if (payload && payload.llm_calls_count != null) {
            state.llmCalls = payload.llm_calls_count;
            llmCallsEl.textContent = `LLM calls: ${state.llmCalls}`;
        }
    }

    // ── Stage pipeline ───────────────────────────────────────

    function setStageState(stageName, stateClass) {
        const el = document.querySelector(`.stage[data-stage="${stageName}"]`);
        if (!el) return;
        el.classList.remove("running", "done", "waiting", "error");
        if (stateClass) el.classList.add(stateClass);
    }

    function onBuildStarted(_payload) {
        state.startTime = Date.now();
        setBadge("running", "Building");
        startTimer();
    }

    function onStageStart(payload) {
        if (!state.startTime) {
            state.startTime = Date.now();
            startTimer();
        }
        const stage = payload.stage;
        setBadge("running", stage.replace(/_/g, " "));
        setStageState(stage, "running");
    }

    function onStageComplete(payload) {
        const stage = payload.stage;
        setStageState(stage, "done");

        // Show output in viewer
        if (payload.output) {
            showOutput(stage, payload.output);
        }
    }

    function onWaitingForApproval(payload) {
        const stage = payload.stage;
        setStageState(stage, "waiting");
        setBadge("waiting", "Waiting for approval");

        state.currentApprovalStage = stage;
        state.currentApprovalData = payload.data;

        showOutput(stage + " (awaiting approval)", payload.data, true);
    }

    function onStageApproved(payload) {
        setStageState(payload.stage, "done");
        setBadge("running", "Resuming...");
        outputActions.style.display = "none";
        state.currentApprovalStage = null;
        state.currentApprovalData = null;
    }

    function onCodeGenerated(payload) {
        const path = payload.file_path || payload.file || "unknown";
        const code = payload.code || payload.content || "";
        state.generatedFiles[path] = code;
        renderFileTree();

        // Show in output viewer
        showOutput(path, code);
    }

    function onReviewResult(payload) {
        if (payload.passed === false && payload.issues) {
            // Still show in feed, handled by default feed addition
        }
    }

    function onSandboxResult(payload) {
        if (payload.passed === false) {
            // Sandbox failure — may trigger error triage eventually
        }
    }

    function onError(payload) {
        const stage = payload.stage;
        if (stage) setStageState(stage, "error");

        // Show error modal if it looks like a self-healing failure
        if (payload.code || payload.traceback) {
            errorMessage.textContent = payload.error || payload.message || "Unknown error";
            errorCode.textContent = payload.code || payload.traceback || "";
            errorModal.style.display = "flex";
        }
    }

    function onBuildComplete(payload) {
        setBadge("complete", "Complete");
        setStageState("complete", "done");
    }

    // ── Output viewer ────────────────────────────────────────

    function showOutput(title, data, showActions = false) {
        emptyState.style.display = "none";
        editorCt.style.display = "none";
        outputViewer.style.display = "";

        outputTitle.textContent = title;
        outputActions.style.display = showActions ? "flex" : "none";

        let text;
        if (typeof data === "string") {
            text = data;
        } else {
            try { text = JSON.stringify(data, null, 2); }
            catch (_) { text = String(data); }
        }

        outputViewer.innerHTML = `<pre>${escapeHtml(text)}</pre>`;
    }

    // ── Editor ───────────────────────────────────────────────

    approveBtn.addEventListener("click", () => {
        if (state.currentApprovalStage) {
            send("approve", { stage: state.currentApprovalStage });
        }
    });

    editBtn.addEventListener("click", () => {
        if (!state.currentApprovalData) return;
        let text;
        if (typeof state.currentApprovalData === "string") {
            text = state.currentApprovalData;
        } else {
            text = JSON.stringify(state.currentApprovalData, null, 2);
        }
        editTextarea.value = text;
        outputViewer.style.display = "none";
        outputActions.style.display = "none";
        editorCt.style.display = "flex";
    });

    saveEditBtn.addEventListener("click", () => {
        let edited;
        try { edited = JSON.parse(editTextarea.value); }
        catch (_) { edited = editTextarea.value; }

        if (state.currentApprovalStage) {
            send("approve", {
                stage: state.currentApprovalStage,
                edited_data: typeof edited === "object" ? edited : { raw: edited },
            });
        }
        editorCt.style.display = "none";
        outputViewer.style.display = "";
    });

    cancelEditBtn.addEventListener("click", () => {
        editorCt.style.display = "none";
        outputViewer.style.display = "";
        outputActions.style.display = "flex";
    });

    // ── Live feed ────────────────────────────────────────────

    function addFeedItem(type, payload, timestamp) {
        const div = document.createElement("div");
        div.className = "feed-item";

        if (type === "error") div.classList.add("error");
        else if (type === "stage_complete" || type === "stage_approved" || type === "build_complete") div.classList.add("success");
        else if (type === "waiting_for_approval") div.classList.add("waiting");

        const time = timestamp ? new Date(timestamp * 1000).toLocaleTimeString("en-US", { hour12: false }) : "";

        const stage = payload.stage || type;
        const message = buildFeedMessage(type, payload);

        div.innerHTML = `
            <span class="feed-time">${time}</span>
            <div class="feed-body">
                <div class="feed-stage">${escapeHtml(stage)}</div>
                <div class="feed-msg">${escapeHtml(message)}</div>
            </div>
        `;

        liveFeed.appendChild(div);
        liveFeed.scrollTop = liveFeed.scrollHeight;
    }

    function buildFeedMessage(type, payload) {
        switch (type) {
            case "stage_start":       return `Started processing...`;
            case "stage_complete":    return `Stage completed successfully`;
            case "stage_output":      return `Output ready`;
            case "code_generated":    return `Generated: ${payload.file_path || payload.file || "file"}`;
            case "review_result":     return payload.passed ? "Review passed ✓" : `Review failed: ${(payload.issues || []).length} issue(s)`;
            case "sandbox_result":    return payload.passed ? "Sandbox passed ✓" : "Sandbox failed ✗";
            case "waiting_for_approval": return "⏸ Waiting for your approval...";
            case "stage_approved":    return "✓ Approved — resuming pipeline";
            case "error":             return payload.message || payload.error || "An error occurred";
            case "build_complete":    return "🎉 Build finished!";
            case "build_started":     return "🏗️ Build started";
            default:                  return type;
        }
    }

    clearFeedBtn.addEventListener("click", () => { liveFeed.innerHTML = ""; });

    // ── File browser ─────────────────────────────────────────

    function renderFileTree() {
        const files = Object.keys(state.generatedFiles).sort();
        fileCount.textContent = `${files.length} file${files.length !== 1 ? "s" : ""}`;

        fileTree.innerHTML = "";
        for (const path of files) {
            const div = document.createElement("div");
            div.className = "file-entry";
            const ext = path.split(".").pop() || "";
            const icon = fileIcon(ext);
            div.innerHTML = `
                <span class="icon">${icon}</span>
                <span class="name" title="${escapeHtml(path)}">${escapeHtml(path)}</span>
                <span class="status done">✓</span>
            `;
            div.addEventListener("click", () => showFilePreview(path));
            fileTree.appendChild(div);
        }
    }

    function showFilePreview(path) {
        fileTree.style.display = "none";
        filePreview.style.display = "";
        previewName.textContent = path;
        previewCode.textContent = state.generatedFiles[path] || "";
    }

    backToTree.addEventListener("click", () => {
        filePreview.style.display = "none";
        fileTree.style.display = "";
    });

    function fileIcon(ext) {
        const map = {
            py: "🐍", js: "🟨", ts: "🔷", tsx: "⚛️", jsx: "⚛️",
            json: "📄", md: "📝", yml: "⚙️", yaml: "⚙️",
            css: "🎨", html: "🌐", sql: "🗃️",
        };
        return map[ext] || "📄";
    }

    // ── Error modal ──────────────────────────────────────────

    $("close-error-modal").addEventListener("click", () => { errorModal.style.display = "none"; });
    $("skip-error-btn").addEventListener("click", () => { errorModal.style.display = "none"; });
    $("retry-error-btn").addEventListener("click", () => {
        errorModal.style.display = "none";
        // Could send a rerun command here
    });
    // Close modal on backdrop click
    errorModal.querySelector(".modal-backdrop").addEventListener("click", () => { errorModal.style.display = "none"; });

    // ── Badge helper ─────────────────────────────────────────

    function setBadge(stateClass, text) {
        badge.className = "badge";
        if (stateClass) badge.classList.add(stateClass);
        badge.textContent = text;
    }

    // ── Timer ────────────────────────────────────────────────

    let timerInterval = null;

    function startTimer() {
        if (timerInterval) return;
        timerInterval = setInterval(() => {
            if (!state.startTime) return;
            const secs = Math.floor((Date.now() - state.startTime) / 1000);
            const m = Math.floor(secs / 60);
            const s = secs % 60;
            elapsedEl.textContent = `${m}:${String(s).padStart(2, "0")}`;
        }, 1000);
    }

    // ── Utilities ────────────────────────────────────────────

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Navigation Logic ─────────────────────────────────────
    
    navPipelineBtn.addEventListener("click", () => {
        navPipelineBtn.className = "btn-primary";
        navAgentsBtn.className = "btn-secondary";
        mainContent.style.display = "flex";
        agentsContent.style.display = "none";
        if (commandCenterContent) commandCenterContent.style.display = "none";
        if (navCommandCenterBtn) navCommandCenterBtn.className = "btn-secondary";
    });

    navAgentsBtn.addEventListener("click", () => {
        navPipelineBtn.className = "btn-secondary";
        navAgentsBtn.className = "btn-primary";
        mainContent.style.display = "none";
        agentsContent.style.display = "flex";
        if (commandCenterContent) commandCenterContent.style.display = "none";
        if (navCommandCenterBtn) navCommandCenterBtn.className = "btn-secondary";
        loadTemplates(); // refresh
    });

    // ── Agent Templates Logic ────────────────────────────────
    
    async function loadTemplates() {
        try {
            const res = await fetch("/api/templates");
            const data = await res.json();
            renderTemplates(data);
        } catch (err) {
            console.error("Failed to load templates", err);
        }
    }

    function renderTemplates(templates) {
        templatesGrid.innerHTML = "";
        for (const tpl of templates) {
            const card = document.createElement("div");
            card.className = "panel";
            card.innerHTML = `
                <div class="panel-header" style="justify-content: space-between; margin-bottom: 0.5rem;">
                    <h3>${escapeHtml(tpl.name)}</h3>
                    <button class="btn-ghost delete-tpl" data-id="${tpl.id}" title="Delete" style="color: var(--text-muted);">🗑️</button>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem; flex: 1;">
                    <p><strong>System:</strong> ${escapeHtml(tpl.system_prompt).substring(0, 60)}...</p>
                    <p><strong>User:</strong> ${escapeHtml(tpl.user_prompt_template).substring(0, 60)}...</p>
                </div>
                <div>
                   <button class="btn-primary run-tpl" data-id="${tpl.id}" data-name="${escapeHtml(tpl.name)}" style="width: 100%;">⚡ Run Agent</button>
                </div>
            `;
            templatesGrid.appendChild(card);
        }

        // Attach listeners
        document.querySelectorAll(".delete-tpl").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const id = e.currentTarget.dataset.id;
                if (confirm("Delete this template?")) {
                    await fetch(`/api/templates/${id}`, { method: "DELETE" });
                    loadTemplates();
                }
            });
        });

        document.querySelectorAll(".run-tpl").forEach(btn => {
            btn.addEventListener("click", (e) => {
                currentRunAgentId = e.currentTarget.dataset.id;
                runAgentName.textContent = e.currentTarget.dataset.name;
                runAgentInput.value = "";
                runAgentModal.style.display = "flex";
            });
        });
    }

    newTemplateBtn.addEventListener("click", () => {
        tplRoleDesc.value = "";
        tplName.value = "";
        tplSysPrompt.value = "";
        tplUserPrompt.value = "{input}";
        tplTemp.value = "0.7";
        templateModal.style.display = "flex";
    });

    closeTplBtn.addEventListener("click", () => { templateModal.style.display = "none"; });
    templateModal.querySelector(".modal-backdrop").addEventListener("click", () => { templateModal.style.display = "none"; });

    autoGenBtn.addEventListener("click", async () => {
        const desc = tplRoleDesc.value.trim();
        if (!desc) {
            alert("Please describe the role first.");
            return;
        }
        
        const oldText = autoGenBtn.textContent;
        autoGenBtn.textContent = "⚙️ Generating...";
        autoGenBtn.disabled = true;
        
        try {
            const res = await fetch("/api/templates/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role_description: desc })
            });
            
            if (!res.ok) {
                // Handle non-JSON errors (like connection refused to LM Studio)
                let errText;
                try {
                    const errData = await res.json();
                    errText = errData.error || errData.detail || res.statusText;
                } catch (e) {
                    errText = await res.text() || res.statusText;
                }
                throw new Error(errText);
            }
            
            const data = await res.json();
            
            if (data.error) {
                alert("Generation failed: " + data.error);
            } else {
                if (data.name) tplName.value = data.name;
                if (data.system_prompt) tplSysPrompt.value = data.system_prompt;
                if (data.user_prompt_template) tplUserPrompt.value = data.user_prompt_template;
            }
        } catch (err) {
            console.error(err);
            alert("Error communicating with generation endpoint: " + err.message);
        } finally {
            autoGenBtn.textContent = oldText;
            autoGenBtn.disabled = false;
        }
    });

    saveTplBtn.addEventListener("click", async () => {
        const data = {
            name: tplName.value || "Untitled Agent",
            system_prompt: tplSysPrompt.value || "You are a helpful assistant.",
            user_prompt_template: tplUserPrompt.value || "{input}",
            temperature: parseFloat(tplTemp.value) || 0.7
        };
        saveTplBtn.disabled = true;
        saveTplBtn.textContent = "Saving...";
        try {
            await fetch("/api/templates", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            templateModal.style.display = "none";
            loadTemplates();
        } finally {
            saveTplBtn.disabled = false;
            saveTplBtn.textContent = "Save Template";
        }
    });

    closeRunBtn.addEventListener("click", () => { runAgentModal.style.display = "none"; });
    runAgentModal.querySelector(".modal-backdrop").addEventListener("click", () => { runAgentModal.style.display = "none"; });

    execAgentBtn.addEventListener("click", async () => {
        if (!currentRunAgentId) return;
        const input = runAgentInput.value;
        
        // Switch to pipeline view to see output
        runAgentModal.style.display = "none";
        navPipelineBtn.click();
        
        try {
            await fetch(`/api/templates/${currentRunAgentId}/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ input })
            });
            // The result will be streamed via EventBus to the output panel!
        } catch (err) {
            console.error(err);
        }
    });

    // ── Pipeline Control Logic ──────────────────────────────
    
    const navIdeasBtn = $("nav-ideas-btn");
    const navWorkflowsBtn = $("nav-workflows-btn");
    const ideasContent = $("ideas-content");
    const workflowsContent = $("workflows-content");
    const ideasGrid = $("ideas-grid");
    const workflowsGrid = $("workflows-grid");
    const newIdeaBtn = $("new-idea-btn");

    const workflowModal = $("workflow-modal");
    const closeWfBtn = $("close-workflow-modal");
    const wfNameInput = $("wf-name");
    const wfDescriptionInput = $("wf-description");
    const wfAgentSelect = $("wf-agent-select");
    const wfEnvSelect = $("wf-env-select");
    const wfAddStepBtn = $("wf-add-step");
    const wfStepsList = $("wf-steps-list");
    const saveWorkflowBtn = $("save-workflow-btn");
    const wfClearAllBtn = $("wf-clear-all");
    const wfValidateBtn = $("wf-validate-btn");
    const stepConfigContainer = $("step-config-container");
    const wfUpdateStepBtn = $("wf-update-step");
    const wfDeleteStepBtn = $("wf-delete-step");
    
    // Canvas elements
    const wfCanvasContainer = $("wf-canvas-container");
    const wfCanvasSvg = $("wf-canvas-svg");
    const wfZoomInBtn = $("wf-zoom-in");
    const wfZoomOutBtn = $("wf-zoom-out");
    const wfResetZoomBtn = $("wf-reset-zoom");
    
    // Step configuration elements
    const wfConditionType = $("wf-condition-type");
    const wfConditionValue = $("wf-condition-value");
    const wfLoopType = $("wf-loop-type");
    const wfLoopFixedContainer = $("wf-loop-fixed-container");
    const wfLoopIterationsInput = $("wf-loop-iterations");
    const wfLoopBreakCondition = $("wf-loop-break-condition");
    
    // Quality sliders
    const wfQualityCreativity = $("wf-quality-creativity");
    const wfQualityDepth = $("wf-quality-depth");
    const wfQualityThorough = $("wf-quality-thorough");
    const wfQualityProactive = $("wf-quality-proactive");
    const newWorkflowBtn = $("new-workflow-btn");

    const runWfModal = $("run-wf-modal");
    const closeRunWfBtn = $("close-run-wf-modal");
    const wfSelectRun = $("wf-select-run");
    const runWfIdeaText = $("run-wf-idea-text");
    const executeWfBtn = $("execute-wf-btn");

    // Workflow state
    let currentIdeaForWf = null;
    let currentWfSteps = [];
    let selectedStepIndex = -1;
    let canvasZoom = 1;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;

    navIdeasBtn.addEventListener("click", () => {
        [navCommandCenterBtn, navPipelineBtn, navIdeasBtn, navAgentsBtn, navWorkflowsBtn].filter(Boolean).forEach(b => b.className = "btn-secondary");
        navIdeasBtn.className = "btn-primary";
        [commandCenterContent, mainContent, agentsContent, ideasContent, workflowsContent].filter(Boolean).forEach(c => c.style.display = "none");
        ideasContent.style.display = "flex";
        loadIdeas();
    });

    navWorkflowsBtn.addEventListener("click", () => {
        [navCommandCenterBtn, navPipelineBtn, navIdeasBtn, navAgentsBtn, navWorkflowsBtn].filter(Boolean).forEach(b => b.className = "btn-secondary");
        navWorkflowsBtn.className = "btn-primary";
        [commandCenterContent, mainContent, agentsContent, ideasContent, workflowsContent].filter(Boolean).forEach(c => c.style.display = "none");
        workflowsContent.style.display = "flex";
        loadWorkflows();
    });

    navPipelineBtn.addEventListener("click", () => {
        [navCommandCenterBtn, navPipelineBtn, navIdeasBtn, navAgentsBtn, navWorkflowsBtn].filter(Boolean).forEach(b => b.className = "btn-secondary");
        navPipelineBtn.className = "btn-primary";
        [commandCenterContent, mainContent, agentsContent, ideasContent, workflowsContent].filter(Boolean).forEach(c => c.style.display = "none");
        mainContent.style.display = "flex";
    });

    navAgentsBtn.addEventListener("click", () => {
        [navCommandCenterBtn, navPipelineBtn, navIdeasBtn, navAgentsBtn, navWorkflowsBtn].filter(Boolean).forEach(b => b.className = "btn-secondary");
        navAgentsBtn.className = "btn-primary";
        [commandCenterContent, mainContent, agentsContent, ideasContent, workflowsContent].filter(Boolean).forEach(c => c.style.display = "none");
        agentsContent.style.display = "flex";
        loadTemplates(); // refresh
    });

    async function loadIdeas() {
        const res = await fetch("/api/ideas");
        const ideas = await res.json();
        ideasGrid.innerHTML = "";
        ideas.forEach(idea => {
            const card = document.createElement("div");
            card.className = "panel";
            card.innerHTML = `
                <div class="panel-header" style="justify-content: space-between;">
                    <h3>Idea</h3>
                    <button class="btn-ghost delete-idea" data-id="${idea.id}">🗑️</button>
                </div>
                <div style="flex: 1; margin: 1rem 0;">${escapeHtml(idea.text)}</div>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn-primary run-wf-on-idea" data-id="${idea.id}" data-text="${escapeHtml(idea.text)}" style="flex: 1;">⚡ Run Workflow</button>
                </div>
            `;
            ideasGrid.appendChild(card);
        });

        document.querySelectorAll(".delete-idea").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                if(confirm("Delete this idea?")) {
                    await fetch(`/api/ideas/${e.currentTarget.dataset.id}`, { method: "DELETE" });
                    loadIdeas();
                }
            });
        });

        document.querySelectorAll(".run-wf-on-idea").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                currentIdeaForWf = e.currentTarget.dataset.id;
                runWfIdeaText.textContent = e.currentTarget.dataset.text;
                await loadWfSelect();
                runWfModal.style.display = "flex";
            });
        });
    }

    async function loadWorkflows() {
        const res = await fetch("/api/workflows");
        const workflows = await res.json();
        workflowsGrid.innerHTML = "";
        workflows.forEach(wf => {
            const card = document.createElement("div");
            card.className = "panel";
            card.innerHTML = `
                <div class="panel-header" style="justify-content: space-between;">
                    <h3>${escapeHtml(wf.name)}</h3>
                    <button class="btn-ghost delete-wf" data-id="${wf.id}">🗑️</button>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin: 0.5rem 0; flex: 1;">
                    Steps: ${wf.steps.join(" → ")}
                </div>
            `;
            workflowsGrid.appendChild(card);
        });

        document.querySelectorAll(".delete-wf").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                if(confirm("Delete this workflow?")) {
                    await fetch(`/api/workflows/${e.currentTarget.dataset.id}`, { method: "DELETE" });
                    loadWorkflows();
                }
            });
        });
    }

    newIdeaBtn.addEventListener("click", async () => {
        const text = prompt("Enter your new app idea:");
        if (text) {
            await fetch("/api/ideas", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });
            loadIdeas();
        }
    });

    // Update workflow modal open handler to include canvas and env vars
    newWorkflowBtn.addEventListener("click", async () => {
        wfNameInput.value = "";
        wfDescriptionInput.value = "";
        currentWfSteps = [];
        selectedStepIndex = -1;
        stepConfigContainer.style.display = "none";
        await fillAgentSelect();
        fillEnvSelect();
        renderWfCanvas();
        renderWfStepsList();
        workflowModal.style.display = "flex";
    });

    closeWfBtn.addEventListener("click", () => {
        workflowModal.style.display = "none";
        selectedStepIndex = -1;
    });

    // Workflow modal backdrop click
    workflowModal.querySelector(".modal-backdrop").addEventListener("click", () => {
        workflowModal.style.display = "none";
        selectedStepIndex = -1;
    });

    async function fillAgentSelect() {
        const res = await fetch("/api/templates");
        const templates = await res.json();
        wfAgentSelect.innerHTML = templates.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("");
    }

    wfAddStepBtn.addEventListener("click", () => {
        const id = wfAgentSelect.value;
        if (!id) return;
        
        // Get full template data to populate name and default env_vars
        fetch(`/api/templates/${id}`)
            .then(res => res.json())
            .then(template => {
                currentWfSteps.push({
                    id: template.id,
                    name: template.name || "Agent",
                    templateName: template.name,
                    description: template.description || "",
                    env_vars: {},
                    agent_qualities: {
                        creativity: 0.7,
                        depth: 0.6,
                        thoroughness: 0.8,
                        proactivity: 0.5
                    }
                });
                renderWfCanvas();
                renderWfStepsList();
            })
            .catch(err => {
                console.error("Failed to fetch template", err);
                // Fallback if template API fails
                const name = wfAgentSelect.options[wfAgentSelect.selectedIndex].text;
                currentWfSteps.push({ id, name });
                renderWfCanvas();
                renderWfStepsList();
            });
    });

    // Deprecated: renderWfSteps kept for backward compatibility but uses canvas rendering now
    function renderWfSteps() {
        renderWfCanvas();
        renderWfStepsList();
    }

    window.removeWfStep = (index) => {
        currentWfSteps.splice(index, 1);
        selectedStepIndex = -1;
        stepConfigContainer.style.display = "none";
        renderWfCanvas();
        renderWfStepsList();
    };

    // New render function for step list with full info (for side panel)
    function renderWfStepsList() {
        const countEl = document.querySelector("#wf-steps-list + div > label") || 
                        document.createElement("label");
        
        wfStepsList.innerHTML = currentWfSteps.map((s, i) => `
            <div style="background: var(--bg-surface); padding: 0.5rem; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                <span>${i+1}. ${escapeHtml(s.name)}</span>
                <button class="btn-ghost" onclick="window.selectWfStep(${i})" style="padding: 0 0.5rem;">⚙️</button>
            </div>
        `).join("");
    }

    saveWorkflowBtn.addEventListener("click", async () => {
        const name = wfNameInput.value.trim();
        if (!name || currentWfSteps.length === 0) {
            alert("Name and steps are required.");
            return;
        }
        
        // Build full workflow object with all metadata
        const workflowData = {
            name,
            description: wfDescriptionInput.value.trim(),
            steps: currentWfSteps.map(s => s.id)
        };
        
        await fetch("/api/workflows", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(workflowData)
        });
        workflowModal.style.display = "none";
        loadWorkflows();
    });

    // Clear all steps
    wfClearAllBtn.addEventListener("click", () => {
        if (currentWfSteps.length > 0 && confirm("Are you sure you want to clear all steps?")) {
            currentWfSteps = [];
            selectedStepIndex = -1;
            stepConfigContainer.style.display = "none";
            renderWfCanvas();
            renderWfStepsList();
        }
    });

    // Validate workflow
    wfValidateBtn.addEventListener("click", () => {
        const errors = validateWorkflow(currentWfSteps);
        if (errors.length === 0) {
            alert("✓ Workflow is valid!");
        } else {
            alert("Validation Errors:\n" + errors.join("\n"));
        }
    });

    function validateWorkflow(steps) {
        const errors = [];
        
        // Check for empty steps
        if (steps.length === 0) {
            errors.push("No steps defined");
            return errors;
        }
        
        // Validate each step's configuration
        steps.forEach((step, index) => {
            // Check loop conditions
            if (step.loop && step.loop.type === "until_condition" && !step.loop.breakCondition) {
                errors.push(`Step ${index + 1}: Loop with 'Until condition' requires a break condition`);
            }
            
            // Check condition value for non-empty types
            if (step.condition && ["contains", "matches_regex", "starts_with", "ends_with"].includes(step.condition.type)) {
                if (!step.condition.value) {
                    errors.push(`Step ${index + 1}: Condition requires a value`);
                } else if (step.condition.type === "matches_regex") {
                    try {
                        new RegExp(step.condition.value);
                    } catch (e) {
                        errors.push(`Step ${index + 1}: Invalid regex pattern: "${step.condition.value}"`);
                    }
                }
            }
        });
        
        return errors;
    }

    async function loadWfSelect() {
        const res = await fetch("/api/workflows");
        const workflows = await res.json();
        wfSelectRun.innerHTML = workflows.map(w => `<option value="${w.id}">${w.name}</option>`).join("");
    }

    closeRunWfBtn.addEventListener("click", () => runWfModal.style.display = "none");

    executeWfBtn.addEventListener("click", async () => {
        const wfId = wfSelectRun.value;
        if (!wfId || !currentIdeaForWf) return;
        
        runWfModal.style.display = "none";
        navPipelineBtn.click();
        resetUI();
        
        await fetch(`/api/workflows/${wfId}/run/${currentIdeaForWf}`, { method: "POST" });
    });

    newPipelineBtn.addEventListener("click", () => {
        pipelineIdea.value = "";
        pipelineModal.style.display = "flex";
    });

    closePipelineBtn.addEventListener("click", () => { pipelineModal.style.display = "none"; });
    pipelineModal.querySelector(".modal-backdrop").addEventListener("click", () => { pipelineModal.style.display = "none"; });

    startFactoryBtn.addEventListener("click", async () => {
        const idea = pipelineIdea.value.trim();
        if (!idea) {
            alert("Please enter an idea first.");
            return;
        }
        
        startFactoryBtn.disabled = true;
        startFactoryBtn.textContent = "⚙️ Launching...";
        
        try {
            const reasoning = {
                enabled: pipelineReasoningEnabled?.value === "on",
                profile: pipelineReasoningProfile?.value || "balanced",
                architect_tot_paths: Number(pipelineTotPaths?.value || 3),
                architect_tot_parallel: pipelineTotParallel?.value === "on",
                critic_enabled: pipelineCriticEnabled?.value === "on",
                tdd_enabled: pipelineTddEnabled?.value === "on",
                tdd_time_split_percent: Number(pipelineTddSplit?.value || 40),
                tdd_max_iterations: Number(pipelineTddIterations?.value || 5),
                thinking_modules_enabled: pipelineThinkingEnabled?.value === "on",
                thinking_visibility: pipelineThinkingVisibility?.value || "logs",
            };
            const res = await fetch("/api/build", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ idea, reasoning })
            });

            if (res.ok) {
                pipelineModal.style.display = "none";
                resetUI();
                navPipelineBtn.click(); // Switch to pipeline view
            } else {
                const err = await res.json();
                alert("Failed to start build: " + (err.detail || "Unknown error"));
            }
        } catch (err) {
            console.error(err);
            alert("Error communicating with build endpoint.");
        } finally {
            startFactoryBtn.disabled = false;
            startFactoryBtn.textContent = "🚀 Start Factory";
        }
    });

    stopPipelineBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to stop the current pipeline? This will instantly kill all active agents.")) {
            return;
        }
        
        try {
            const res = await fetch("/api/build/stop", { method: "POST" });
            const data = await res.json();
            
            if (data.ok) {
                // The backend emits an error/stop message which the feed will show
                // We also clear the locally tracked state timer
                if (timerInterval) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                }
                setBadge("idle", "Stopped");
            } else {
                alert(data.message);
            }
        } catch (err) {
            console.error(err);
            alert("Error stopping pipeline.");
        }
    });

    function resetUI() {
        state.startTime = null;
        state.llmCalls = 0;
        state.generatedFiles = {};
        state.currentApprovalStage = null;
        state.currentApprovalData = null;
        
        llmCallsEl.textContent = "LLM calls: 0";
        elapsedEl.textContent = "0:00";
        liveFeed.innerHTML = "";
        fileTree.innerHTML = "";
        outputViewer.style.display = "none";
        outputActions.style.display = "none";
        editorCt.style.display = "none";
        emptyState.style.display = "flex";
        badge.textContent = "Idle";
        badge.className = "badge";
        
        if (timerInterval) {
           clearInterval(timerInterval);
           timerInterval = null;
        }

        document.querySelectorAll(".stage").forEach(el => {
            el.classList.remove("running", "done", "waiting", "error");
        });
    }

    // ── Canvas Pan Functions for Workflow Builder ─────────────
    let panX = 0;
    let panY = 0;
    let draggedNodeIndex = -1;
    let dragOffsetX = 0;
    let dragOffsetY = 0;
    let ghostElement = null;

    window.startPan = (e) => {
        // Check if clicking on a node
        if (e.target.closest('.wf-node')) {
            const node = e.target.closest('.wf-node');
            const index = parseInt(node.dataset.index);
            if (!isNaN(index)) {
                startDragNode(e, index);
                return;
            }
        }
        
        // Start panning
        isPanning = true;
        panStartX = e.clientX;
        panStartY = e.clientY;
        wfCanvasContainer.classList.add('panning');
        wfCanvasContainer.style.cursor = 'grabbing';
    };

    window.endPan = () => {
        isPanning = false;
        draggedNodeIndex = -1;
        wfCanvasContainer.classList.remove('panning');
        wfCanvasContainer.style.cursor = 'grab';
        document.querySelectorAll('.drop-zone').forEach(el => el.remove());
    };

    window.pan = (e) => {
        if (!isPanning || !e.buttons) return;
        const dx = e.clientX - panStartX;
        const dy = e.clientY - panStartY;
        panX += dx;
        panY += dy;
        panStartX = e.clientX;
        panStartY = e.clientY;
        applyCanvasTransform();
    };

    // Apply pan and zoom transform with proper coordinate handling
    function applyCanvasTransform() {
        const transform = `translate(${panX}px, ${panY}px) scale(${canvasZoom})`;
        wfCanvasContainer.style.transform = transform;
        
        // Update connection lines to account for pan/zoom
        updateWfConnections();
        
        // Update zoom info display
        const zoomInfo = document.querySelector('.pan-zoom-info');
        if (zoomInfo) {
            zoomInfo.textContent = `${Math.round(canvasZoom * 100)}%`;
        }
    }

    // ── Workflow Builder Functions ───────────────────────────-
    
    async function fillAgentSelect() {
        try {
            const res = await fetch("/api/templates");
            const templates = await res.json();
            wfAgentSelect.innerHTML = templates.map(t => 
                `<option value="${t.id}">${escapeHtml(t.name)}</option>`
            ).join("");
        } catch (err) {
            console.error("Failed to load agents", err);
        }
    }

    function fillEnvSelect() {
        // Get env vars from window.envVars if available, otherwise use defaults
        const envVars = window.envVars || [
            { key: "LM_STUDIO_BASE_URL", label: "LM Studio Base URL" },
            { key: "LM_STUDIO_MODEL_NAME", label: "LM Studio Model Name" },
            { key: "MAX_TOKENS", label: "Max Tokens" },
            { key: "TEMPERATURE_CREATIVE", label: "Temperature (Creative)" },
            { key: "TEMPERATURE_CODING", label: "Temperature (Coding)" },
            { key: "TIMEOUT_SECONDS", label: "Timeout Seconds" },
            { key: "MAX_RETRIES", label: "Max Retries" },
            { key: "SANDBOX_TIMEOUT", label: "Sandbox Timeout" },
            { key: "MAX_RETRIES_PER_FILE", label: "Max Retries Per File" },
            { key: "TOOL_CALLING_ENABLED", label: "Tool Calling Enabled" },
            { key: "TOOL_CALLING_FALLBACK_ENABLED", label: "Tool Calling Fallback Enabled" },
            { key: "TOOL_CALLING_MAX_ROUNDS", label: "Tool Calling Max Rounds" },
            { key: "TOOL_CALLING_FILE_TOOL_MAX_CHARS", label: "Tool Read Max Chars" }
        ];
        wfEnvSelect.innerHTML = envVars.map(e => 
            `<option value="${e.key}">${escapeHtml(e.label)}</option>`
        ).join("");
    }

    function renderWfCanvas() {
        // Clear canvas but keep SVG
        const svg = wfCanvasSvg;
        wfCanvasContainer.innerHTML = "";

        // Render each step as a draggable node with visual feedback
        currentWfSteps.forEach((step, index) => {
            const node = document.createElement("div");
            node.className = "wf-node";
            node.dataset.index = index;
            node.style.left = `${100 + (index * 250)}px`;
            node.style.top = "80px";
            
            // Add visual feedback classes
            if (selectedStepIndex === index) {
                node.classList.add('selected');
            }
            
            node.innerHTML = `
                <div class="wf-node-header">
                    <span class="wf-node-number">${index + 1}</span>
                    <span class="wf-node-title">${escapeHtml(step.name)}</span>
                </div>
                <div class="wf-node-meta">
                    ${escapeHtml(step.templateName || "Agent")}
                </div>
                <button onclick="window.selectWfStep(${index})" class="btn-ghost" style="position: absolute; right: 8px; top: 8px; padding: 0.25rem 0.5rem; font-size: 0.75rem;">⚙️</button>
            `;

            // Drag start handler with ghost creation
            node.addEventListener("mousedown", (e) => {
                if (!e.target.closest("button")) {
                    e.preventDefault();
                    startDragNode(e, index);
                }
            });

            wfCanvasContainer.appendChild(node);
        });

        updateWfConnections();
    }

    function updateWfConnections() {
        const svg = wfCanvasSvg;
        
        // Preserve the defs section, remove old lines
        const existingDefs = svg.querySelector('defs');
        if (existingDefs) {
            existingDefs.remove();
        }
        
        svg.innerHTML = `
            <defs>
                <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                    <polygon points="0 0, 6 3, 0 6" fill="#666" />
                </marker>
            </defs>
        `;

        // Draw connections between consecutive nodes (by array order, not position)
        for (let i = 0; i < currentWfSteps.length - 1; i++) {
            const node1 = wfCanvasContainer.querySelector(`.wf-node[data-index="${i}"]`);
            const node2 = wfCanvasContainer.querySelector(`.wf-node[data-index="${i+1}"]`);

            if (node1 && node2) {
                // Get positions relative to the container, accounting for pan/zoom
                const containerRect = wfCanvasContainer.getBoundingClientRect();
                
                // Node 1 position (right center)
                const rect1 = node1.getBoundingClientRect();
                const x1 = ((rect1.right - containerRect.left) - panX) / canvasZoom;
                const y1 = ((rect1.top + rect1.height / 2 - containerRect.top) - panY) / canvasZoom;

                // Node 2 position (left center)
                const rect2 = node2.getBoundingClientRect();
                const x2 = ((rect2.left - containerRect.left) - panX) / canvasZoom;
                const y2 = ((rect2.top + rect2.height / 2 - containerRect.top) - panY) / canvasZoom;

                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", x1);
                line.setAttribute("y1", y1);
                line.setAttribute("x2", x2);
                line.setAttribute("y2", y2);
                line.setAttribute("stroke", getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || "#666");
                line.setAttribute("stroke-width", "2");
                line.setAttribute("marker-end", "url(#arrowhead)");

                svg.appendChild(line);
            }
        }
    }

    // Drag node with visual feedback and reorder support
    let dragGhost = null;
    let originalParent = null;

    function startDragNode(e, index) {
        draggedNodeIndex = index;
        const node = wfCanvasContainer.querySelector(`.wf-node[data-index="${index}"]`);
        if (!node) return;

        // Create ghost element for visual feedback
        createDragGhost(node, e.clientX, e.clientY);
        
        // Add dragging class to original node
        node.classList.add('dragging');
        
        // Store drag offset relative to the node's top-left corner
        const rect = node.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
        originalParent = wfCanvasContainer;

        // Add global event listeners for smooth dragging across zoom/pan boundaries
        document.addEventListener("mousemove", onDragNode);
        document.addEventListener("mouseup", stopDragNode);
    }

    function createDragGhost(sourceNode, mouseX, mouseY) {
        // Remove any existing ghost
        if (dragGhost) dragGhost.remove();
        
        const rect = sourceNode.getBoundingClientRect();
        dragGhost = sourceNode.cloneNode(true);
        dragGhost.className = 'wf-node drag-ghost';
        dragGhost.style.position = 'fixed';
        dragGhost.style.left = `${mouseX - 100}px`;
        dragGhost.style.top = `${mouseY - 35}px`;
        dragGhost.style.width = '200px';
        dragGhost.style.zIndex = '9999';
        dragGhost.style.pointerEvents = 'none';
        
        document.body.appendChild(dragGhost);
    }

    function onDragNode(e) {
        if (draggedNodeIndex === -1 || !dragGhost) return;
        
        const node = wfCanvasContainer.querySelector(`.wf-node[data-index="${draggedNodeIndex}"]`);
        if (!node) return;

        // Update ghost position to follow cursor
        dragGhost.style.left = `${e.clientX - 100}px`;
        dragGhost.style.top = `${e.clientY - 35}px`;

        // Calculate new position in container coordinates (accounting for pan/zoom)
        const containerRect = wfCanvasContainer.getBoundingClientRect();
        let newX = (e.clientX - containerRect.left - dragOffsetX) / canvasZoom - panX / canvasZoom;
        let newY = (e.clientY - containerRect.top - dragOffsetY) / canvasZoom - panY / canvasZoom;

        // Clamp to container bounds
        const maxLeft = wfCanvasContainer.scrollWidth - 200;
        const maxTop = wfCanvasContainer.scrollHeight - 60;
        newX = Math.max(0, Math.min(newX, maxLeft));
        newY = Math.max(0, Math.min(newY, maxTop));

        node.style.left = `${newX}px`;
        node.style.top = `${newY}px`;

        // Check for drop zones and show visual feedback
        checkDropZones(e.clientX, e.clientY);
        
        updateWfConnections();
    }

    function stopDragNode() {
        if (draggedNodeIndex === -1) return;
        
        const node = wfCanvasContainer.querySelector(`.wf-node[data-index="${draggedNodeIndex}"]`);
        if (node) {
            node.classList.remove('dragging');
        }
        
        // Remove ghost and cleanup
        if (dragGhost) {
            dragGhost.remove();
            dragGhost = null;
        }
        
        // Remove all drop zones
        document.querySelectorAll('.drop-zone').forEach(el => el.remove());
        document.querySelectorAll('.wf-node.drag-over').forEach(el => el.classList.remove('drag-over'));
        
        draggedNodeIndex = -1;
        originalParent = null;
        
        document.removeEventListener("mousemove", onDragNode);
        document.removeEventListener("mouseup", stopDragNode);
    }

    function checkDropZones(mouseX, mouseY) {
        // Remove existing drag-over states
        document.querySelectorAll('.wf-node.drag-over').forEach(el => el.classList.remove('drag-over'));
        
        const nodes = Array.from(wfCanvasContainer.querySelectorAll('.wf-node'));
        const draggedRect = nodes[draggedNodeIndex]?.getBoundingClientRect();
        
        if (!draggedRect) return;

        // Check each node to see if mouse is near it for potential reordering
        nodes.forEach((node, idx) => {
            if (idx === draggedNodeIndex) return; // Skip the dragged node itself
            
            const rect = node.getBoundingClientRect();
            const centerX = (rect.left + rect.right) / 2;
            const centerY = (rect.top + rect.bottom) / 2;
            
            // Check if mouse is in a drop zone relative to this node
            const dx = mouseX - centerX;
            const dy = mouseY - centerY;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < 100) {
                // Determine direction and show visual feedback
                node.classList.add('drag-over');
                
                // Create drop zone indicator
                createDropZoneIndicator(node, dx, dy);
            }
        });
    }

    function createDropZoneIndicator(targetNode, dx, dy) {
        const rect = targetNode.getBoundingClientRect();
        const containerRect = wfCanvasContainer.getBoundingClientRect();
        
        // Calculate position relative to container (accounting for pan/zoom)
        let left = ((rect.left - containerRect.left) / canvasZoom) - panX / canvasZoom;
        let top = ((rect.top - containerRect.top) / canvasZoom) - panY / canvasZoom;
        
        // Determine direction and position arrow
        const isLeft = dx < 0;
        const isAbove = dy < 0;
        
        if (isAbove && Math.abs(dy) > Math.abs(dx)) {
            // Above target - show up arrow
            top -= 25;
        } else if (!isAbove && Math.abs(dy) >= Math.abs(dx)) {
            // Below or equal - show down arrow
            top += rect.height / canvasZoom + 10;
        } else if (isLeft) {
            // Left side
            left -= 25;
        } else {
            // Right side
            left += rect.width / canvasZoom + 10;
        }
        
        const arrow = document.createElement('div');
        arrow.className = 'drag-arrow';
        if (isAbove && Math.abs(dy) > Math.abs(dx)) arrow.classList.add('up');
        else if (!isAbove && Math.abs(dy) >= Math.abs(dx)) arrow.classList.add('down');
        else if (isLeft) arrow.classList.add('left');
        else arrow.classList.add('right');
        
        arrow.style.left = `${left}px`;
        arrow.style.top = `${top}px`;
        arrow.style.pointerEvents = 'none';
        
        wfCanvasContainer.appendChild(arrow);
    }

    // Expose selectWfStep to window for onclick handlers
    window.selectWfStep = (index) => {
        selectedStepIndex = index;
        if (selectedStepIndex < 0 || selectedStepIndex >= currentWfSteps.length) {
            stepConfigContainer.style.display = "none";
            return;
        }
        const step = currentWfSteps[selectedStepIndex];
        
        // Populate form fields with step data
        wfConditionType.value = step.condition?.type || "";
        wfConditionValue.value = step.condition?.value || "";
        wfLoopType.value = step.loop?.type || "";
        wfLoopIterationsInput.value = step.loop?.iterations || "3";
        wfLoopBreakCondition.value = step.loop?.breakCondition || "";
        
        // Populate environment variables
        const selectedEnvVars = Object.keys(step.env_vars || {});
        Array.from(wfEnvSelect.options).forEach(opt => {
            opt.selected = selectedEnvVars.includes(opt.value);
        });
        
        // Populate quality sliders if they exist in the step
        const qualities = step.agent_qualities || {};
        wfQualityCreativity.value = qualities.creativity !== undefined ? qualities.creativity : 0.7;
        wfQualityDepth.value = qualities.depth !== undefined ? qualities.depth : 0.6;
        wfQualityThorough.value = qualities.thoroughness !== undefined ? qualities.thoroughness : 0.8;
        wfQualityProactive.value = qualities.proactivity !== undefined ? qualities.proactivity : 0.5;
        
        // Update slider value displays
        document.getElementById("wf-quality-creativity-val").textContent = wfQualityCreativity.value;
        document.getElementById("wf-quality-depth-val").textContent = wfQualityDepth.value;
        document.getElementById("wf-quality-thorough-val").textContent = wfQualityThorough.value;
        document.getElementById("wf-quality-proactive-val").textContent = wfQualityProactive.value;

        stepConfigContainer.style.display = "block";
    };

    // Loop type toggle
    wfLoopType.addEventListener("change", () => {
        if (wfLoopType.value === "fixed") {
            wfLoopFixedContainer.style.display = "block";
            wfLoopBreakCondition.parentElement.style.display = "none";
        } else if (wfLoopType.value === "until_condition") {
            wfLoopFixedContainer.style.display = "none";
            wfLoopBreakCondition.parentElement.style.display = "block";
        } else {
            wfLoopFixedContainer.style.display = "none";
            wfLoopBreakCondition.parentElement.style.display = "none";
        }
    });

    // Condition type toggle
    wfConditionType.addEventListener("change", () => {
        if (wfConditionType.value) {
            wfConditionValue.disabled = false;
        } else {
            wfConditionValue.disabled = true;
        }
    });

    // Zoom controls
    wfZoomInBtn.addEventListener("click", () => {
        canvasZoom = Math.min(canvasZoom + 0.2, 3);
        applyCanvasTransform();
    });
    wfZoomOutBtn.addEventListener("click", () => {
        canvasZoom = Math.max(canvasZoom - 0.2, 0.5);
        applyCanvasTransform();
    });
    wfResetZoomBtn.addEventListener("click", () => {
        canvasZoom = 1;
        applyCanvasTransform();
    });

    function applyCanvasTransform() {
        const transform = `scale(${canvasZoom})`;
        wfCanvasContainer.style.transform = transform;
        wfCanvasSvg.style.transform = transform;
        updateWfConnections();
    }

    // Update step from form
    wfUpdateStepBtn.addEventListener("click", () => {
        if (selectedStepIndex < 0 || selectedStepIndex >= currentWfSteps.length) return;

        const envVars = {};
        Array.from(wfEnvSelect.selectedOptions).forEach(opt => {
            envVars[opt.value] = `{{${opt.label}}}`;
        });

        const condition = wfConditionType.value ? {
            type: wfConditionType.value,
            value: wfConditionValue.value
        } : null;

        let loop = null;
        if (wfLoopType.value === "fixed") {
            loop = { type: "fixed", iterations: parseInt(wfLoopIterationsInput.value) || 3 };
        } else if (wfLoopType.value === "until_condition") {
            loop = { 
                type: "until_condition", 
                breakCondition: wfLoopBreakCondition.value || "" 
            };
        }

        const qualities = {
            creativity: parseFloat(wfQualityCreativity.value),
            depth: parseFloat(wfQualityDepth.value),
            thoroughness: parseFloat(wfQualityThorough.value),
            proactivity: parseFloat(wfQualityProactive.value)
        };

        currentWfSteps[selectedStepIndex] = {
            ...currentWfSteps[selectedStepIndex],
            env_vars: envVars,
            condition: condition,
            loop: loop,
            agent_qualities: qualities
        };

        renderWfCanvas();
        
        // Also update the step list view if it's visible
        renderWfStepsList();
    });

    wfDeleteStepBtn.addEventListener("click", () => {
        if (selectedStepIndex < 0 || selectedStepIndex >= currentWfSteps.length) return;
        currentWfSteps.splice(selectedStepIndex, 1);
        selectedStepIndex = -1;
        stepConfigContainer.style.display = "none";
        renderWfCanvas();
        renderWfStepsList();
    });

    // Canvas resize listener
    window.addEventListener("resize", () => {
        updateWfConnections();
    });

    // ── Boot ─────────────────────────────────────────────────
    connect();

})();

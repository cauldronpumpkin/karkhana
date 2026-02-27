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

    // ── Boot ─────────────────────────────────────────────────
    connect();

})();

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const DEFAULT_CAPABILITIES: &[&str] = &[
    "repo_index",
    "architecture_dossier",
    "gap_analysis",
    "build_task_plan",
    "agent_branch_work",
    "test_verify",
    "sync_remote_state",
];

pub const OPENCODE_SERVER_CAPABILITIES: &[&str] = &[
    "permission_guard",
    "circuit_breaker",
    "litellm_proxy",
    "diff_api",
    "verification_runner",
    "graphify_update",
];

pub const HIGH_AUTONOMY_REQUIRED_CAPABILITIES: &[&str] = OPENCODE_SERVER_CAPABILITIES;

pub const LIMITED_ENGINES: &[&str] = &["opencode", "openclaude", "codex"];

pub const SKIP_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".svelte-kit",
];

pub const SOURCE_SUFFIXES: &[&str] = &[
    ".py", ".js", ".jsx", ".ts", ".tsx", ".svelte", ".go", ".rs", ".java", ".cs", ".php", ".rb",
];

pub const MANIFEST_NAMES: &[&str] = &[
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorkerConfig {
    pub api_base: String,
    #[serde(default = "default_display_name")]
    pub display_name: String,
    #[serde(default = "default_engine")]
    pub engine: String,
    #[serde(default)]
    pub allow_full_control: bool,
    #[serde(default = "default_workspace_root")]
    pub workspace_root: String,
    #[serde(default = "default_poll_seconds")]
    pub poll_seconds: u64,
    #[serde(default = "default_capabilities")]
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub tenant_id: Option<String>,
    #[serde(default)]
    pub openclaude: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub opencode_server_url: Option<String>,
    #[serde(default)]
    pub litellm_port: Option<u16>,
    #[serde(default)]
    pub litellm_config: Option<serde_json::Value>,
}

fn default_display_name() -> String {
    "OpenClaude local worker".to_string()
}

fn default_engine() -> String {
    "openclaude".to_string()
}

fn default_workspace_root() -> String {
    "~/.idearefinery-worker/repos".to_string()
}

fn default_poll_seconds() -> u64 {
    20
}

fn default_capabilities() -> Vec<String> {
    DEFAULT_CAPABILITIES.iter().map(|s| s.to_string()).collect()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorkerState {
    pub api_base: String,
    pub worker_id: String,
    pub api_token: String,
    #[serde(default)]
    pub credentials: WorkerCredentials,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub worker_auth_token: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct WorkerCredentials {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub api_token: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub command_queue_url: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub event_queue_url: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub region: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub access_key_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub secret_access_key: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub session_token: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RegisterRequest {
    pub display_name: String,
    pub machine_name: String,
    pub platform: String,
    pub engine: String,
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub config: HashMap<String, serde_json::Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tenant_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RegisterResponse {
    pub request: RegistrationRequest,
    pub pairing_token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RegistrationRequest {
    pub id: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PairingResponse {
    pub request: RegistrationRequest,
    pub worker: Option<WorkerInfo>,
    pub credentials: Option<WorkerCredentials>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorkerInfo {
    pub id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ClaimRequest {
    pub worker_id: String,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ClaimResponse {
    pub claim: Option<JobClaim>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JobClaim {
    pub job: Job,
    pub project: Project,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Job {
    pub id: String,
    #[serde(rename = "job_type")]
    pub job_type: String,
    #[serde(default)]
    pub claim_token: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Project {
    pub id: String,
    #[serde(rename = "repo_full_name")]
    pub repo_full_name: String,
    #[serde(rename = "clone_url")]
    pub clone_url: String,
    #[serde(default, rename = "default_branch")]
    pub default_branch: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JobUpdateRequest {
    pub worker_id: String,
    pub claim_token: String,
    #[serde(default)]
    pub logs: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JobCompleteRequest {
    pub worker_id: String,
    pub claim_token: String,
    #[serde(default)]
    pub logs: String,
    #[serde(default)]
    pub result: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JobFailRequest {
    pub worker_id: String,
    pub claim_token: String,
    pub error: String,
    #[serde(default = "default_retryable")]
    pub retryable: bool,
    #[serde(default)]
    pub logs: String,
}

fn default_retryable() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FileEntry {
    pub path: String,
    pub size: u64,
    pub kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RepoIndex {
    pub file_inventory: Vec<FileEntry>,
    pub manifests: Vec<Manifest>,
    pub route_map: Vec<RouteEntry>,
    #[serde(default)]
    pub test_commands: Vec<String>,
    #[serde(default)]
    pub risks: Vec<String>,
    #[serde(default)]
    pub todos: Vec<String>,
    #[serde(default)]
    pub searchable_chunks: Vec<String>,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub architecture_summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Manifest {
    pub path: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RouteEntry {
    pub path: String,
    pub line: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct BranchWorkResult {
    pub branch_name: String,
    pub commit_sha: String,
    pub commit_message: String,
    pub agent_output: String,
    pub tests_passed: bool,
    pub full_control_used: bool,
    #[serde(default)]
    pub graphify_updated: bool,
    #[serde(default)]
    pub ledger_updated: bool,
    #[serde(default)]
    pub ledger_sections_updated: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SqsMessageEnvelope {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub job_type: String,
    #[serde(rename = "work_item_id")]
    pub work_item_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct JobFailWithBreakerRequest {
    pub worker_id: String,
    pub claim_token: String,
    pub error: String,
    #[serde(default = "default_retryable")]
    pub retryable: bool,
    #[serde(default)]
    pub logs: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub circuit_breaker_triggered: Option<String>,
}

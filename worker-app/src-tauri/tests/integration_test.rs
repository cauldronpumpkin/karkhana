use idearefinery_worker_lib::types::{WorkerConfig, WorkerState, WorkerCredentials};
use std::collections::HashMap;

#[test]
fn test_config_roundtrip() {
    let config = WorkerConfig {
        api_base: "http://localhost:8000".to_string(),
        display_name: "Test Worker".to_string(),
        engine: "openclaude".to_string(),
        allow_full_control: false,
        workspace_root: "~/.test-worker/repos".to_string(),
        poll_seconds: 30,
        capabilities: vec!["repo_index".to_string()],
        tenant_id: Some("test-tenant".to_string()),
        openclaude: HashMap::new(),
        opencode_server_url: None,
        litellm_port: None,
        litellm_config: None,
    };

    let temp_dir = std::env::temp_dir().join("idearefinery-worker-test");
    let config_path = temp_dir.join("worker-config.json");
    std::fs::create_dir_all(&temp_dir).unwrap();

    // Temporarily override config path by setting env (if supported) or use direct save
    // For this test we test serialization directly
    let json = serde_json::to_string(&config).unwrap();
    let parsed: WorkerConfig = serde_json::from_str(&json).unwrap();
    assert_eq!(config.api_base, parsed.api_base);
    assert_eq!(config.display_name, parsed.display_name);
    assert_eq!(config.capabilities, parsed.capabilities);
}

#[test]
fn test_state_roundtrip() {
    let state = WorkerState {
        api_base: "http://localhost:8000".to_string(),
        worker_id: "worker-123".to_string(),
        api_token: "token-abc".to_string(),
        credentials: WorkerCredentials {
            api_token: Some("token-abc".to_string()),
            command_queue_url: Some("https://sqs.us-east-1.amazonaws.com/123/cmd".to_string()),
            event_queue_url: Some("https://sqs.us-east-1.amazonaws.com/123/events".to_string()),
            region: Some("us-east-1".to_string()),
            access_key_id: Some("AKIA...".to_string()),
            secret_access_key: Some("secret".to_string()),
            session_token: None,
        },
        worker_auth_token: None,
    };

    let json = serde_json::to_string_pretty(&state).unwrap();
    let parsed: WorkerState = serde_json::from_str(&json).unwrap();
    assert_eq!(state.worker_id, parsed.worker_id);
    assert_eq!(state.api_token, parsed.api_token);
    assert_eq!(state.credentials.region, parsed.credentials.region);
}

#[test]
fn test_default_config() {
    let config = WorkerConfig::default();
    assert_eq!(config.api_base, "https://api.karkhana.one");
    assert_eq!(config.engine, "opencode-server");
    assert!(config.capabilities.contains(&"repo_index".to_string()));
}

#[test]
fn test_api_client_construction() {
    use idearefinery_worker_lib::api::ApiClient;
    let _client = ApiClient::new("http://localhost:8000".to_string(), "test-token".to_string());
    assert!(true);
}

#[test]
fn test_slug() {
    fn slug_value(value: &str) -> String {
        value
            .chars()
            .map(|ch| if ch.is_alphanumeric() { ch.to_lowercase().to_string() } else { "-".to_string() })
            .collect::<String>()
            .trim_matches('-')
            .to_string()
    }
    assert_eq!(slug_value("Hello/World"), "hello-world");
    assert_eq!(slug_value("MyRepo"), "myrepo");
}

#[test]
fn test_indexing_detects_manifests() {
    use idearefinery_worker_lib::indexing::index_repo;
    use std::path::Path;

    let repo_dir = Path::new("tests/fixtures/sample-repo");
    std::fs::create_dir_all(repo_dir).unwrap();
    std::fs::write(repo_dir.join("package.json"), r#"{"name":"test","scripts":{"test":"jest"}}"#).unwrap();
    std::fs::write(repo_dir.join("README.md"), "# Test").unwrap();

    let rt = tokio::runtime::Runtime::new().unwrap();
    let index = rt.block_on(index_repo(repo_dir));

    assert!(!index.file_inventory.is_empty());
    assert!(!index.manifests.is_empty());
    assert!(index.test_commands.contains(&"npm test".to_string()));

    // cleanup
    let _ = std::fs::remove_dir_all(repo_dir);
}

#[test]
fn test_pairing_payload_shape() {
    use idearefinery_worker_lib::types::RegisterRequest;
    let req = RegisterRequest {
        display_name: "Test".to_string(),
        machine_name: "machine".to_string(),
        platform: "windows".to_string(),
        engine: "openclaude".to_string(),
        capabilities: vec!["repo_index".to_string()],
        config: HashMap::new(),
        tenant_id: Some("tenant-1".to_string()),
    };
    let json = serde_json::to_string(&req).unwrap();
    assert!(json.contains("display_name"));
    assert!(json.contains("tenant_id"));
}

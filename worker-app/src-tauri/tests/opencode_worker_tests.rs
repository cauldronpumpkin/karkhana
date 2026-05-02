use idearefinery_worker_lib::opencode_session::OpenCodeError;
use idearefinery_worker_lib::worker::{is_opencode_server_engine, opencode_contract_failure};

#[test]
fn opencode_server_engine_detects_only_real_server_mode() {
    assert!(is_opencode_server_engine("opencode-server"));
    assert!(!is_opencode_server_engine("opencode"));
    assert!(!is_opencode_server_engine("openclaude"));
}

#[test]
fn opencode_contract_failure_remains_structured() {
    let failure = opencode_contract_failure(
        "opencode_message_failed",
        "opencode_message",
        "missing payload",
        Some("branch-1".to_string()),
        Some(serde_json::json!({"kind": "test"})),
    );

    assert_eq!(failure.code, "opencode_message_failed");
    assert_eq!(failure.stage, "opencode_message");
    assert_eq!(failure.branch_name.as_deref(), Some("branch-1"));
}

#[test]
fn opencode_error_display_includes_contract_context() {
    let err = OpenCodeError::Contract {
        code: "opencode_health_invalid".to_string(),
        stage: "health".to_string(),
        details: "missing version".to_string(),
    };

    assert!(err.to_string().contains("opencode_health_invalid"));
    assert!(err.to_string().contains("health"));
}

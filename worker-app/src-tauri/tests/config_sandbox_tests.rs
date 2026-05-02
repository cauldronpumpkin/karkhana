use std::fs;
use std::path::PathBuf;

use idearefinery_worker_lib::config::load_config_from_dir;
use idearefinery_worker_lib::sandbox::{remove_agents_md, write_agents_md, AGENTS_MD_CONTENT};

fn temp_dir(name: &str) -> PathBuf {
    let mut dir = std::env::temp_dir();
    dir.push(format!("idearefinery-{}-{}", name, std::process::id()));
    dir
}

#[test]
fn worker_config_defaults_to_opencode_server() {
    let config = idearefinery_worker_lib::types::WorkerConfig::default();
    assert_eq!(config.engine, "opencode-server");
    assert_eq!(config.opencode_server_url.as_deref(), Some("http://127.0.0.1:4096"));
}

#[test]
fn load_config_preserves_missing_engine_as_opencode_server() {
    let dir = temp_dir("config");
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(dir.join("idearefinery-worker")).unwrap();
    fs::write(
        dir.join("idearefinery-worker/worker-config.json"),
        r#"{"api_base":"https://example.com","display_name":"Test Worker"}"#,
    )
    .unwrap();

    let config = load_config_from_dir(&dir);
    assert_eq!(config.engine, "opencode-server");
    assert_eq!(config.opencode_server_url, None);
    assert_eq!(config.display_name, "Test Worker");
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn sandbox_restores_existing_agents_md() {
    let dir = temp_dir("sandbox");
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();
    fs::write(dir.join("AGENTS.md"), "original content").unwrap();

    write_agents_md(&dir).unwrap();
    assert_eq!(fs::read_to_string(dir.join("AGENTS.md")).unwrap(), AGENTS_MD_CONTENT);
    assert!(dir.join("AGENTS.md.bak").exists());

    remove_agents_md(&dir).unwrap();
    assert_eq!(fs::read_to_string(dir.join("AGENTS.md")).unwrap(), "original content");
    assert!(!dir.join("AGENTS.md.bak").exists());
    let _ = fs::remove_dir_all(&dir);
}

use crate::api::ApiClient;
use crate::config::load_config;
use crate::state::StateStore;
use crate::types::{RegisterRequest, WorkerState};
use serde_json::json;
use tauri::{AppHandle, Emitter};
use tokio::time::{sleep, Duration};

#[tauri::command]
pub async fn start_pairing(
    app: AppHandle,
    api_base: String,
    display_name: String,
    tenant_id: Option<String>,
) -> Result<(), String> {
    let config = load_config();
    let client = ApiClient::new(api_base.clone(), String::new());
    let machine_name = hostname::get()
        .ok()
        .and_then(|h| h.into_string().ok())
        .unwrap_or_else(|| "local-worker".to_string());
    let platform = format!("{} {}", std::env::consts::OS, std::env::consts::ARCH);

    let req = RegisterRequest {
        display_name: display_name.clone(),
        machine_name,
        platform,
        engine: config.engine.clone(),
        capabilities: config.capabilities.clone(),
        config: {
            let mut map = std::collections::HashMap::new();
            map.insert(
                "autonomy".to_string(),
                serde_json::Value::String("branch_pr".to_string()),
            );
            map.insert(
                "allow_full_control".to_string(),
                serde_json::Value::Bool(config.allow_full_control),
            );
            map.insert(
                "openclaude".to_string(),
                serde_json::Value::Object(
                    config
                        .openclaude
                        .into_iter()
                        .map(|(k, v)| (k, v))
                        .collect(),
                ),
            );
            map
        },
        tenant_id: tenant_id.clone(),
    };

    let registered = client.register(&req).await.map_err(|e| e.to_string())?;
    let request_id = registered.request.id.clone();
    let pairing_token = registered.pairing_token.clone();

    app.emit("pairing-status-changed", json!({"status": "waiting", "request_id": request_id}))
        .map_err(|e| e.to_string())?;

    let state_store = StateStore::new();

    loop {
        sleep(Duration::from_secs(5)).await;
        let status = client
            .get_registration(&request_id, &pairing_token)
            .await
            .map_err(|e| e.to_string())?;

        match status.request.status.as_str() {
            "approved" => {
                let credentials = status.credentials.ok_or("No credentials returned")?;
                let worker = status.worker.ok_or("No worker returned")?;
                let api_token = credentials.api_token.clone().ok_or("No API token returned")?;
                let state = WorkerState {
                    api_base: api_base.clone(),
                    worker_id: worker.id.clone(),
                    api_token: api_token.clone(),
                    credentials: credentials.clone(),
                    worker_auth_token: None,
                };
                state_store.save(&state).map_err(|e| e.to_string())?;
                app.emit(
                    "pairing-status-changed",
                    json!({"status": "approved", "worker_id": worker.id}),
                )
                .map_err(|e| e.to_string())?;
                return Ok(());
            }
            "denied" => {
                let reason = "Pairing denied".to_string();
                app.emit(
                    "pairing-status-changed",
                    json!({"status": "denied", "reason": reason}),
                )
                .map_err(|e| e.to_string())?;
                return Err(reason);
            }
            _ => {
                app.emit(
                    "pairing-status-changed",
                    json!({"status": "waiting"}),
                )
                .map_err(|e| e.to_string())?;
            }
        }
    }
}

#[tauri::command]
pub async fn pair_with_dev_token(
    app: AppHandle,
    api_base: String,
    worker_auth_token: String,
    worker_id: String,
) -> Result<(), String> {
    let state_store = StateStore::new();
    let state = WorkerState {
        api_base: api_base.clone(),
        worker_id: worker_id.clone(),
        api_token: worker_auth_token.clone(),
        credentials: crate::types::WorkerCredentials::default(),
        worker_auth_token: Some(worker_auth_token),
    };
    state_store.save(&state).map_err(|e| e.to_string())?;
    app.emit(
        "pairing-status-changed",
        json!({"status": "dev_paired", "worker_id": worker_id}),
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

use crate::state::StateStore;
use crate::types::WorkerState;
use serde_json::json;
use std::collections::HashMap;
use tauri::{AppHandle, Emitter};
use url::Url;

#[tauri::command]
pub async fn pair_with_invite_link(
    app: AppHandle,
    invite_link: String,
) -> Result<(), String> {
    let parsed = Url::parse(&invite_link).map_err(|e| format!("Invalid invite link: {e}"))?;

    if parsed.scheme() != "idearefinery" || parsed.host_str() != Some("connect") {
        return Err("Invalid invite link: must start with idearefinery://connect".to_string());
    }

    let params: HashMap<String, String> = parsed.query_pairs().map(|(k, v)| (k.to_string(), v.to_string())).collect();

    let api_base = params
        .get("api_base")
        .or_else(|| params.get("api"))
        .ok_or_else(|| "Missing api_base in invite link".to_string())?;

    let token = params
        .get("token")
        .or_else(|| params.get("t"))
        .ok_or_else(|| "Missing token in invite link".to_string())?;

    let worker_id = params
        .get("worker_id")
        .or_else(|| params.get("w"))
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            hostname::get()
                .ok()
                .and_then(|h| h.into_string().ok())
                .unwrap_or_else(|| "local-worker".to_string())
        });

    let state_store = StateStore::new();
    let state = WorkerState {
        api_base: api_base.clone(),
        worker_id,
        api_token: token.clone(),
        credentials: crate::types::WorkerCredentials::default(),
        worker_auth_token: Some(token.clone()),
    };
    state_store.save(&state).map_err(|e| e.to_string())?;
    app.emit(
        "pairing-status-changed",
        json!({"status": "dev_paired", "worker_id": state.worker_id}),
    )
    .map_err(|e| e.to_string())?;
    Ok(())
}

use serde_json;
use tauri::{AppHandle, Emitter};
use tauri_plugin_updater::UpdaterExt;

pub async fn check_for_updates(app: AppHandle) -> Result<(), String> {
    let updater = app.updater().map_err(|e| e.to_string())?;
    match updater.check().await {
        Ok(Some(update)) => {
            let _ = app.emit("update-available", serde_json::json!({
                "version": update.version,
                "notes": update.body,
            }));
            Ok(())
        }
        Ok(None) => {
            let _ = app.emit("update-available", serde_json::json!({"version": null}));
            Ok(())
        }
        Err(e) => Err(e.to_string()),
    }
}

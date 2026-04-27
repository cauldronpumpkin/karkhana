pub mod agent;
pub mod api;
pub mod branch_work;
pub mod circuit_breaker;
pub mod config;
pub mod error;
pub mod git;
pub mod indexing;
pub mod litellm;
pub mod opencode_session;
pub mod pairing;
pub mod retry;
pub mod sandbox;
pub mod sqs;
pub mod state;
pub mod tray;
pub mod types;
pub mod updater;
pub mod worker;

#[tauri::command]
async fn check_updates(app: tauri::AppHandle) -> Result<(), String> {
    updater::check_for_updates(app).await
}

#[tauri::command]
fn toggle_autostart(app: tauri::AppHandle, enable: bool) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    let manager = app.autolaunch();
    if enable {
        manager.enable().map_err(|e| e.to_string())
    } else {
        manager.disable().map_err(|e| e.to_string())
    }
}

#[tauri::command]
fn is_autostart_enabled(app: tauri::AppHandle) -> Result<bool, String> {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().is_enabled().map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--hidden"]),
        ))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            tray::setup_tray(app)?;
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let _ = updater::check_for_updates(app_handle).await;
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            pairing::pair_with_invite_link,
            worker::start_worker,
            worker::stop_worker,
            worker::get_worker_status,
            config::load_config_command,
            config::save_config_command,
            check_updates,
            toggle_autostart,
            is_autostart_enabled,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

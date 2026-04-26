use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{App, AppHandle, Emitter, Manager};

pub fn setup_tray(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let open_dashboard = tauri::menu::MenuItem::with_id(app, "open_dashboard", "Open Dashboard", true, None::<&str>)?;
    let start_stop = tauri::menu::MenuItem::with_id(app, "start_stop", "Start Worker", true, None::<&str>)?;
    let autostart = tauri::menu::MenuItem::with_id(app, "autostart", "Start at Login", true, None::<&str>)?;
    let check_updates = tauri::menu::MenuItem::with_id(app, "check_updates", "Check for Updates", true, None::<&str>)?;
    let separator = tauri::menu::PredefinedMenuItem::separator(app)?;
    let quit = tauri::menu::MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    let menu = tauri::menu::Menu::with_items(app, &[
        &open_dashboard,
        &start_stop,
        &autostart,
        &check_updates,
        &separator,
        &quit,
    ])?;

    TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open_dashboard" => {
                show_dashboard(app);
            }
            "start_stop" => {
                let _ = app.emit("tray-toggle-worker", ());
            }
            "autostart" => {
                let _ = app.emit("tray-toggle-autostart", ());
            }
            "check_updates" => {
                let _ = app.emit("tray-check-updates", ());
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                show_dashboard(tray.app_handle());
            }
        })
        .build(app)?;

    Ok(())
}

fn show_dashboard(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

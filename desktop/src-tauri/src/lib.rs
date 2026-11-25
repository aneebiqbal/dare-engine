//! Clipdesk Missions desktop shell.
//!
//! The window loads the app (the cloud URL, or a locally started stack). The Rust
//! side owns the two things a browser cannot do: start the local engine and
//! record the screen with FFmpeg. Everything heavy runs on this machine.

use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::State;

struct Capture(Mutex<Option<Child>>);

/// The URL the window opens. Defaults to a locally started stack.
#[tauri::command]
fn app_url() -> String {
    std::env::var("CLIPDESK_APP_URL").unwrap_or_else(|_| "http://localhost:3100".into())
}

/// The repo directory that holds docker-compose.yml.
#[tauri::command]
fn app_home() -> String {
    std::env::var("CLIPDESK_HOME")
        .unwrap_or_else(|_| format!("{}/..", env!("CARGO_MANIFEST_DIR")))
}

/// Start the local stack (database, API, worker, web) in the repo directory.
#[tauri::command]
fn start_stack() -> Result<String, String> {
    let out = Command::new("docker")
        .args(["compose", "up", "-d", "--wait", "--build"])
        .current_dir(app_home())
        .output()
        .map_err(|e| format!("could not run docker compose: {e}"))?;
    if !out.status.success() {
        return Err(String::from_utf8_lossy(&out.stderr).trim().to_string());
    }
    Ok("started".into())
}

/// Record the screen with FFmpeg (avfoundation). `device` is "display:audio",
/// default "1:0". The file stays on this machine.
#[tauri::command]
fn capture_start(out_path: String, device: Option<String>, state: State<Capture>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|_| "capture state poisoned".to_string())?;
    if guard.is_some() {
        return Err("already recording".into());
    }
    let device = device.unwrap_or_else(|| "1:0".into());
    let child = Command::new("ffmpeg")
        .args(["-hide_banner", "-f", "avfoundation", "-i", &device, "-y", &out_path])
        .spawn()
        .map_err(|e| format!("could not start ffmpeg: {e}"))?;
    *guard = Some(child);
    Ok(out_path)
}

/// Stop the recording with SIGINT so FFmpeg finalises the MP4 cleanly.
#[tauri::command]
fn capture_stop(state: State<Capture>) -> Result<String, String> {
    let mut guard = state.0.lock().map_err(|_| "capture state poisoned".to_string())?;
    let child = guard.take().ok_or_else(|| "not recording".to_string())?;
    let pid = child.id();
    let _ = Command::new("kill").args(["-INT", &pid.to_string()]).status();
    Ok("stopped".into())
}

/// Read a recording back to the web UI (base64) so it can be uploaded to the
/// studio without the browser touching the filesystem.
#[tauri::command]
fn read_file_b64(path: String) -> Result<String, String> {
    use base64::Engine as _;
    let bytes = std::fs::read(&path).map_err(|e| format!("could not read {path}: {e}"))?;
    Ok(base64::engine::general_purpose::STANDARD.encode(bytes))
}

/// Where recordings made in the app are stored.
#[tauri::command]
fn recordings_dir() -> Result<String, String> {
    let home = std::env::var("HOME").map_err(|_| "no HOME".to_string())?;
    let dir = std::path::Path::new(&home).join(".clipdesk").join("recordings");
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.to_string_lossy().into_owned())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(Capture(Mutex::new(None)))
        .setup(|app| {
            let url = app_url();
            if let Ok(parsed) = url.parse::<tauri::Url>() {
                let _ = tauri::WebviewWindowBuilder::new(
                    app,
                    "app",
                    tauri::WebviewUrl::External(parsed),
                )
                .title("Clipdesk Missions")
                .inner_size(1440.0, 900.0)
                .build();
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            app_url,
            app_home,
            start_stack,
            capture_start,
            capture_stop,
            read_file_b64,
            recordings_dir
        ])
        .run(tauri::generate_context!())
        .expect("error while running Clipdesk Missions");
}

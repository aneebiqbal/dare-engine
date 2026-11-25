fn main() {
    // App commands are ACL-managed: this autogenerates allow-/deny- permissions
    // for each command, which `capabilities/default.json` then grants to the
    // `app` window.
    let attributes = tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "app_url",
            "app_home",
            "start_stack",
            "capture_start",
            "capture_stop",
            "read_file_b64",
            "recordings_dir",
        ]),
    );
    tauri_build::try_build(attributes).expect("failed to build Tauri");
}

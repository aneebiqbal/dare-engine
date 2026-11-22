// Fallback loader: if the Rust window did not open, point the browser at the app.
const url = window.__CLIPDESK_APP_URL__ ?? "http://localhost:3100";
if (!window.__TAURI_INTERNALS__) {
  window.location.href = url;
}

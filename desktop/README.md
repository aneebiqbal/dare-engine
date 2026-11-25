# Clipdesk Missions — desktop app

A Tauri shell for the admin's local engine. It opens the web app in a native
window and adds the two things a browser cannot do: start the local stack and
record the screen. See `docs/desktop-app.md`.

```sh
npm install
npm run tauri build
# desktop/src-tauri/target/release/bundle/dmg/Clipdesk Missions_0.1.0_aarch64.dmg
```

`icon-src.png` is the source for `src-tauri/icons` (already committed). Regenerate
with `npx tauri icon icon-src.png`.

Environment:

- `CLIPDESK_APP_URL` — the URL the window opens (default `http://localhost:3100`).
- `CLIPDESK_HOME` — where `docker compose up` runs (default: the repo).

# The desktop app

One application for the admin's heavy half: the local engine, the capture, the
SSD import and the Models screen. It talks to the same cloud API and database as
the website. See `docs/architecture.md` for why the split exists.

## What it is

A [Tauri](https://tauri.app) shell (Rust + the system web view), not Electron.
The released macOS build is **~2.4 MB**, against Electron's ~150 MB, and it uses
the Mac's own web view. The window loads the app — the cloud URL, or a locally
started stack — so the existing web UI is reused rather than rewritten.

## Build it (macOS, Apple Silicon)

```sh
cd desktop
npm install
npx tauri icon icon-src.png          # generates src-tauri/icons (already committed)
npm run tauri build
```

Artifact:

```
desktop/src-tauri/target/release/bundle/dmg/Clipdesk Missions_0.1.0_aarch64.dmg
```

Open the `.dmg` and drag **Clipdesk Missions** to Applications. The build is
unsigned; macOS will ask you to confirm the first open. A released build needs an
Apple Developer certificate for signing and notarisation — see below.

`make desktop` runs the same build from the repo root.

## What it does

| Command | What it does |
| --- | --- |
| `app_url` | The URL the window opens. `CLIPDESK_APP_URL`, default `http://localhost:3100`. |
| `start_stack` | `docker compose up -d --wait --build` in `CLIPDESK_HOME` (or the repo it was built from). |
| `capture_start` / `capture_stop` | Records the screen with FFmpeg (`avfoundation`). Stop sends SIGINT so the MP4 finalises cleanly. |
| `read_file_b64` | Reads a recording back to the web UI so it can be uploaded to the studio. |
| `recordings_dir` | `~/.clipdesk/recordings`, created on demand. |

The **Desktop engine** card appears in the Studio only inside the app (in a
browser it is absent). It offers **Start local engine**, **Record screen**, and
imports the recording straight into the studio.

## Capture: OBS and no-OBS

Two paths, because a user should not have to set up OBS before they can record:

1. **OBS (the reliable default).** The web UI's **Go Live** page connects to a
   running OBS over obs-websocket 5.x and shows the real connection, stream,
   record, scene and mic state. OBS does the capture; the platform does the
   clipping. This is the proven path (tested against OBS 33.0.1).
2. **No OBS (bundled recorder).** The desktop app's **Record screen** button
   records with FFmpeg `avfoundation`. It writes a file on this Mac and imports
   it into the studio. No scene setup, no WebSocket, one click.

We do not reinvent OBS. OBS is the default; the bundled recorder is the fallback.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLIPDESK_APP_URL` | `http://localhost:3100` | The URL the window opens. Set it to the cloud origin to use the app as a desktop client of the cloud. |
| `CLIPDESK_HOME` | the repo it was built from | Where `docker compose up` runs. |

## Download page

`/landing` is the public download page. It reads three environment slots and
shows an honest `NEXT_PUBLIC_*` placeholder until they are filled:

| Variable | Meaning |
| --- | --- |
| `NEXT_PUBLIC_DOWNLOAD_MAC` | The `.dmg` download URL. |
| `NEXT_PUBLIC_DOWNLOAD_WINDOWS` | The Windows installer URL. |
| `NEXT_PUBLIC_WEB_PORTAL` | The deployed web origin (also linked in the header). |
| `NEXT_PUBLIC_DEMO_CLIP` | A real demo clip (mp4) recorded from a real run. |

`docs/desktop-app.md` and `docs/deploy-web.md` say where those artifacts come
from. Never commit a real URL as a build artifact; set it in the deploy
environment.

## Windows

Tauri can bundle a Windows installer (`.exe` / `.msi`) on a Windows machine.
A macOS host cannot cross-compile it; build it on Windows or in a Windows CI
runner. The Rust commands are cross-platform except `capture_start`, which uses
macOS `avfoundation`.

### Build on Windows

```powershell
cd desktop
npm install
npm run tauri build
```

Artifact:

```
desktop\src-tauri\target\release\bundle\nsis\Clipdesk Missions_0.1.0_x64_en-US.msi
desktop\src-tauri\target\release\bundle\msix\Clipdesk Missions_0.1.0_x64.msix
```

### Capture on Windows

Replace the macOS capture with FFmpeg's Windows grabbers in
`desktop/src-tauri/src/lib.rs`:

| macOS | Windows |
| --- | --- |
| `-f avfoundation` | `-f gdigrab` (screen) or `-f dshow` (capture card) |
| `kill -INT <pid>` to finalise | send `CTRL_C_EVENT` / terminate cleanly |

### Signing (required before distribution)

An unsigned Windows installer triggers SmartScreen. Buy a code-signing
certificate (OV or EV) and sign both artifacts:

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  "desktop\src-tauri\target\release\bundle\nsis\Clipdesk Missions_0.1.0_x64_en-US.msi"
```

EV certificates give immediate SmartScreen reputation; OV needs reputation to
build. This path is **documented, not built or tested** — it needs a Windows
machine and a certificate.

## What is proven, and what is not

**Proven here:** the app builds, the `.dmg` mounts and verifies, the Rust
commands compile, and the web UI calls them only inside the app.

**Not proven:** launching the `.app` on a real desktop, an actual OBS session
through the app, a real screen recording, and code signing. Those need a human
at a Mac. Do not call the desktop capture finished until someone has recorded a
real clip with it.

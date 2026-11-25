// PM2 deployment for the cloud half: FastAPI (api/) + Next.js standalone (web/).
// The worker engine, relay, desktop shell and local bridges are not part of this
// process list — they do not run on the web host.
//
//   pm2 start ecosystem.config.cjs
//   pm2 save            # persist across reboots (then: pm2 startup)
//
// Ports are overridable for local checks:
//   API_PORT=8010 WEB_PORT=3200 pm2 start ecosystem.config.cjs
module.exports = {
  apps: [
    {
      name: "clipdesk-api",
      namespace: "clipdesk",
      cwd: __dirname,
      script: ".venv/bin/python",
      args: `-m uvicorn --app-dir ${__dirname}/api app.main:app --host 127.0.0.1 --port ${process.env.API_PORT || "8000"}`,
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 3000,
      env: {
        PYTHONUNBUFFERED: "1",
        NODE_ENV: "production",
        // app.main imports `llm_shared`, `key_crypto` and `platforms` as
        // top-level modules; the images copy them beside the app, bare metal
        // gets shims from scripts/setup-pm2.sh into .pm2/py.
        PYTHONPATH: `${__dirname}/.pm2/py:${__dirname}/api`,
      },
    },
    {
      name: "clipdesk-web",
      namespace: "clipdesk",
      // next build (output: standalone) emits .next/standalone/server.js; the
      // build script copies .next/static and public/ beside it.
      cwd: `${__dirname}/web/.next/standalone`,
      script: "server.js",
      interpreter: "node",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 3000,
      env: {
        NODE_ENV: "production",
        PORT: process.env.WEB_PORT || "3100",
        HOSTNAME: "127.0.0.1",
        // Server-side /api proxy target.
        API_URL: `http://127.0.0.1:${process.env.API_PORT || "8000"}`,
      },
    },
  ],
};

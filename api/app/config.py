from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database --------------------------------------------------------
    # Pooled connection for the API; direct connection for migrations and the
    # job worker. On Neon the pooled host has `-pooler` in it; on Aiven the
    # service URI is direct and a pooler host is optional.
    database_url: str = "postgresql://clipdesk:clipdesk@db:5432/clipdesk"
    database_url_direct: str = ""

    # --- Sessions / cookies ---------------------------------------------
    session_secret: str = "change-me"
    cookie_secure: bool = False
    session_cookie: str = "clipdesk_session"
    csrf_cookie: str = "clipdesk_csrf"

    app_env: str = "development"
    web_origin: str = "http://localhost:3100"

    # --- Sign-up --------------------------------------------------------
    invite_required: bool = True

    # --- Development sign-in (tests only) -------------------------------
    dev_auth_enabled: bool = False

    # --- Storage ---------------------------------------------------------
    storage_driver: str = "local"          # local | s3
    storage_local_dir: str = "/data/storage"
    s3_endpoint: str = "http://storage:9090"
    s3_bucket: str = "clipdesk"
    s3_access_key: str = "clipdesk"
    s3_secret_key: str = "clipdesk-dev-secret"
    s3_region: str = "us-east-1"

    # --- AI --------------------------------------------------------------
    # One OpenAI-compatible chat-completions client. Change these three values
    # to move between OpenCode Zen, xAI Grok, or any compatible provider.
    llm_provider: str = "recorded"         # openai | recorded | stub
    llm_base_url: str = "https://opencode.ai/zen/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_recorded_response: str = "/app/app/llm_recorded.json"
    llm_timeout: int = 60

    # --- Voice-over ------------------------------------------------------
    # Piper is MIT (rhasspy/piper). The voice model is downloaded separately.
    tts_command: str = "piper"
    tts_voice: str = "en_US-amy-medium"
    tts_model_dir: str = "/data/voices"

    # --- Uploads ---------------------------------------------------------
    upload_tmp_dir: str = "/tmp/clipdesk-uploads"
    # Days to keep a raw recording after its clips were made.
    recording_retention_days: int = 7

    # --- Research brain ---------------------------------------------------
    # All optional: with no keys the brain runs on the recorded sample feed and
    # marks its output as a fallback. Never a secret in a log or response.
    rawg_api_key: str = ""
    youtube_api_key: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_username: str = ""
    reddit_password: str = ""
    reddit_user_agent: str = "clipdesk-research/0.1"
    research_enabled: bool = True
    research_hour: int = 5
    research_timezone: str = "UTC"

    # --- Relay -----------------------------------------------------------
    # Optional shared secret for relay hooks; the stream key is always checked.
    relay_hook_secret: str = ""

    @property
    def direct_url(self) -> str:
        return self.database_url_direct or self.database_url

    @property
    def cookies_secure(self) -> bool:
        return self.cookie_secure or self.app_env == "production"

    @property
    def ai_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)


settings = Settings()

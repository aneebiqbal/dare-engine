from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://clipdesk:clipdesk@db:5432/clipdesk"

    s3_endpoint: str = "http://storage:9090"
    s3_bucket: str = "clipdesk"
    s3_access_key: str = "clipdesk"
    s3_secret_key: str = "clipdesk-dev-secret"
    s3_region: str = "us-east-1"

    llm_provider: str = "stub"
    llm_recorded_response: str = ""
    gemini_api_key: str = ""

    # Development sign-in. Refuses to start in production when enabled.
    dev_auth_enabled: bool = False
    app_env: str = "development"

    @property
    def session_cookie(self) -> str:
        return "clipdesk_session"


settings = Settings()

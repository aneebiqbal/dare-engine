from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://clipdesk:clipdesk@db:5432/clipdesk"
    database_url_direct: str = ""
    # Same value as the API: the key-store encryption key is derived from it.
    session_secret: str = ""

    storage_driver: str = "local"
    storage_local_dir: str = "/data/storage"
    s3_endpoint: str = "http://storage:9090"
    s3_bucket: str = "clipdesk"
    s3_access_key: str = "clipdesk"
    s3_secret_key: str = "clipdesk-dev-secret"
    s3_region: str = "us-east-1"

    llm_provider: str = "stub"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: int = 60

    tts_command: str = "piper"
    tts_voice: str = "en_US-amy-medium"
    tts_model_dir: str = "/data/voices"

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    # Host MLX Whisper bridge. Empty = use faster-whisper in the container.
    mlx_whisper_url: str = ""
    mlx_whisper_model: str = "mlx-community/whisper-large-v3-mlx"
    # The same host bridge also serves the vision model (Ollama).
    model_bridge_url: str = "http://host.docker.internal:8798"
    vision_model: str = "qwen2.5vl:7b"
    # Local chat model used by the moment scorer (Ollama on the Mac).
    ollama_url: str = "http://host.docker.internal:11434"
    scoring_model: str = "qwen2.5-coder:14b"
    score_temperature: float = 0.75
    rerank_temperature: float = 0.3
    skills_dir: str = "/app/skills/clip-scoring"
    score_batch: int = 1

    @property
    def direct_url(self) -> str:
        return self.database_url_direct or self.database_url


settings = Settings()

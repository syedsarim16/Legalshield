from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Security
    jwt_secret: str = "change-me-in-production"
    data_encryption_key: str = ""  # optional; derived from jwt_secret when empty
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    # OTP
    otp_minutes: int = 1
    otp_max_attempts: int = 5
    otp_rate_limit: int = 3
    otp_rate_window_minutes: int = 10
    debug_return_otp: bool = False  # DEV ONLY: returns the OTP in the API response

    # Rate limits
    chat_rate_limit_per_hour: int = 30
    login_attempts_per_10_min: int = 10

    # Uploads
    max_upload_mb: int = 5

    # Firebase
    firebase_google_services_file: str = "google-services (1).json"
    firebase_service_account_json: str = ""
    google_application_credentials: str = ""
    firebase_storage_bucket: str = ""
    firebase_web_vapid_key: str = ""

    # AI / chatbot
    llm_provider: str = "mock"  # mock | anthropic
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"
    llm_timeout_seconds: int = 20
    retrieval_min_score: float = 1.0

    # Legal data safety: only advisor-reviewed statutes are served unless this is true
    allow_unreviewed_statutes: bool = False


settings = Settings()

import os
import secrets
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "EUROGRIP PITSTOP OS API"
    database_url: str = "sqlite:///./pitstop_dev.db"
    jwt_secret: str = "replace-this-with-a-long-random-secret-before-any-shared-deployment"
    jwt_issuer: str = "eurogrip-pitstop-os"
    jwt_audience: str = "eurogrip-pitstop-api"
    rate_limit_per_minute: int = Field(default=120, ge=10, le=5000)
    auth_rate_limit_per_minute: int = Field(default=10, ge=2, le=100)
    audit_log_enabled: bool = True
    client_fingerprint_secret: str = "replace-this-fingerprint-secret"
    jwt_ttl_minutes: int = 60
    otp_ttl_minutes: int = 5
    otp_retention_hours: int = Field(default=0, ge=0, le=87600)
    security_audit_retention_days: int = Field(default=0, ge=0, le=36500)
    user_activity_retention_days: int = Field(default=0, ge=0, le=36500)
    otp_dev_return_code: bool = True
    cors_origins: str = "http://localhost:5173"
    passport_public_base_url: str = "http://localhost:8000"
    public_api_base_url: str = "http://localhost:8000"
    trustvision_storage_dir: str = "./var/trustvision"
    object_storage_backend: str = "local"
    object_storage_local_dir: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_prefix: str = "pitstop"
    s3_endpoint_url: str = ""
    s3_server_side_encryption: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    redis_url: str = ""
    sms_provider: str = "none"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    cloud_service_name: str = "pitstop-api"
    cloud_log_level: str = "INFO"
    metrics_token: str = ""
    trustvision_max_upload_bytes: int = 10485760
    trustvision_ocr_enabled: bool = True
    rag_embedding_provider: str = "hashing"
    rag_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_embedding_dimensions: int = 384
    rag_chunk_chars: int = 1200
    rag_chunk_overlap: int = 180
    rag_top_k: int = 5
    rag_min_similarity: float = 0.12
    rag_llm_base_url: str = ""
    rag_llm_api_key: str = ""
    rag_llm_model: str = ""
    rag_llm_timeout_seconds: int = 25
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if self.object_storage_backend not in ("local", "s3"):
            raise ValueError("OBJECT_STORAGE_BACKEND must be local or s3.")
        if self.object_storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required when S3 storage is enabled.")
        if self.app_env.lower() in ("production", "prod"):
            weak = (
                len(self.jwt_secret) < 32
                or self.jwt_secret.startswith("replace-this")
                or len(self.client_fingerprint_secret) < 32
                or self.client_fingerprint_secret.startswith("replace-this")
                or self.otp_dev_return_code
                or not self.redis_url
                or "*" in self.cors_origins
                or self.sms_provider not in ("twilio",)
                or not self.twilio_account_sid
                or not self.twilio_auth_token
                or not self.twilio_from_number
                or len(self.metrics_token) < 32
                or self.object_storage_backend != "s3"
                or not self.s3_access_key_id
                or not self.s3_secret_access_key
            )
            if weak:
                raise ValueError("Production requires strong secrets, Redis, explicit CORS, disabled development OTP, configured Twilio SMS credentials, a metrics bearer token, and dedicated S3 credentials.")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

settings = Settings()

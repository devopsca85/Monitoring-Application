from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Azure Monitoring Solution"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "monitoring_db"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Azure Key Vault
    AZURE_KEY_VAULT_URL: str = ""

    # Azure Communication Services (Email)
    AZURE_COMM_CONNECTION_STRING: str = ""
    AZURE_COMM_SENDER_EMAIL: str = "DoNotReply@monitoring.com"

    # Teams Webhook
    TEAMS_WEBHOOK_URL: str = ""

    # Azure Application Insights
    APPINSIGHTS_CONNECTION_STRING: str = ""

    # Monitoring Engine
    MONITORING_ENGINE_URL: str = "http://localhost:8001"

    # Encryption key for stored credentials
    CREDENTIAL_ENCRYPTION_KEY: str = "change-me-32-byte-key-here!!"

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()

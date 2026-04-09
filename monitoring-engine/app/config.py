from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BACKEND_API_URL: str = "http://localhost:8000/api/v1"
    SCREENSHOT_DIR: str = "/tmp/screenshots"
    BROWSER_TIMEOUT_MS: int = 30000
    model_config = {"env_file": ".env"}


settings = Settings()

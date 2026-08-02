from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://alphafood:changeme@db:5432/alphafood"
    secret_key: str = "changeme-please-set-a-real-secret"
    jwt_expire_hours: int = 24
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    scrape_interval_hours: int = 24
    scrape_concurrency: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    links_service_url: str = "http://links:8012"
    service_name: str = "tracker"
    port: int = 8013
    debug: bool = False


settings = Settings()

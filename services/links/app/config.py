from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    encryption_key: str
    catalog_service_url: str = "http://catalog:8011"
    service_name: str = "links"
    port: int = 8012
    debug: bool = False


settings = Settings()

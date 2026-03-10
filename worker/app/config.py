from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    catalog_db_url: str = ""
    links_db_url: str = ""
    tracker_db_url: str = ""
    analytics_db_url: str = ""
    catalog_service_url: str = "http://catalog:8011"
    links_service_url: str = "http://links:8012"
    tracker_service_url: str = "http://tracker:8013"
    analytics_service_url: str = "http://analytics:8014"
    prism_content_url: str = "http://content:8007"
    encryption_key: str = ""


settings = Settings()

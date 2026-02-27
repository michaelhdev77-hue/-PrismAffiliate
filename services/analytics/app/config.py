from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    tracker_service_url: str = "http://tracker:8013"
    catalog_service_url: str = "http://catalog:8011"
    links_service_url: str = "http://links:8012"
    secret_key: str
    service_name: str = "analytics"
    port: int = 8014
    debug: bool = False


settings = Settings()

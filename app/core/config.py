from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "My Sarcasm API"
    # The published origin. The static build writes it into CNAME and resolves
    # every redirect against it.
    site_url: str = "https://www.snarkapi.com/"

    # Pydantic v2 style configuration (avoids deprecation warnings in tests)
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    app_name: str = "Greenhouse Control API"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # db 
    database_url: str = "sqlite:///./app.db"

    # cors
    cors_allow_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # app boot mode
    app_mode: str = "NORMAL"

    # Gemini API Key
    gemini_api_key: str = "AIzaSyCMnN7EHR5KhE-g_qB44aAQpjP8PCNRVhw"

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

config = Config()

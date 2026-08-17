from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    central_id: str = "CENTRAL-001"
    central_name: str = "Central de Processamento"
    timezone: str = "America/Sao_Paulo"

    central_db_url: str = "postgresql://vision:change-me@localhost:5432/vision_central"
    central_api_host: str = "0.0.0.0"
    central_api_port: int = 8081
    central_api_token: str = "change-me"

    local_api_base_url: str = "http://192.168.1.10:8080"
    local_api_token: str = "change-me"

    collector_interval_ms: int = 60000


settings = Settings()

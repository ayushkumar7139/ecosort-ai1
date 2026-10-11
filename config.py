from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    dynamodb_table: str = "ecosort-scans"
    s3_bucket: str = "ecosort-images"
    demo_mode: bool = False
    ai_provider: str = "huggingface"  # 'huggingface', 'bedrock', 'demo'
    huggingface_token: str = ""
    huggingface_model: str = "google/vit-base-patch16-224"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_mb: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

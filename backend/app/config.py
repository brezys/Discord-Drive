from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "changeme"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "latent_assets"
    thumb_dir: str = "/app/thumbs"
    image_dir: str = "/app/images"
    store_full_images: bool = False
    embed_model: str = "ViT-B-32"
    embed_pretrained: str = "openai"
    embed_dim: int = 512
    thumb_size: tuple[int, int] = (256, 256)


settings = Settings()

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... (existant)
    DATABASE_URL: str
    
    # --- AJOUT ---
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    OPENROUTER_API_KEY: str
    # -------------

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
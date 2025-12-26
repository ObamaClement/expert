from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Classe pour gérer la configuration de l'application.
    Les variables sont chargées depuis le fichier .env.
    """
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
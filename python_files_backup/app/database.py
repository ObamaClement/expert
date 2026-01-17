from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

# L'objet 'engine' est le point d'entrée principal pour communiquer avec la BDD.
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping=True # Option utile en production
)

# La 'SessionLocal' est une "usine" à sessions de base de données.
# Chaque fois que nous aurons besoin de parler à la BDD, nous demanderons une session à cette usine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from sqlalchemy.orm import declarative_base

# Cette instance de 'declarative_base' est le catalogue central où SQLAlchemy
# enregistrera toutes les classes de modèles que nous définirons.
# C'est ce que Alembic utilisera pour comparer l'état de notre code
# avec l'état de la base de données.
Base = declarative_base()
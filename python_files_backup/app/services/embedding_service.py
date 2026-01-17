from sentence_transformers import SentenceTransformer
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service pour générer des embeddings (vecteurs) à partir de texte.
    Utilise le modèle 'all-MiniLM-L6-v2' qui est un excellent compromis
    rapidité/qualité pour l'anglais et le français technique.
    """
    
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            logger.info("Initialisation du modèle d'embedding...")
            # Chargement du modèle. On essaie sans le préfixe 'sentence-transformers/'
            # Si cela échoue encore, nous essaierons une autre approche.
            try:
                cls._model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Erreur chargement modèle 'all-MiniLM-L6-v2': {e}")
                # Tentative de repli explicite
                cls._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            
            logger.info("Modèle d'embedding chargé avec succès.")
        return cls._instance

    def get_text_embedding(self, text: str) -> list:
        """
        Génère un vecteur d'embedding pour une chaîne de caractères donnée.
        
        :param text: Le texte à vectoriser.
        :return: Une liste de flottants (le vecteur).
        """
        if not text or not isinstance(text, str):
            return None
            
        try:
            # Le modèle retourne un numpy array, on le convertit en liste simple
            # pour qu'il soit compatible avec pgvector et JSON.
            embedding = self._model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Erreur lors de la vectorisation du texte : {e}")
            return None

# Instance globale prête à l'emploi
embedding_service = EmbeddingService()
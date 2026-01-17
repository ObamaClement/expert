from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

class BaseIntegrator(ABC):
    """
    Classe de base abstraite (blueprint) pour tous les intégrateurs de datasets.
    
    Elle impose une structure ETL (Extract, Transform, Load) cohérente pour
    garantir que chaque script d'importation fonctionne de la même manière.
    """

    def __init__(self, db_session: Session, dataset_path: str):
        """
        Initialise l'intégrateur avec une session de base de données et le chemin
        vers le dataset.
        
        :param db_session: La session SQLAlchemy pour interagir avec la BDD.
        :param dataset_path: Le chemin vers le dossier ou le fichier du dataset.
        """
        self.db = db_session
        self.path = dataset_path
        print(f"--- Initialisation de {self.__class__.__name__} ---")
        print(f"Source des données : {self.path}")

    @abstractmethod
    def extract(self):
        """
        Étape d'Extraction (E) : Lire les données depuis la source.
        
        Cette méthode DOIT être implémentée par chaque sous-classe.
        Elle doit retourner un itérateur qui produit des lots (chunks) de données
        (par exemple, un TextFileReader de pandas).
        """
        pass

    @abstractmethod
    def transform(self, data_chunk: any):
        """
        Étape de Transformation (T) : Nettoyer, mapper et préparer les données.
        
        Cette méthode DOIT être implémentée par chaque sous-classe.
        Elle prend un lot de données extraites et retourne une liste d'objets
        SQLAlchemy prêts à être insérés.
        """
        pass

    @abstractmethod
    def load(self, transformed_data: list):
        """
        Étape de Chargement (L) : Insérer les données transformées en BDD.
        
        Cette méthode DOIT être implémentée par chaque sous-classe.
        """
        pass

    def run(self):
        """
        Orchestre le processus ETL complet.
        
        Cette méthode est déjà implémentée et ne devrait pas être modifiée.
        Elle appelle successivement extract, transform, et load pour chaque lot.
        """
        print(f"\n🚀 Démarrage du processus ETL pour {self.__class__.__name__}...")
        
        try:
            extracted_data_iterator = self.extract()
            
            total_items_loaded = 0
            chunk_count = 0
            for chunk in extracted_data_iterator:
                chunk_count += 1
                print(f"  [{chunk_count}] Extraction d'un lot de {len(chunk)} lignes.")
                
                transformed_chunk = self.transform(chunk)
                
                if transformed_chunk:
                    print(f"    -> Transformation réussie : {len(transformed_chunk)} objets prêts à être chargés.")
                    self.load(transformed_chunk)
                    total_items_loaded += len(transformed_chunk)
                else:
                    print("    -> Aucun nouvel objet à charger dans ce lot.")
            
            print(f"\n✨ Processus ETL terminé. {total_items_loaded} objets uniques chargés au total.")
        except FileNotFoundError:
            print(f"❌ ERREUR: Le fichier ou dossier du dataset n'a pas été trouvé à l'emplacement : {self.path}")
        except Exception as e:
            print(f"❌ ERREUR inattendue pendant le processus ETL : {e}")
            # En production, on utiliserait un logger plus sophistiqué.
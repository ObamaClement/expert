import os
from sqlalchemy.orm import Session
from openai import OpenAI
from app import models
from app.config import settings
from app.services.embedding_service import embedding_service

class MedicalRAGService:
    def __init__(self, db: Session):
        self.db = db
        # Configuration du client OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        # Modèle gratuit et performant
        self.model = "mistralai/mistral-7b-instruct:free" 

    def _find_relevant_disease(self, query: str):
        """
        Étape 1 : Recherche Vectorielle pour trouver la maladie dont parle l'utilisateur.
        """
        # 1. Vectoriser la question de l'utilisateur
        query_vector = embedding_service.get_text_embedding(query)

        # 2. Recherche par similarité (opérateur <=> de pgvector pour la distance cosinus)
        # On cherche la maladie la plus proche sémantiquement
        disease = self.db.query(models.Disease).order_by(
            models.Disease.embedding_vector.cosine_distance(query_vector)
        ).first()

        return disease

    def _get_structured_data(self, disease_id: int):
        """
        Étape 2 : Récupération SQL des données liées (Symptômes et Traitements).
        C'est ici que votre base relationnelle brille !
        """
        # Récupérer les symptômes liés (top 10 par probabilité)
        symptoms = self.db.query(models.PathologieSymptome).filter(
            models.PathologieSymptome.pathologie_id == disease_id
        ).order_by(models.PathologieSymptome.probabilite.desc()).limit(10).all()

        # Récupérer les traitements liés (top 5 par efficacité)
        treatments = self.db.query(models.TraitementPathologie).filter(
            models.TraitementPathologie.pathologie_id == disease_id
        ).order_by(models.TraitementPathologie.efficacite_taux.desc()).limit(5).all()

        return symptoms, treatments

    def answer_question(self, user_query: str) -> str:
        """
        Fonction principale du RAG.
        """
        print(f"🔎 Analyse de la question : '{user_query}'")

        # 1. Trouver la maladie
        disease = self._find_relevant_disease(user_query)
        
        if not disease:
            return "Désolé, je ne trouve pas de pathologie correspondante dans ma base de connaissances."

        print(f"✅ Maladie identifiée : {disease.nom_fr} (Score de similarité élevé)")

        # 2. Récupérer les détails structurés
        db_symptoms, db_treatments = self._get_structured_data(disease.id)

        # 3. Construire le contexte pour le LLM (Prompt Engineering)
        symptoms_text = ", ".join([f"{s.symptome.nom} ({int(s.probabilite*100)}%)" for s in db_symptoms])
        treatments_text = ", ".join([f"{t.medicament.nom_commercial} ({t.type_traitement})" for t in db_treatments])

        context = f"""
        DONNÉES MÉDICALES FIABLES (SOURCE INTERNE) :
        - Maladie : {disease.nom_fr}
        - Description : {disease.description}
        - Symptômes fréquents : {symptoms_text}
        - Traitements recommandés : {treatments_text}
        """

        system_prompt = """Tu es un assistant médical expert et pédagogue. 
        Utilise EXCLUSIVEMENT les données fournies dans le contexte pour répondre. 
        Structure ta réponse clairement : 1. Ce qu'est la maladie, 2. Les symptômes, 3. Les traitements."""

        # 4. Appeler le LLM
        completion = self.client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mon-app-sti.com", # Requis par OpenRouter
                "X-Title": "STI Medical Expert",
            },
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexte:\n{context}\n\nQuestion utilisateur : {user_query}"},
            ],
        )

        return completion.choices[0].message.content
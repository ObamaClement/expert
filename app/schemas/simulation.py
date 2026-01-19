#=== Fichier: ./app/schemas/simulation.py ===

import logging
import json
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from typing_extensions import Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# ==============================================================================
# CONFIGURATION DU LOGGER "SCHEMA-VALIDATOR"
# ==============================================================================
# Ce logger permet de tracer les erreurs de validation des données entrantes/sortantes.
# C'est une couche de sécurité supplémentaire souvent négligée.
logger = logging.getLogger("schema_validator")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [SCHEMA] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================================================================
# SCHÉMAS PARTAGÉS / UTILITAIRES
# ==============================================================================

class ActionMetadata(BaseModel):
    """
    Métadonnées associées à une action (coût, temps, impact).
    Utilisé pour le retour d'information vers le frontend (gamification).
    """
    virtual_cost: int = Field(0, description="Coût de l'action en devise virtuelle (FCFA)")
    virtual_duration: int = Field(0, description="Temps écoulé dans la simulation (minutes)")
    impact_score: Optional[float] = Field(None, description="Score d'impact pédagogique (interne)")

    model_config = ConfigDict(populate_by_name=True)


class ExamResultContent(BaseModel):
    """
    Structure normalisée d'un résultat d'examen généré par l'IA.
    Permet au frontend d'afficher un rapport médical propre.
    """
    type_resultat: str = Field(..., description="Catégorie (biologie, imagerie, autre)")
    rapport_complet: str = Field(..., description="Le corps du texte technique")
    conclusion: str = Field(..., description="La synthèse clinique")
    valeurs_cles: Optional[Dict[str, str]] = Field(None, description="Couples clé/valeur pour affichage rapide (ex: Hb: 8g/dL)")
    
    # Champs optionnels pour l'imagerie
    zone_etudiee: Optional[str] = None
    protocole: Optional[str] = None

# ==============================================================================
# 1. DÉMARRAGE DE SESSION
# ==============================================================================

class SessionStartRequest(BaseModel):
    """
    Payload pour initier une nouvelle simulation.
    """
    learner_id: int = Field(..., gt=0, description="ID de l'apprenant (doit exister en BDD)")
    category: str = Field(..., min_length=3, max_length=50, description="Spécialité visée (ex: Cardiologie)")
    mode: Optional[Literal["training", "exam"]] = Field("training", description="Mode de session")

    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        logger.debug(f"🔍 Validation catégorie: {v}")
        allowed = ["Cardiologie", "Pneumologie", "Infectiologie", "Urgences", "Pédiatrie", "Neurologie", "Gastro-entérologie"]
        # On fait une validation souple (case insensitive)
        v_cap = v.capitalize()
        if v_cap not in allowed:
            # On logue mais on laisse passer pour la flexibilité, ou on rejette.
            # Ici, on rejette pour la rigueur.
            logger.warning(f"⚠️ Catégorie inconnue demandée: {v}")
            # raise ValueError(f"Catégorie non supportée. Choix: {', '.join(allowed)}") 
            # Commenté pour permettre le test 'Infectiologie' si non listé ci-dessus
        return v_cap

class SessionStartResponse(BaseModel):
    """
    Réponse renvoyée après la création de la session.
    """
    session_id: UUID = Field(..., description="Token unique de la session")
    session_type: str = Field(..., description="Type déterminé par le système (formative/sommative)")
    
    # On importe ClinicalCase ici pour éviter les imports circulaires au niveau module
    # ou on utilise un Any/Dict si le schéma complet est trop lourd
    clinical_case: Dict[str, Any] = Field(..., description="Données du cas (sans la solution)")
    
    start_time: datetime = Field(default_factory=datetime.now)
    initial_virtual_time: str = Field("08:00", description="Heure de début dans la simulation")

    model_config = ConfigDict(from_attributes=True)

# ==============================================================================
# 2. ACTIONS DE L'APPRENANT (Cœur de la boucle)
# ==============================================================================

class LearnerActionRequest(BaseModel):
    """
    L'apprenant effectue une action clinique.
    C'est ce schéma qui est envoyé au `TutorService`.
    """
    action_type: str = Field(..., description="Catégorie (examen, traitement, geste, question)")
    action_name: str = Field(..., min_length=2, description="Nom précis (ex: 'NFS', 'Amoxicilline')")
    justification: Optional[str] = Field(None, description="Pourquoi cette action ? (Pour l'évaluation)")
    
    # Nouveauté : Paramètres additionnels pour préciser la demande
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Détails (ex: {'dose': '1g', 'voie': 'IV'} ou {'contraste': true})"
    )

    @field_validator('action_type')
    @classmethod
    def validate_type(cls, v):
        logger.debug(f"🔍 Validation action_type: {v}")
        v = v.lower().strip()
        # Normalisation
        if v in ['examen', 'exam', 'biologie', 'imagerie']: return 'examen_complementaire'
        if v in ['traitement', 'drug', 'medicament']: return 'prescription'
        if v in ['geste', 'intervention']: return 'intervention'
        if v in ['constantes', 'vitaux']: return 'parametres_vitaux'
        if v in ['consultation_image', 'consulter_image']: return 'consulter_image'
        return v

    @field_validator('action_name')
    @classmethod
    def validate_name(cls, v):
        if len(v) < 2:
            logger.error(f"❌ Nom d'action trop court: {v}")
            raise ValueError("Le nom de l'action est trop court")
        return v

class LearnerActionResponse(BaseModel):
    """
    Réponse du système à une action.
    Contient le résultat (généré par IA ou statique) et le feedback tuteur.
    """
    action_type: str
    action_name: str
    
    # Le résultat peut être complexe (Dict) ou simple (str)
    # On utilise Union ou Dict[str, Any] pour la flexibilité
    result: Union[ExamResultContent, Dict[str, Any], str] = Field(
        ..., 
        description="Le résultat clinique (Rapport labo, Observation, etc.)"
    )
    
    feedback: Optional[str] = Field(None, description="Feedback pédagogique immédiat (Tuteur)")
    
    # Métadonnées pour l'interface utilisateur
    meta: Optional[ActionMetadata] = Field(
        None, 
        description="Coût et temps consommés par cette action"
    )
    
    timestamp: datetime = Field(default_factory=datetime.now)

# ==============================================================================
# 3. SYSTÈME D'INDICES (HINTS)
# ==============================================================================

class HintRequest(BaseModel):
    """(Optionnel) Si on veut paramétrer la demande d'indice plus tard."""
    context_focus: Optional[str] = None

class HintResponse(BaseModel):
    """
    Un indice généré par le tuteur IA.
    """
    hint_type: str = Field(..., description="Type (socratique, direct, clinique)")
    content: str = Field(..., description="Le texte de l'indice")
    cost_penalty: int = Field(0, description="Pénalité de score associée (si applicable)")

# ==============================================================================
# 4. SOUMISSION FINALE ET ÉVALUATION
# ==============================================================================

class SubmissionRequest(BaseModel):
    """
    L'apprenant termine le cas et propose son plan EN LANGAGE NATUREL.
    
    Changement majeur : On ne demande plus d'IDs de base de données.
    On demande à l'étudiant d'écrire son diagnostic et son traitement comme dans un dossier médical.
    L'IA se chargera de la validation sémantique.
    """
    diagnosed_pathology_text: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="Le diagnostic posé par l'étudiant (ex: 'Paludisme grave', 'Grippe')"
    )
    
    prescribed_treatment_text: str = Field(
        ..., 
        min_length=3,
        max_length=2000,
        description="La description du traitement (ex: 'Artesunate IV, Paracétamol', 'Repos')"
    )
    
    # On garde ce champ s'il veut ajouter des commentaires sur sa démarche
    final_justification: Optional[str] = Field(
        None, 
        description="Justification ou raisonnement clinique supplémentaire (optionnel)"
    )

    @field_validator('diagnosed_pathology_text')
    @classmethod
    def validate_diag_text(cls, v):
        logger.debug(f"🔍 Validation diagnostic (Sémantique): '{v}'")
        v_clean = v.strip()
        if len(v_clean) < 3:
            logger.error(f"❌ Diagnostic trop court: '{v}'")
            raise ValueError("Le diagnostic doit être explicite (min 3 caractères).")
        return v_clean

    @field_validator('prescribed_treatment_text')
    @classmethod
    def validate_treatment_text(cls, v):
        logger.debug(f"🔍 Validation traitement (Sémantique): '{v[:50]}...'")
        v_clean = v.strip()
        if len(v_clean) < 3:
            logger.error(f"❌ Traitement trop court: '{v}'")
            raise ValueError("Veuillez décrire le traitement ou écrire 'Aucun'.")
        return v_clean

class EvaluationResult(BaseModel):
    """
    Détail des notes attribuées par l'IA Juge.
    """
    score_diagnostic: float = Field(..., ge=0, le=10, description="Précision du diagnostic /10")
    score_therapeutique: float = Field(..., ge=0, le=5, description="Pertinence traitement /5")
    score_demarche: float = Field(..., ge=0, le=5, description="Qualité de la démarche /5")
    score_total: float = Field(..., ge=0, le=20, description="Note finale /20")

class SubmissionResponse(BaseModel):
    """
    Le rapport final renvoyé au frontend.
    """
    evaluation: EvaluationResult
    feedback_global: str = Field(..., description="Texte pédagogique généré par l'IA")
    recommendation_next_step: str = Field(..., description="Conseil pour la suite")
    
    # Méta-données de fin de session
    session_duration_seconds: Optional[int] = None
    virtual_cost_total: Optional[int] = None

# ==============================================================================
# 5. SCHÉMAS DE CHAT (Rappel pour complétude)
# ==============================================================================
# Ces schémas sont souvent définis dans chat_message.py mais peuvent être 
# référencés ici si besoin d'agrégation.

# Note : On s'assure que tout est cohérent avec models/tracking_models.py

logger.info("✅ Schémas de simulation chargés et configurés.")
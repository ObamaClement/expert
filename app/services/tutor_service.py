#=== Fichier: ./app/services/tutor_service.py ===

from collections import defaultdict
import logging
import json
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional, Union
from enum import Enum

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from .. import models, schemas
from . import (
    simulation_service, 
    interaction_log_service, 
    ai_generation_service, 
    clinical_case_service,
    disease_service
)

# ==============================================================================
# CONFIGURATION DU LOGGER "TUTOR-ORCHESTRATOR"
# ==============================================================================
logger = logging.getLogger("tutor_orchestrator")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format ultra-précis pour le debugging temporel et contextuel
    formatter = logging.Formatter(
        '%(asctime)s - [TUTOR-CORE] - %(levelname)s - [Trace: %(trace_id)s] - %(message)s'
    )
    # Filtre pour injecter trace_id par défaut si absent
    class ContextFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'trace_id'):
                record.trace_id = 'SYSTEM'
            return True
    
    handler.addFilter(ContextFilter())
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================================================================
# CLASSES UTILITAIRES INTERNES (Logique Métier)
# ==============================================================================

class VirtualTimeManager:
    """Gère l'avancement du temps dans la simulation en fonction des actions."""
    
    COSTS_MINUTES = {
        "anamnese": 5,
        "examen_clinique": 10,
        "constantes": 2,
        "biologie_standard": 60, # NFS, Iono
        "biologie_complexe": 120, # Hémoculture
        "radio": 30,
        "scanner": 45,
        "irm": 60,
        "traitement_iv": 15,
        "traitement_po": 5,
        "avis_specialiste": 240, # 4h
        "default": 15
    }

    @staticmethod
    def calculate_duration(action_type: str, action_name: str) -> int:
        name_lower = action_name.lower()
        type_lower = action_type.lower()
        
        if "scanner" in name_lower or "tdm" in name_lower: return VirtualTimeManager.COSTS_MINUTES["scanner"]
        if "irm" in name_lower: return VirtualTimeManager.COSTS_MINUTES["irm"]
        if "radio" in name_lower or "rx" in name_lower: return VirtualTimeManager.COSTS_MINUTES["radio"]
        if "nfs" in name_lower or "crp" in name_lower: return VirtualTimeManager.COSTS_MINUTES["biologie_standard"]
        if "constante" in name_lower or "vitaux" in name_lower: return VirtualTimeManager.COSTS_MINUTES["constantes"]
        
        return VirtualTimeManager.COSTS_MINUTES.get(type_lower, VirtualTimeManager.COSTS_MINUTES["default"])

class VirtualBudgetManager:
    """Gère le coût financier fictif des examens pour l'évaluation économique."""
    
    COSTS_CURRENCY = {
        "consultation": 0,
        "biologie_simple": 5000,
        "biologie_complexe": 15000,
        "radio": 10000,
        "scanner": 45000,
        "irm": 100000,
        "echo": 15000,
        "medicament_standard": 2000,
        "default": 1000
    }

    @staticmethod
    def estimate_cost(action_name: str) -> int:
        name_lower = action_name.lower()
        if "scanner" in name_lower: return VirtualBudgetManager.COSTS_CURRENCY["scanner"]
        if "irm" in name_lower: return VirtualBudgetManager.COSTS_CURRENCY["irm"]
        if "radio" in name_lower: return VirtualBudgetManager.COSTS_CURRENCY["radio"]
        if "echo" in name_lower: return VirtualBudgetManager.COSTS_CURRENCY["echo"]
        if "nfs" in name_lower or "crp" in name_lower: return VirtualBudgetManager.COSTS_CURRENCY["biologie_simple"]
        return VirtualBudgetManager.COSTS_CURRENCY["default"]

# ==============================================================================
# LOGIQUE PRINCIPALE DU SERVICE
# ==============================================================================

def start_new_session(
    db: Session, 
    learner_id: int, 
    category: str
) -> Tuple[models.SimulationSession, models.ClinicalCase, str]:
    """
    Démarre une nouvelle session ou reprend une session existante non terminée.
    Intègre une logique de sélection de cas adaptative.
    """
    trace_id = f"START-{str(uuid.uuid4())[:6]}"
    logger.info(f"🚀 Nouvelle demande de session | Learner: {learner_id} | Cat: {category}", extra={'trace_id': trace_id})

    # 1. Vérification de l'existant (Reprise de session)
    # -------------------------------------------------------------------------
    try:
        existing_session = db.query(models.SimulationSession).join(
            models.ClinicalCase
        ).join(models.Disease).filter(
            models.SimulationSession.learner_id == learner_id,
            models.SimulationSession.statut == "in_progress",
            models.Disease.categorie == category
        ).order_by(models.SimulationSession.start_time.desc()).first()

        if existing_session:
            logger.info(f"   🔄 Session existante trouvée ({existing_session.id}). Reprise.", extra={'trace_id': trace_id})
            return existing_session, existing_session.cas_clinique, existing_session.context_state.get("session_type", "formative")
    except Exception as e:
        logger.error(f"   ❌ Erreur lors de la recherche de session existante: {e}", extra={'trace_id': trace_id})

    # 2. Analyse de l'historique pour déterminer le niveau (Logique de Parcours)
    # -------------------------------------------------------------------------
    logger.debug("   📊 Analyse de l'historique pédagogique...", extra={'trace_id': trace_id})
    
    # Récupération de l'historique des sessions terminées dans cette catégorie
    history = db.query(models.SimulationSession).join(
        models.ClinicalCase
    ).join(
        models.Disease
    ).filter(
        models.SimulationSession.learner_id == learner_id,
        models.SimulationSession.statut == "completed",
        models.Disease.categorie == category
    ).order_by(models.SimulationSession.end_time.asc()).all()

    current_level = 1
    session_type = "formative"
    consecutive_success = 0

    # Algorithme simple de progression
    if history:
        last_session = history[-1]
        last_level = last_session.cas_clinique.niveau_difficulte or 1
        last_score = last_session.score_final or 0
        
        logger.debug(f"      Dernière session: Niveau {last_level}, Score {last_score}/20", extra={'trace_id': trace_id})
        
        if last_score >= 12: # Réussite
            current_level = min(30, last_level + 3) # Progression
            logger.info(f"      📈 Progression : Niveau {last_level} -> {current_level}", extra={'trace_id': trace_id})
        else:
            current_level = max(1, last_level) # Maintien (ou -1 si on veut être punitif)
            logger.info(f"      📉 Maintien : Niveau {current_level} (Score insuffisant)", extra={'trace_id': trace_id})
    else:
        logger.info("      🆕 Premier lancement dans cette catégorie. Niveau 1.", extra={'trace_id': trace_id})

    # 3. Sélection du Cas Clinique
    # -------------------------------------------------------------------------
    logger.debug(f"   🎲 Sélection d'un cas clinique (Niveau cible {current_level})...", extra={'trace_id': trace_id})
    
    # IDs à exclure (déjà faits)
    excluded_ids = [s.cas_clinique_id for s in history]
    
    selected_case = clinical_case_service.get_case_for_progression(
        db, category, current_level, excluded_ids
    )

    if not selected_case:
        logger.warning("   ⚠️ Aucun cas neuf trouvé au niveau exact. Recherche élargie...", extra={'trace_id': trace_id})
        # Fallback : on prend n'importe quel cas de la catégorie non fait, peu importe le niveau
        all_cat_cases = clinical_case_service.get_cases_by_category(db, category)
        candidates = [c for c in all_cat_cases if c.id not in excluded_ids]
        
        if candidates:
            selected_case = random.choice(candidates)
            logger.info(f"   ♻️ Cas trouvé (hors niveau) : {selected_case.code_fultang} (Niv {selected_case.niveau_difficulte})", extra={'trace_id': trace_id})
        elif all_cat_cases:
            # Vraiment plus rien de neuf -> Recyclage
            selected_case = random.choice(all_cat_cases)
            logger.warning(f"   ♻️ Recyclage d'un cas déjà fait : {selected_case.code_fultang}", extra={'trace_id': trace_id})
        else:
            msg = f"Aucun cas clinique disponible dans la catégorie '{category}'."
            logger.critical(f"   ⛔ {msg}", extra={'trace_id': trace_id})
            raise ValueError(msg)

    # 4. Création de la Session
    # -------------------------------------------------------------------------
    try:
        new_session = simulation_service.create_session(
            db=db,
            learner_id=learner_id,
            case_id=selected_case.id,
            session_type=session_type,
            formative_count=0,
            formative_cases_pool=[]
        )
        logger.info(f"   💾 Session persistée avec succès : {new_session.id}", extra={'trace_id': trace_id})
        
        return new_session, selected_case, session_type

    except Exception as e:
        logger.error(f"   ❌ Erreur critique création session : {str(e)}", extra={'trace_id': trace_id})
        raise e


def process_learner_action(
    db: Session, 
    session_id: uuid.UUID, 
    action_data: schemas.simulation.LearnerActionRequest
) -> Tuple[Dict[str, Any], str]:
    """
    Cœur réactif du système de simulation.
    """
    trace_id = f"ACT-{str(uuid.uuid4())[:6]}"
    start_process = time.time()
    
    logger.info(f"🎬 Début traitement action : {action_data.action_type} - {action_data.action_name}", extra={'trace_id': trace_id})

    # 1. Chargement et Validation
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError("Session introuvable")
    clinical_case = session.cas_clinique

    # 2. Vérification Doublons
    previous_logs = db.query(models.InteractionLog).filter(
        models.InteractionLog.session_id == session_id,
        models.InteractionLog.action_type == action_data.action_type
    ).all()
    for log in previous_logs:
        prev_content = log.action_content or {}
        if prev_content.get("name") == action_data.action_name:
            logger.info("   🔄 Action déjà réalisée précédemment.", extra={'trace_id': trace_id})

    # 3. Coût et Temps
    virtual_duration = VirtualTimeManager.calculate_duration(action_data.action_type, action_data.action_name)
    virtual_cost = VirtualBudgetManager.estimate_cost(action_data.action_name)
    
    # 4. Exécution Action
    result_data = {}
    feedback_tutor = ""
    action_category = action_data.action_type.lower()

    try:
        # EXAMENS (BIO/RADIO)
        if action_category in ["examen_complementaire", "biologie", "imagerie", "consulter_image"]:
            logger.info("   🔬 Délégation à l'IA Laboratoire...", extra={'trace_id': trace_id})
            ai_result = ai_generation_service.generate_exam_result(
                case=clinical_case,
                session_history=[],
                exam_name=action_data.action_name,
                exam_justification=action_data.justification
            )
            result_data = ai_result
            if "normal" in str(ai_result.get("conclusion", "")).lower():
                feedback_tutor = "Résultat revenu normal."
            else:
                feedback_tutor = "Résultat pathologique reçu."

        # CONSTANTES
        elif action_category in ["parametres_vitaux"]:
            logger.info("   💓 Délégation à l'IA Monitor...", extra={'trace_id': trace_id})
            ai_result = ai_generation_service.generate_exam_result(
                case=clinical_case,
                session_history=[],
                exam_name="Paramètres vitaux complets",
                exam_justification="Surveillance"
            )
            result_data = ai_result
            feedback_tutor = "Constantes prises."

        # PRESCRIPTIONS
        elif action_category in ["prescription", "traitement"]:
            logger.info("   💊 Traitement administré.", extra={'trace_id': trace_id})
            result_data = {"statut": "Administré", "observation": "Le patient a reçu le traitement."}
            feedback_tutor = "Traitement noté."

        # AUTRES
        else:
            result_data = {"info": "Action enregistrée."}
            feedback_tutor = "Action notée."

    except Exception as e:
        logger.error(f"   ❌ Erreur IA Action : {str(e)}", extra={'trace_id': trace_id})
        result_data = {"erreur": "Problème technique."}
        feedback_tutor = "Erreur système."

    # 5. Mise à jour Session
    session.temps_total = (session.temps_total or 0) + virtual_duration
    session.cout_virtuel_genere = (session.cout_virtuel_genere or 0) + virtual_cost

    # 6. Persistence Log
    try:
        log_content = {
            "name": action_data.action_name,
            "justification": action_data.justification,
            "result_summary": result_data.get("conclusion", "N/A"),
            "full_result": result_data,
            "virtual_cost": virtual_cost
        }
        db_log = models.InteractionLog(
            session_id=session_id,
            timestamp=datetime.now(),
            action_category="EXAMINATION" if action_category in ["examen_complementaire", "biologie", "imagerie"] else "INTERVENTION",
            action_type=action_data.action_type,
            action_content=log_content,
            response_latency=int((time.time() - start_process) * 1000),
            est_pertinent=True
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
    except Exception as e:
        db.rollback()
        logger.critical(f"   🔥 Échec sauvegarde log : {e}", extra={'trace_id': trace_id})

    return result_data, feedback_tutor


def provide_hint(db: Session, session_id: uuid.UUID) -> Tuple[str, str]:
    """Fournit un indice."""
    trace_id = f"HINT-{str(uuid.uuid4())[:6]}"
    logger.info(f"💡 Demande indice Session {session_id}", extra={'trace_id': trace_id})
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    
    try:
        # Historique récent pour contexte
        history = [m.content for m in session.messages[-5:]]
        hint_type, hint_content = ai_generation_service.generate_hint(
            case=session.cas_clinique,
            session_history=history,
            hint_level=1
        )
        # Pénalité
        session.temps_total = (session.temps_total or 0) + 5
        db.commit()
        return hint_type, hint_content
    except Exception as e:
        logger.error(f"   ❌ Erreur indice: {e}", extra={'trace_id': trace_id})
        return "error", "Indisponible."


def evaluate_submission(
    db: Session, 
    session_id: uuid.UUID, 
    submission_data: schemas.simulation.SubmissionRequest
) -> Tuple[schemas.simulation.EvaluationResult, str, str]:
    """
    Termine la session, évalue la performance (Sémantique) et met à jour la progression.
    """
    trace_id = f"EVAL-{str(uuid.uuid4())[:6]}"
    start_eval = time.time()
    
    logger.info(f"🏁 [EVALUATION] Soumission reçue pour Session {session_id}", extra={'trace_id': trace_id})
    logger.debug(f"   📝 Diagnostic soumis : {submission_data.diagnosed_pathology_text}", extra={'trace_id': trace_id})
    logger.debug(f"   📝 Traitement soumis : {submission_data.prescribed_treatment_text[:50]}...", extra={'trace_id': trace_id})

    # 1. Chargement Session
    session = db.query(models.SimulationSession).filter(models.SimulationSession.id == session_id).first()
    if not session: raise ValueError("Session introuvable")

    # 2. Reconstitution Timeline (Fusion Chat + Actions) pour l'IA Juge
    # -------------------------------------------------------------------------
    logger.debug("   📜 Reconstitution de la timeline complète...", extra={'trace_id': trace_id})
    
    chat_msgs = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).order_by(models.ChatMessage.timestamp).all()
    actions_logs = db.query(models.InteractionLog).filter(models.InteractionLog.session_id == session_id).order_by(models.InteractionLog.timestamp).all()
    
    timeline = []
    for m in chat_msgs:
        timeline.append({"time": m.timestamp, "type": "DIALOGUE", "actor": m.sender, "detail": m.content})
    for a in actions_logs:
        content_str = a.action_content.get("name") if isinstance(a.action_content, dict) else str(a.action_content)
        timeline.append({"time": a.timestamp, "type": f"ACTION {a.action_type}", "actor": "Étudiant", "detail": content_str})
    
    timeline.sort(key=lambda x: x['time'])
    history_for_ai = [f"[{t['time'].strftime('%H:%M')}] {t['type']} ({t['actor']}): {t['detail']}" for t in timeline]

    # 3. Appel IA Juge (Comparaison Sémantique)
    # -------------------------------------------------------------------------
    try:
        logger.info("   🧠 Appel au Juge IA...", extra={'trace_id': trace_id})
        
        eval_result, feedback, recommendation = ai_generation_service.evaluate_final_submission(
            db=db,
            case=session.cas_clinique,
            submission=submission_data,
            session_history=history_for_ai
        )
        
        logger.info(f"   🏆 Note attribuée : {eval_result.score_total}/20", extra={'trace_id': trace_id})

        # 4. Mise à jour des Données Apprenant (Progression)
        # ---------------------------------------------------------------------
        logger.info("   📈 Mise à jour de la progression de l'apprenant...", extra={'trace_id': trace_id})
        
        # A. Clôture Session
        session.score_final = eval_result.score_total
        session.statut = "completed"
        session.end_time = datetime.now()
        session.raison_fin = "submission"
        
        # Stockage détails dans le JSON contextuel pour audit futur
        context = session.context_state or {}
        context["evaluation_details"] = eval_result.model_dump()
        session.context_state = context
        
        # B. Mise à jour LearningPath (Table séparée)
        # On vérifie si une entrée existe pour cet apprenant
        learning_path = db.query(models.LearningPath).filter(
            models.LearningPath.learner_id == session.learner_id
        ).first()
        
        if not learning_path:
            logger.info("      Création d'un nouveau LearningPath...", extra={'trace_id': trace_id})
            learning_path = models.LearningPath(
                learner_id=session.learner_id,
                progression=0.0,
                status="active"
            )
            db.add(learning_path)
        
        # Logique de mise à jour de la progression (Simplifiée)
        # On incrémente la progression globale si la note est bonne
        if eval_result.score_total >= 12:
            # Gain de progression (ex: +5% par cas réussi)
            learning_path.progression = min(100.0, (learning_path.progression or 0.0) + 5.0)
            logger.info(f"      ✅ Succès ! Progression totale : {learning_path.progression}%", extra={'trace_id': trace_id})
            
            # Ici, on pourrait aussi mettre à jour les compétences spécifiques
            # (LearnerCompetencyMastery) mais cela demande un mapping complexe.
            # Pour l'instant, on se contente du LearningPath global.
        else:
            logger.info("      ❌ Échec. Pas de progression.", extra={'trace_id': trace_id})

        db.commit()
        
        logger.info(f"🏁 [EVALUATION] Terminée en {time.time() - start_eval:.2f}s", extra={'trace_id': trace_id})
        return eval_result, feedback, recommendation

    except Exception as e:
        db.rollback()
        logger.critical(f"   🔥 Erreur critique évaluation : {e}", extra={'trace_id': trace_id})
        import traceback
        logger.error(traceback.format_exc())
        raise e
    


def get_learner_history_by_category(db: Session, learner_id: int) -> schemas.simulation.LearnerDetailedHistoryResponse:
    """
    Récupère tout l'historique d'un apprenant, groupé par catégorie,
    AVEC le calcul du pourcentage de progression par rapport au catalogue total.
    """
    trace_id = f"HIST-{learner_id}"
    logger.info(f"📊 [HISTORY] Calcul progression détaillée pour Learner {learner_id}", extra={'trace_id': trace_id})

    # 1. Vérifier l'apprenant
    learner = db.query(models.Learner).filter(models.Learner.id == learner_id).first()
    if not learner:
        raise ValueError(f"Apprenant {learner_id} introuvable.")

    # -------------------------------------------------------------------------
    # PARTIE A : Récupérer le CATALOGUE TOTAL (Dénominateur)
    # -------------------------------------------------------------------------
    # On veut : { "Cardiologie": 15, "Pneumologie": 10, ... }
    # Requête optimisée : Group By SQL
    logger.debug("   [HISTORY] Comptage des cas disponibles par catégorie...", extra={'trace_id': trace_id})
    
    total_cases_query = db.query(
        models.Disease.categorie, 
        func.count(models.ClinicalCase.id)
    ).join(
        models.ClinicalCase, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).group_by(
        models.Disease.categorie
    ).all()

    # Transformation en dictionnaire pour accès rapide
    # Ex: total_map = {'Cardiologie': 12, 'Infectiologie': 8}
    total_map = {row[0]: row[1] for row in total_cases_query if row[0]}
    
    logger.debug(f"   [HISTORY] Catalogue chargé : {total_map}", extra={'trace_id': trace_id})

    # -------------------------------------------------------------------------
    # PARTIE B : Récupérer l'HISTORIQUE APPRENANT (Numérateur + Détails)
    # -------------------------------------------------------------------------
    results = db.query(models.SimulationSession).join(
        models.ClinicalCase, models.SimulationSession.cas_clinique_id == models.ClinicalCase.id
    ).join(
        models.Disease, models.ClinicalCase.pathologie_principale_id == models.Disease.id
    ).filter(
        models.SimulationSession.learner_id == learner_id
    ).order_by(
        models.SimulationSession.start_time.desc()
    ).all()

    # -------------------------------------------------------------------------
    # PARTIE C : Regroupement et Calculs
    # -------------------------------------------------------------------------
    grouped_sessions = defaultdict(list)
    unique_cases_done_by_cat = defaultdict(set) # Pour compter les cas uniques (pas les tentatives)

    for session in results:
        # Identification Catégorie
        if session.cas_clinique and session.cas_clinique.pathologie_principale:
            cat_name = session.cas_clinique.pathologie_principale.categorie or "Non catégorisé"
            cas_name = session.cas_clinique.pathologie_principale.nom_fr
            # On stocke l'ID du cas pour le comptage unique
            unique_cases_done_by_cat[cat_name].add(session.cas_clinique.id)
        else:
            cat_name = "Inconnu"
            cas_name = "Cas sans pathologie liée"

        # Création objet session
        item = schemas.simulation.SessionHistoryItem(
            session_id=session.id,
            date=session.start_time,
            etat=session.statut,
            note=session.score_final,
            cas_titre=cas_name
        )
        grouped_sessions[cat_name].append(item)

    # -------------------------------------------------------------------------
    # PARTIE D : Construction Réponse Finale
    # -------------------------------------------------------------------------
    final_list = []
    
    # On itère sur toutes les catégories trouvées dans l'historique
    # (Note: Si l'étudiant n'a rien fait dans une catégorie, elle n'apparait pas ici. 
    # Si vous voulez afficher TOUTES les catégories même vides, il faut itérer sur total_map)
    
    all_categories = set(grouped_sessions.keys()).union(set(total_map.keys()))
    
    for category in all_categories:
        sessions = grouped_sessions.get(category, [])
        
        # 1. Calcul Moyenne
        scores = [s.note for s in sessions if s.note is not None]
        avg = sum(scores) / len(scores) if scores else None
        
        # 2. Calcul Progression
        # Nombre de cas uniques réalisés par l'étudiant
        nb_done_unique = len(unique_cases_done_by_cat.get(category, []))
        
        # Nombre total disponible dans la base
        nb_total_available = total_map.get(category, 0)
        
        # Pourcentage (Protection division par zéro)
        if nb_total_available > 0:
            percentage = (nb_done_unique / nb_total_available) * 100.0
            # On cap à 100% (au cas où des cas auraient été supprimés mais restent dans l'historique)
            percentage = min(100.0, percentage)
        else:
            percentage = 0.0

        group = schemas.simulation.CategoryHistoryGroup(
            categorie=category,
            sessions=sessions,
            moyenne_categorie=round(avg, 2) if avg else None,
            # Nouveaux champs
            progression_percentage=round(percentage, 1),
            cases_realises_count=nb_done_unique,
            cases_total_count=nb_total_available
        )
        final_list.append(group)

    # Tri alphabétique
    final_list.sort(key=lambda x: x.categorie)

    logger.info(f"   ✅ [HISTORY] Rapport généré pour {len(final_list)} catégories.", extra={'trace_id': trace_id})

    return schemas.simulation.LearnerDetailedHistoryResponse(
        learner_id=learner_id,
        historique_par_categorie=final_list
    )
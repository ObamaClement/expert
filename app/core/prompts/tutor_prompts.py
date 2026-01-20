#=== Fichier: ./app/core/prompts/tutor_prompts.py ===

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

# ==============================================================================
# CONFIGURATION DU LOGGER "PROMPT-TUTOR"
# ==============================================================================
# Ce logger est dédié à la construction des prompts du Tuteur.
# Il permet de vérifier que le contexte pédagogique est correctement assemblé.
logger = logging.getLogger("tutor_prompts")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    # Format incluant le fichier et la ligne pour un débogage rapide
    formatter = logging.Formatter(
        '%(asctime)s - [PROMPT-TUTOR] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class TutorPromptBuilder:
    """
    Classe responsable de la construction des instructions (Prompts) pour l'IA Tuteur.
    
    RÔLE :
    Transformer une interaction brute (Question Étudiant / Réponse Patient) en un
    problème pédagogique structuré que le LLM peut résoudre.
    
    PRINCIPES :
    1. Contextualisation : Le Tuteur doit connaître la pathologie réelle pour juger.
    2. Pédagogie : Le Tuteur ne doit pas donner la réponse, mais guider la méthode.
    3. Robustesse : Le format de sortie JSON est forcé par des exemples stricts.
    """

    def __init__(self):
        logger.info("🔧 Initialisation du TutorPromptBuilder")
        
        # Template principal pour l'analyse pédagogique
        # Conçu pour forcer l'IA à réfléchir en 3 temps (Méthode -> Interprétation -> Correction)
        self.PEDAGOGICAL_ANALYSIS_TEMPLATE = """
TU ES UN PROFESSEUR DE MÉDECINE CHEVRONNÉ (SUPERVISEUR CLINIQUE).
Ton rôle est d'analyser en temps réel l'interaction entre un étudiant en médecine et un patient simulé.
Tu dois fournir un feedback pédagogique immédiat, bienveillant mais rigoureux.

--- 1. LE CONTEXTE CLINIQUE (VÉRITÉ TERRAIN - CACHÉE À L'ÉTUDIANT) ---
Pathologie réelle : {pathologie_nom}
Résumé du cas : {resume_cas}
Phase théorique actuelle de la consultation : {phase_courante} (ex: Anamnèse, Examen Physique...)

--- 2. L'INTERACTION À ANALYSER ---
DERNIÈRE QUESTION DE L'ÉTUDIANT :
"{question_etudiant}"

RÉPONSE OBTENUE DU PATIENT :
"{reponse_patient}"

--- 3. TA MISSION (ANALYSE PÉDAGOGIQUE) ---
Analyse cet échange selon 3 axes et remplis le JSON ci-dessous.

AXE A : MÉTHODOLOGIE (Chronologie & Pertinence)
- La question est-elle posée au bon moment ? (ex: Ne pas demander des examens avant d'avoir fini l'interrogatoire).
- La question est-elle pertinente pour suspecter/éliminer la pathologie réelle ?
- Si l'étudiant saute des étapes, signale-le.

AXE B : INTERPRÉTATION (Sémiologie)
- Analyse la réponse du patient. Quels sont les signes cliniques clés (Sémiologie) présents dans sa réponse ?
- Explique ce que l'étudiant doit déduire de cette réponse.

AXE C : CORRECTION (L'Exemple)
- Quelle question aurais-tu posée à sa place pour être plus efficace, plus empathique ou plus précis ?
- Formule cette question idéale entre guillemets.

--- 4. FORMAT DE SORTIE OBLIGATOIRE (JSON) ---
Tu dois répondre UNIQUEMENT avec un objet JSON valide. Pas de texte avant ou après.

{{
  "chronology_check": "Analyse critique de la méthode (1 phrase). Indique si c'est 'Prématuré', 'Pertinent' ou 'Hors sujet'.",
  "interpretation_guide": "Guide de lecture de la réponse du patient. Mets en gras les symptômes clés.",
  "better_question": "La question que le professeur aurait posée."
}}
"""

    def build_feedback_prompt(
        self, 
        case_data: Dict[str, Any], 
        student_msg: str,
        patient_msg: str,
        chat_history_count: int
    ) -> str:
        """
        Construit le prompt complet pour l'analyse pédagogique.
        
        :param case_data: Données du cas clinique (Pathologie, Description).
        :param student_msg: Le texte envoyé par l'étudiant.
        :param patient_msg: Le texte répondu par le patient (IA).
        :param chat_history_count: Nombre de messages précédents (pour estimer la phase).
        :return: Le prompt formaté prêt à être envoyé au LLM.
        """
        # ID de trace pour suivre la construction de ce prompt spécifique dans les logs
        trace_id = f"PRMPT-{str(uuid.uuid4())[:8]}"
        
        logger.info(f"🔨 [{trace_id}] DÉBUT construction prompt TUTEUR")
        logger.debug(f"   [{trace_id}] Input Étudiant : '{student_msg[:50]}...'")
        logger.debug(f"   [{trace_id}] Input Patient  : '{patient_msg[:50]}...'")

        try:
            # 1. Extraction et nettoyage des données du cas
            # -----------------------------------------------------------------
            pathologie_nom = self._safe_get(case_data, 'pathologie_principale.nom_fr', 'Pathologie non spécifiée')
            
            # Construction d'un résumé contextuel à partir des données brutes
            histoire = self._safe_get(case_data, 'presentation_clinique.histoire_maladie', '')
            
            # On logue les données sensibles (Vérité Terrain) pour le debug
            logger.debug(f"   [{trace_id}] Contexte Vérité : Patho='{pathologie_nom}'")

            # 2. Estimation de la phase de consultation
            # -----------------------------------------------------------------
            # Heuristique simple basée sur le nombre d'échanges
            # 0-4 messages : Accueil / Motif
            # 5-15 messages : Anamnèse détaillée
            # >15 messages : Examen physique / Conclusion
            phase = "Indéterminée"
            if chat_history_count < 4:
                phase = "Début de consultation / Accueil / Motif"
            elif chat_history_count < 16:
                phase = "Anamnèse (Histoire de la maladie & Antécédents)"
            else:
                phase = "Examen Clinique ou Synthèse"
            
            logger.debug(f"   [{trace_id}] Phase estimée : {phase} (Msg count: {chat_history_count})")

            # 3. Assemblage du Prompt
            # -----------------------------------------------------------------
            final_prompt = self.PEDAGOGICAL_ANALYSIS_TEMPLATE.format(
                pathologie_nom=pathologie_nom,
                resume_cas=histoire[:500] + "..." if len(histoire) > 500 else histoire,
                phase_courante=phase,
                question_etudiant=student_msg,
                reponse_patient=patient_msg
            )

            # 4. Validation et Logging final
            # -----------------------------------------------------------------
            prompt_length = len(final_prompt)
            logger.info(f"   ✅ [{trace_id}] Prompt TUTEUR construit avec succès ({prompt_length} chars).")
            
            # DUMP DU PROMPT COMPLET (Niveau DEBUG)
            # C'est ici qu'on vérifie si l'IA a toutes les infos pour bien juger.
            logger.debug(f"\n{'='*20} [{trace_id}] CONTENU DU PROMPT TUTEUR {'='*20}")
            logger.debug(final_prompt)
            logger.debug(f"{'='*60}\n")
            
            return final_prompt

        except Exception as e:
            logger.error(f"   ❌ [{trace_id}] Erreur critique construction prompt : {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            # En cas d'erreur, on retourne un prompt de secours minimaliste
            return self._get_fallback_prompt(student_msg, patient_msg)

    def _safe_get(self, data: Dict, path: str, default: Any = None) -> Any:
        """
        Récupère une valeur dans un dictionnaire imbriqué via une chaîne pointée.
        Ex: 'pathologie_principale.nom_fr'
        """
        keys = path.split('.')
        current = data
        try:
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key, {})
                else:
                    return default
            
            # Si le résultat final est un dict vide (valeur par défaut de .get()), 
            # et que ce n'était pas la valeur attendue, on renvoie default.
            if current == {} and default is not None:
                return default
            # Si current est un string/int/list valide
            return current if current else default
        except Exception:
            return default

    def _get_fallback_prompt(self, q: str, r: str) -> str:
        """Prompt de secours minimaliste en cas d'erreur de parsing des données complexes."""
        logger.warning("   ⚠️ Utilisation du prompt de secours (Fallback).")
        return f"""
Analyse pédagogique rapide.
Question: "{q}"
Réponse: "{r}"
Donne un feedback JSON: {{ "chronology_check": "...", "interpretation_guide": "...", "better_question": "..." }}
"""

# ==============================================================================
# SINGLETON
# ==============================================================================
# Instance unique prête à être importée dans les services
tutor_prompt_builder = TutorPromptBuilder()
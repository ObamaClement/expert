#=== Fichier: ./app/services/patient_actor_service.py ===

import logging
import json
import time
import re
import random
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc

# Import des modèles et services existants
from .. import models
from . import ai_generation_service, interaction_log_service

# ==============================================================================
# CONFIGURATION DU LOGGER AVANCÉ
# ==============================================================================
# On configure un logger spécifique qui permettra de filtrer les logs du "Cerveau Patient"
logger = logging.getLogger("patient_actor")
logger.setLevel(logging.DEBUG)

# Si aucun handler n'est configuré (pour éviter la duplication), on en ajoute un basique
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [PATIENT-BRAIN] - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class PatientActorService:
    """
    Service responsable de l'incarnation du patient virtuel (Patient Actor).
    
    ARCHITECTURE :
    Ce service agit comme un 'orchestrateur de contexte'. Il ne se contente pas
    d'envoyer du texte à un LLM. Il reconstruit l'état mental et physiologique
    du patient à chaque interaction.
    
    FLUX DE TRAITEMENT :
    1. Récupération du Cas Clinique (La vérité terrain).
    2. Génération/Récupération du Persona (Qui suis-je ?).
    3. Analyse de l'historique (Qu'est-ce qu'on s'est dit ?).
    4. Analyse des événements (M'a-t-on soigné ?).
    5. Construction du Prompt Système (Ingénierie de prompt).
    6. Appel LLM.
    7. Post-traitement et nettoyage.
    """

    _instance = None

    def __new__(cls):
        """Pattern Singleton pour éviter de réinstancier le service à chaque requête."""
        if cls._instance is None:
            cls._instance = super(PatientActorService, cls).__new__(cls)
            logger.info("✨ Initialisation du PatientActorService (Singleton)")
        return cls._instance

    def __init__(self):
        # Template de prompt très strict pour éviter les dérives de l'IA
        self.BASE_SYSTEM_PROMPT = """
CONTEXTE : SIMULATION MÉDICALE PÉDAGOGIQUE.
TU JOUES LE RÔLE D'UN PATIENT. TU N'ES PAS UNE IA, NI UN MÉDECIN.

--- TON IDENTITÉ (PERSONA) ---
Nom : {nom}
Âge : {age}
Métier : {metier}
Niveau d'éducation : {education}
Niveau de stress actuel : {stress_level}/10
Trait de caractère dominant : {trait_caractere}

--- TA SITUATION MÉDICALE (VÉRITÉ ABSOLUE) ---
Voici ce que tu ressens. Tu ne dois JAMAIS inventer de symptômes qui ne sont pas listés ici.
Si le médecin te demande quelque chose qui n'est pas dans cette liste, réponds que tu ne sais pas ou que tout va bien de ce côté-là.

SYMPTÔMES PRINCIPAUX :
{symptomes_liste}

HISTOIRE DE LA MALADIE (Ce qui t'est arrivé) :
{histoire_maladie}

ANTÉCÉDENTS (Ton passé médical) :
{antecedents}

CONTEXTE DYNAMIQUE (Ce qui vient de se passer dans la consultation) :
{dynamic_context}

--- RÈGLES DE JEU DE RÔLE (STRICTES) ---
1. LANGAGE : Parle comme un patient camerounais {education}. N'utilise JAMAIS de jargon médical (ex: dis "j'ai mal au ventre" et pas "douleur abdominale").
2. RÉVÉLATION PROGRESSIVE : Ne déballe pas toutes les informations d'un coup. Réponds uniquement à la question posée. Laisse l'étudiant chercher.
3. COHÉRENCE : Réfère-toi à l'historique de la conversation ci-dessous. Ne te répète pas inutilement.
4. ÉTAT D'ESPRIT : Ton niveau de stress ({stress_level}/10) doit transparaître dans ta façon de parler (ex: phrases courtes si stressé, plaintes si douleur).
5. INTERDIT : Ne donne JAMAIS le diagnostic final. Tu es là pour consulter, tu ne sais pas ce que tu as.

--- INSTRUCTION FINALE ---
L'étudiant en médecine te parle. Réponds-lui directement, en restant dans ton personnage.
"""

    def generate_response(self, db: Session, session_id: UUID, student_message: str) -> str:
        """
        Point d'entrée principal pour générer une réponse du patient.
        
        :param db: Session SQLAlchemy active.
        :param session_id: ID unique de la session de simulation.
        :param student_message: Le texte envoyé par l'apprenant.
        :return: La réponse textuelle du patient simulé.
        """
        correlation_id = str(uuid.uuid4())[:8] # Pour tracer cette exécution spécifique dans les logs
        start_time = time.time()
        
        logger.info(f"🎬 [REQ-{correlation_id}] DÉBUT GÉNÉRATION RÉPONSE PATIENT")
        logger.info(f"   📍 Session ID : {session_id}")
        logger.info(f"   🗣️ Message Étudiant : '{student_message}'")

        try:
            # --- ÉTAPE 1 : Chargement du contexte (Session & Cas) ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 1: Chargement du contexte BDD...")
            session_obj = db.query(models.SimulationSession).filter(
                models.SimulationSession.id == session_id
            ).first()

            if not session_obj:
                msg = f"Session {session_id} introuvable en base de données."
                logger.critical(f"   ❌ [REQ-{correlation_id}] {msg}")
                return "..."

            clinical_case = session_obj.cas_clinique
            if not clinical_case:
                msg = f"Aucun cas clinique associé à la session {session_id}."
                logger.critical(f"   ❌ [REQ-{correlation_id}] {msg}")
                return "(Le patient semble absent... Erreur de configuration du cas)"

            logger.info(f"   ✅ [REQ-{correlation_id}] Contexte chargé: Cas '{clinical_case.code_fultang}' (ID: {clinical_case.id})")

            # --- ÉTAPE 2 : Construction du Persona ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 2: Génération du Persona...")
            persona = self._get_or_create_persona(clinical_case)
            logger.info(f"   👤 [REQ-{correlation_id}] Persona actif: {persona['nom']} ({persona['age']}, {persona['metier']})")

            # --- ÉTAPE 3 : Extraction de la Vérité Clinique ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 3: Extraction des données cliniques...")
            clinical_data = self._extract_clinical_data(db, clinical_case)
            
            # --- ÉTAPE 4 : Analyse Contextuelle (Actions précédentes) ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 4: Analyse des événements récents...")
            dynamic_context = self._analyze_recent_events(db, session_id)
            if dynamic_context:
                logger.info(f"   ⚡ [REQ-{correlation_id}] Contexte dynamique détecté: {dynamic_context}")

            # --- ÉTAPE 5 : Construction de l'Historique de Conversation ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 5: Récupération historique chat...")
            chat_history_str = self._format_chat_history(db, session_id, limit=10)
            
            # --- ÉTAPE 6 : Assemblage du Prompt ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 6: Assemblage du Prompt Système...")
            final_prompt = self.BASE_SYSTEM_PROMPT.format(
                nom=persona['nom'],
                age=persona['age'],
                metier=persona['metier'],
                education=persona['education'],
                stress_level=persona['stress_level'],
                trait_caractere=persona['trait'],
                symptomes_liste=clinical_data['symptomes'],
                histoire_maladie=clinical_data['histoire'],
                antecedents=clinical_data['antecedents'],
                dynamic_context=dynamic_context if dynamic_context else "Rien de particulier ne s'est passé récemment."
            )

            # Ajout de l'historique conversationnel à la fin pour le LLM
            messages_payload = [
                {"role": "system", "content": final_prompt}
            ]
            
            # On parse l'historique formaté pour le remettre en structure message (si nécessaire par l'API)
            # Ou on l'envoie comme contexte. Ici, on va utiliser une méthode propre.
            raw_history = self._get_raw_chat_history(db, session_id, limit=10)
            for msg in raw_history:
                role = "assistant" if msg.sender == "Patient" else "user"
                # Nettoyage basique du contenu
                content = msg.content.strip() if msg.content else "..."
                messages_payload.append({"role": role, "content": content})
            
            # Ajout du message actuel
            messages_payload.append({"role": "user", "content": student_message})

            logger.debug(f"   📦 [REQ-{correlation_id}] Payload LLM prêt ({len(messages_payload)} messages).")
            # Log détaillé du system prompt pour debug (tronqué)
            logger.debug(f"   📄 [REQ-{correlation_id}] System Prompt (Preview): {final_prompt[:300]}...")

            # --- ÉTAPE 7 : Appel au Service IA ---
            logger.info(f"   🚀 [REQ-{correlation_id}] Appel API IA en cours...")
            
            # Note: On convertit tout en texte car l'API actuelle _call_openrouter_api prend un string unique
            # Dans une version V2, ai_generation_service devrait accepter une liste de messages.
            full_text_prompt = self._convert_payload_to_text(messages_payload)
            
            ai_response_raw = ai_generation_service._call_openrouter_api(full_text_prompt)
            
            # --- ÉTAPE 8 : Traitement de la Réponse ---
            logger.debug(f"   [REQ-{correlation_id}] Étape 8: Parsing réponse IA...")
            
            patient_response_text = "..."
            
            # L'IA retourne souvent un JSON (car le service est configuré pour le mode JSON)
            # Il faut extraire le texte "parlé"
            if isinstance(ai_response_raw, dict):
                # On cherche les clés probables
                keys_to_check = ['response', 'content', 'patient_response', 'text', 'message']
                found = False
                for key in keys_to_check:
                    if key in ai_response_raw and ai_response_raw[key]:
                        patient_response_text = ai_response_raw[key]
                        found = True
                        break
                
                if not found:
                    # Si aucune clé standard, on prend la première valeur string trouvée
                    logger.warning(f"   ⚠️ [REQ-{correlation_id}] Structure JSON IA inconnue: {ai_response_raw.keys()}")
                    for v in ai_response_raw.values():
                        if isinstance(v, str):
                            patient_response_text = v
                            break
            elif isinstance(ai_response_raw, str):
                patient_response_text = ai_response_raw
            
            # Nettoyage final (suppression de guillemets parasites, etc.)
            patient_response_text = self._clean_text_response(patient_response_text)

            execution_time = time.time() - start_time
            logger.info(f"   🏁 [REQ-{correlation_id}] FIN GÉNÉRATION ({execution_time:.2f}s)")
            logger.info(f"   🗣️ [PATIENT] : {patient_response_text[:100]}...")

            return patient_response_text

        except Exception as e:
            logger.error(f"   ❌ [REQ-{correlation_id}] ERREUR CRITIQUE DANS PATIENT_ACTOR: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback en cas de crash complet pour ne pas casser l'UI
            return "Je... excusez-moi, j'ai un moment d'absence. Pouvez-vous répéter ?"

    # ==============================================================================
    # MÉTHODES PRIVÉES (HELPER METHODS)
    # ==============================================================================

    def _get_or_create_persona(self, case: models.ClinicalCase) -> Dict[str, Any]:
        """
        Génère un persona cohérent et déterministe basé sur l'ID du cas.
        Cela garantit que si on relance la session, le patient a le même nom/âge.
        """
        # Utiliser l'ID du cas comme graine (seed) pour le générateur aléatoire
        seed_value = case.id if case.id else 12345
        rng = random.Random(seed_value)

        # Banques de données pour la génération
        noms_famille = ["Kamga", "Abessolo", "Nguema", "Tchatat", "Mbarga", "Eto'o", "Fossi", "Minka", "Onana", "Siewe"]
        prenoms_h = ["Jean", "Pierre", "Paul", "Joseph", "Emmanuel", "Samuel", "Roger", "Alain"]
        prenoms_f = ["Marie", "Suzanne", "Jeanne", "Bernadette", "Chantal", "Solange", "Carine", "Odile"]
        
        metiers_ville = ["Commerçant", "Enseignant", "Fonctionnaire", "Chauffeur de taxi", "Étudiant", "Comptable"]
        metiers_campagne = ["Agriculteur", "Éleveur", "Commerçant", "Retraité"]
        
        # Détermination du genre (50/50 ou basé sur le cas si spécifié plus tard)
        genre = rng.choice(["H", "F"])
        
        # Génération
        nom = rng.choice(noms_famille)
        prenom = rng.choice(prenoms_h) if genre == "H" else rng.choice(prenoms_f)
        full_name = f"{prenom} {nom}"
        
        # Âge : on essaie de le parser de l'histoire, sinon aléatoire cohérent
        age = rng.randint(25, 75)
        raw_history = str(case.presentation_clinique.get('histoire_maladie', ''))
        # Tentative naïve d'extraction d'âge par regex (ex: "Patient de 45 ans")
        age_match = re.search(r'(\d{2})\s*ans', raw_history)
        if age_match:
            age = int(age_match.group(1))
            logger.debug(f"      -> Âge extrait du texte : {age} ans")
        
        # Contexte social
        milieu = rng.choice(["Ville", "Campagne"])
        metier = rng.choice(metiers_ville) if milieu == "Ville" else rng.choice(metiers_campagne)
        
        # Niveau d'éducation (impacte le vocabulaire)
        education_level = rng.choice(["primaire (parle simplement)", "secondaire (vocabulaire standard)", "universitaire (articulé)"])
        
        # Niveau de stress (1-10)
        # On augmente le stress si le cas est grave (niveau_difficulte)
        base_stress = rng.randint(1, 5)
        case_severity = case.niveau_difficulte if case.niveau_difficulte else 1
        stress_level = min(10, base_stress + int(case_severity / 2))

        return {
            "nom": full_name,
            "genre": genre,
            "age": f"{age} ans",
            "metier": metier,
            "education": education_level,
            "stress_level": stress_level,
            "trait": rng.choice(["Bavard", "Timide", "Anxieux", "Stoïque", "Impatient", "Confus"])
        }

    def _extract_clinical_data(self, db: Session, case: models.ClinicalCase) -> Dict[str, str]:
        """
        Transforme les données relationnelles/JSON de la BDD en texte narratif pour le prompt.
        """
        # 1. Histoire
        presentation = case.presentation_clinique or {}
        histoire = presentation.get("histoire_maladie", "Pas d'histoire disponible.")
        
        # 2. Symptômes
        # Les symptômes sont souvent stockés sous forme d'IDs dans le JSON presentation_clinique
        # Structure attendue : [{'symptome_id': 123, 'details': '...'}, ...]
        symptomes_txt = []
        raw_symptoms = presentation.get("symptomes_patient", [])
        
        if isinstance(raw_symptoms, list):
            for item in raw_symptoms:
                if isinstance(item, dict):
                    s_id = item.get("symptome_id")
                    details = item.get("details", "")
                    
                    # Récupération du nom du symptôme
                    symptom_name = "Symptôme inconnu"
                    if s_id:
                        symptom_obj = db.query(models.Symptom).filter(models.Symptom.id == s_id).first()
                        if symptom_obj:
                            symptom_name = symptom_obj.nom
                            # Ajout du nom local si disponible pour plus de réalisme
                            if symptom_obj.nom_local:
                                symptom_name += f" (ou '{symptom_obj.nom_local}')"
                    
                    line = f"- {symptom_name}"
                    if details:
                        line += f" : {details}"
                    symptomes_txt.append(line)
        
        if not symptomes_txt:
            symptomes_txt = ["Aucun symptôme spécifique listé (improviser selon l'histoire)."]

        # 3. Antécédents
        antecedents_raw = presentation.get("antecedents", {})
        antecedents_txt = "Aucun antécédent notable."
        if isinstance(antecedents_raw, dict):
            # Transformation simple du dict en texte
            parts = []
            for k, v in antecedents_raw.items():
                if isinstance(v, list):
                    v_str = ", ".join(v)
                    parts.append(f"{k}: {v_str}")
                else:
                    parts.append(f"{k}: {v}")
            if parts:
                antecedents_txt = "\n".join(parts)
        elif isinstance(antecedents_raw, str):
            antecedents_txt = antecedents_raw

        return {
            "histoire": histoire,
            "symptomes": "\n".join(symptomes_txt),
            "antecedents": antecedents_txt
        }

    def _analyze_recent_events(self, db: Session, session_id: UUID) -> Optional[str]:
        """
        Vérifie les logs d'interaction pour voir si des actions pertinentes ont eu lieu
        récemment (ex: prise de médicament) et adapte le contexte.
        """
        # Récupérer les 5 dernières actions
        recent_logs = db.query(models.InteractionLog).filter(
            models.InteractionLog.session_id == session_id
        ).order_by(models.InteractionLog.timestamp.desc()).limit(5).all()
        
        context_updates = []
        
        for log in recent_logs:
            # Exemple : Si l'étudiant a prescrit un antidouleur
            # Note: Il faudrait une logique plus poussée pour mapper les types de médicaments
            # Ici on fait une détection basique sur le nom de l'action
            content = log.action_content or {}
            action_name = str(content.get("name", "")).lower()
            
            if "paracétamol" in action_name or "morphine" in action_name or "antalgique" in action_name:
                context_updates.append("Le médecin t'a donné un médicament contre la douleur. Tu commences à te sentir un peu soulagé.")
            
            if "examen" in action_name:
                context_updates.append(f"Le médecin t'a fait passer un examen : {action_name}. Tu attends les résultats.")

        if context_updates:
            return "\n".join(context_updates)
        return None

    def _get_raw_chat_history(self, db: Session, session_id: UUID, limit: int = 10) -> List[models.ChatMessage]:
        """Récupère les objets messages bruts."""
        return db.query(models.ChatMessage).filter(
            models.ChatMessage.session_id == session_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(limit).all()[::-1] # Ordre chronologique

    def _format_chat_history(self, db: Session, session_id: UUID, limit: int = 10) -> str:
        """Formate l'historique en bloc de texte pour le log ou le debug."""
        msgs = self._get_raw_chat_history(db, session_id, limit)
        txt = ""
        for m in msgs:
            txt += f"[{m.sender}]: {m.content}\n"
        return txt

    def _convert_payload_to_text(self, messages: List[Dict[str, str]]) -> str:
        """
        Convertit la liste de messages structurés en un prompt textuel unique
        pour l'API d'IA actuelle.
        """
        prompt = ""
        for msg in messages:
            role = msg['role'].upper()
            content = msg['content']
            prompt += f"\n--- {role} ---\n{content}\n"
        
        prompt += "\n--- ASSISTANT (PATIENT) ---\n"
        return prompt

    def _clean_text_response(self, text: str) -> str:
        """
        Nettoie la réponse générée par l'IA pour enlever les artefacts.
        """
        if not text:
            return "..."
            
        # Supprimer les balises JSON si l'IA a halluciné du JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
            try:
                data = json.loads(text)
                # Chercher une valeur textuelle
                return str(list(data.values())[0])
            except:
                pass
        
        # Supprimer les préfixes de rôle que l'IA ajoute parfois
        text = re.sub(r'^(Patient|Assistant|Moi) :', '', text, flags=re.IGNORECASE)
        
        # Supprimer les guillemets englobants
        text = text.strip().strip('"').strip("'")
        
        return text

# Instance globale prête à l'emploi
patient_actor_service = PatientActorService()
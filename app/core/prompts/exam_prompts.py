#=== Fichier: ./app/core/prompts/exam_prompts.py ===

import logging
import json
import datetime
from typing import Dict, Any, Optional, List

# ==============================================================================
# CONFIGURATION DU LOGGER SPÉCIFIQUE
# ==============================================================================
# Ce logger est dédié à la construction des prompts d'examens.
# Il est configuré pour être très verbeux afin de tracer chaque variable injectée.
logger = logging.getLogger("exam_prompts")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - [PROMPT-BUILDER] - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ExamPromptBuilder:
    """
    Classe responsable de la construction des instructions (Prompts) pour la
    génération de résultats d'examens médicaux (Biologie, Imagerie, Constantes).
    
    PRINCIPE :
    Cette classe ne génère pas le résultat, elle génère la "recette" très précise
    que le LLM devra suivre pour produire le résultat.
    """

    def __init__(self):
        logger.info("🔧 Initialisation du ExamPromptBuilder")
        
        # Template pour les examens de Biologie (Sang, Urine, LCR...)
        self.BIOLOGY_TEMPLATE = """
TU ES UN AUTOMATE DE LABORATOIRE D'ANALYSES MÉDICALES DE HAUTE PRÉCISION.
Ton rôle est de générer un rapport d'analyse biologique structuré.

--- CONTEXTE PATIENT (DONNÉES PROTEGÉES) ---
Sexe : {sexe}
Âge : {age}
Pathologie Réelle (Inconnue de l'étudiant) : {pathologie_nom}
Gravité : {gravite}/5

--- VÉRITÉ TERRAIN (DONNÉES BRUTES DU CAS) ---
Voici les anomalies biologiques réellement présentes chez ce patient.
Tu DOIS impérativement inclure ces valeurs dans ton rapport si l'examen demandé les couvre.
{donnees_cachees_json}

--- DEMANDE DE L'ÉTUDIANT ---
Examen demandé : "{nom_examen}"
Justification fournie : "{justification}"

--- ALGORITHME DE GÉNÉRATION (RÈGLES ABSOLUES) ---
1. PERTINENCE : L'examen demandé couvre-t-il les anomalies listées dans la "VÉRITÉ TERRAIN" ?
   - OUI : Génère un rapport montrant ces anomalies précises (chiffres anormaux, rouge, gras).
   - NON : Génère un rapport STRICTEMENT NORMAL pour cet examen. Ne pas inventer de pathologie.

2. STYLE : Utilise un format technique professionnel (Paramètre | Valeur | Unité | Normes).
   - Pour une NFS : Hématies, Hb, VGM, TCMH, Plaquettes, Leucocytes...
   - Pour un Ionogramme : Na+, K+, Cl-, Réserves alcalines...
   - Pour CRP : Valeur numérique.

3. COHÉRENCE : 
   - Si le patient est infecté (selon la pathologie), les marqueurs infectieux (CRP, Leucocytes) doivent être cohérents.
   - Si le patient anémique, l'hémoglobine doit être basse.

4. FORMAT DE SORTIE : JSON STRICT.
{{
  "type_resultat": "biologie",
  "valeurs_cles": {{ "Nom Paramètre": "Valeur + Unité" }},  <-- Résumé des 3-4 valeurs les plus importantes
  "rapport_complet": "Le texte complet du rapport avec tableau des valeurs...",
  "conclusion": "Conclusion courte du biologiste (ex: 'Syndrome inflammatoire biologique', 'Bilan normal')."
}}
"""

        # Template pour l'Imagerie (Radio, Scanner, IRM, Écho)
        self.IMAGING_TEMPLATE = """
TU ES UN RADIOLOGUE EXPERT (Senior).
Ton rôle est de rédiger le compte-rendu d'un examen d'imagerie.

--- CONTEXTE PATIENT ---
Sexe : {sexe}
Âge : {age}
Pathologie Réelle : {pathologie_nom}

--- VÉRITÉ TERRAIN (IMAGERIE) ---
Anomalies visuelles théoriques associées à cette pathologie :
{description_lesions}

Données spécifiques ce cas (si disponibles) :
{donnees_cachees_json}

--- DEMANDE ---
Examen : "{nom_examen}"
Justification : "{justification}"

--- ALGORITHME DE GÉNÉRATION ---
1. PERTINENCE : Cet examen peut-il voir la pathologie ? 
   (Ex: Une Radio Thorax VOIT une pneumonie, mais NE VOIT PAS une méningite).
   - SI VISIBLE : Décris les lésions typiques de la pathologie (opacités, fractures, épanchement...).
   - SI INVISIBLE ou HORS ZONE : Rédige un compte-rendu NORMAL (ex: "Transparence pulmonaire normale").

2. STYLE :
   - Technique, descriptif, anatomique.
   - Utilise des termes comme "Opacité", "Hyperclarté", "Hypersignal", "Echostructure".
   - Structure : Indication -> Technique -> Résultats -> Conclusion.

3. FORMAT DE SORTIE : JSON STRICT.
{{
  "type_resultat": "imagerie",
  "zone_etudiee": "ex: Thorax",
  "protocole": "ex: Incidence face et profil",
  "rapport_complet": "Description détaillée...",
  "conclusion": "Conclusion du radiologue (ex: 'Image en faveur d'une pneumopathie lobaire inférieure droite')."
}}
"""

        # Template générique (Constantes, ECG, etc.)
        self.GENERIC_TEMPLATE = """
TU ES UN APPAREIL MÉDICAL OU UN INFIRMIER.
Tâche : Fournir le résultat de : "{nom_examen}".

CONTEXTE PATIENT : {pathologie_nom}, Gravité {gravite}/5.
DONNÉES PHYSIOLOGIQUES RÉELLES : 
{donnees_cachees_json}

CONSIGNE :
Génère des valeurs réalistes. 
Si l'examen est "Constantes" ou "Vitaux", fournis : TA, FC, FR, SpO2, Temp.
Si l'examen est "ECG", décris le rythme et les ondes.

FORMAT DE SORTIE : JSON STRICT.
{{
  "type_resultat": "autre",
  "rapport_complet": "Liste des valeurs ou description...",
  "conclusion": "Synthèse rapide."
}}
"""

    def build_prompt(
        self, 
        case_data: Dict[str, Any], 
        exam_request: Dict[str, str],
        patient_persona: Dict[str, Any]
    ) -> str:
        """
        Construit le prompt final en choisissant le bon template et en injectant les données.
        
        :param case_data: Dictionnaire contenant 'pathologie', 'donnees_paracliniques', etc.
        :param exam_request: Dictionnaire {'name': '...', 'type': '...', 'justification': '...'}
        :param patient_persona: Dictionnaire {'age': '...', 'genre': '...'}
        """
        request_id = f"PRMPT-{id(exam_request) % 10000}"
        logger.info(f"🔨 [{request_id}] Construction du prompt pour : {exam_request.get('name')}")

        # 1. Analyse du type d'examen pour choisir le template
        exam_name = exam_request.get('name', '').lower()
        exam_type = exam_request.get('type', '').lower() # ex: 'biologie', 'imagerie'
        
        template_to_use = self.GENERIC_TEMPLATE
        template_name = "GENERIC"

        # Détection heuristique si le type n'est pas explicite
        if 'bio' in exam_type or 'sang' in exam_name or 'nfs' in exam_name or 'crp' in exam_name or 'urine' in exam_name:
            template_to_use = self.BIOLOGY_TEMPLATE
            template_name = "BIOLOGY"
        elif 'image' in exam_type or 'radio' in exam_name or 'scanner' in exam_name or 'irm' in exam_name or 'echo' in exam_name:
            template_to_use = self.IMAGING_TEMPLATE
            template_name = "IMAGING"
        
        logger.debug(f"   [{request_id}] Template sélectionné : {template_name}")

        # 2. Préparation des données d'injection (Data Cleaning)
        # On s'assure que les données ne sont jamais 'None' pour éviter les crashs de formatage
        
        pathologie_nom = case_data.get('pathologie_principale', {}).get('nom_fr', 'Pathologie indéterminée')
        gravite = case_data.get('niveau_gravite', 3)
        
        # Données cachées (C'est le trésor !)
        # On va chercher dans 'donnees_paracliniques' qui est un JSON en BDD
        hidden_data = case_data.get('donnees_paracliniques', {})
        if not hidden_data:
            hidden_data = {"note": "Aucune donnée spécifique pré-enregistrée. Improviser selon la pathologie."}
        
        hidden_data_str = json.dumps(hidden_data, ensure_ascii=False, indent=2)
        
        # Pour l'imagerie, on essaie d'extraire des infos spécifiques sur les lésions
        description_lesions = "Lésions classiques associées à cette pathologie."
        if template_name == "IMAGING":
            # On regarde si on a une description dans le cas
            desc = case_data.get('description', '')
            physio = case_data.get('physiopathologie', '')
            description_lesions = f"Base physiopathologique : {physio}\nContexte : {desc}"

        logger.debug(f"   [{request_id}] Injection des données : Patho='{pathologie_nom}', Gravité={gravite}")
        logger.debug(f"   [{request_id}] Données cachées injectées (taille) : {len(hidden_data_str)} chars")

        # 3. Formatage final
        try:
            final_prompt = template_to_use.format(
                sexe=patient_persona.get('genre', 'Non spécifié'),
                age=patient_persona.get('age', 'Non spécifié'),
                pathologie_nom=pathologie_nom,
                gravite=gravite,
                donnees_cachees_json=hidden_data_str,
                nom_examen=exam_request.get('name', 'Examen inconnu'),
                justification=exam_request.get('justification', 'Aucune justification'),
                # Arguments spécifiques aux templates (on utilise **kwargs style ou defaults)
                description_lesions=description_lesions 
            )
            
            logger.info(f"   ✅ [{request_id}] Prompt construit avec succès ({len(final_prompt)} chars).")
            
            # LOG DU PROMPT COMPLET (Pour le debug expert)
            logger.debug(f"\n{'='*20} [{request_id}] CONTENU DU PROMPT {'='*20}")
            logger.debug(final_prompt)
            logger.debug(f"{'='*60}\n")
            
            return final_prompt

        except KeyError as e:
            logger.error(f"   ❌ [{request_id}] Erreur de formatage du template : Clé manquante {e}")
            # Fallback de secours
            return f"Génère un résultat pour l'examen {exam_name} concernant un patient atteint de {pathologie_nom}."
        except Exception as e:
            logger.error(f"   ❌ [{request_id}] Erreur inattendue : {str(e)}")
            raise e

# Instance Singleton pour utilisation directe
exam_prompt_builder = ExamPromptBuilder()
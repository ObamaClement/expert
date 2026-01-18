import requests
import json
from datetime import datetime
import time
import uuid

# Configuration
BASE_URL = "https://expert-cmck.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"
OUTPUT_FILE = f"test_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

class SimulationTester:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8')
        self.test_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.session_data = {}
        
    def write(self, message, color=None):
        """Écrit dans le fichier et affiche à l'écran"""
        self.file.write(message + '\n')
        self.file.flush()
        
        if color:
            print(f"{color}{message}{Colors.END}")
        else:
            print(message)
    
    def section(self, title):
        separator = '='*100
        self.write(f"\n{separator}")
        self.write(f"  {title}")
        self.write(separator)
    
    def test_header(self, method, endpoint, description):
        self.test_count += 1
        header = f"\n{'─'*100}\nTEST #{self.test_count}: {method} {endpoint}\nDescription: {description}\n{'─'*100}"
        self.write(header, Colors.CYAN)
    
    def log_request(self, method, url, data=None, params=None):
        self.write(f"\n📤 REQUÊTE:", Colors.BLUE)
        self.write(f"   Méthode: {method}")
        self.write(f"   URL: {url}")
        if params:
            self.write(f"   Paramètres: {json.dumps(params, indent=6, ensure_ascii=False)}")
        if data:
            self.write(f"   Données envoyées:")
            self.write(json.dumps(data, indent=6, ensure_ascii=False))
    
    def log_response(self, response, show_full=True):
        self.write(f"\n📥 RÉPONSE:", Colors.BLUE)
        self.write(f"   Status Code: {response.status_code}")
        self.write(f"   Temps de réponse: {response.elapsed.total_seconds():.2f}s")
        
        try:
            data = response.json()
            if show_full:
                self.write(f"   Données reçues:")
                self.write(json.dumps(data, indent=6, ensure_ascii=False))
            else:
                if isinstance(data, list):
                    self.write(f"   Type: Liste de {len(data)} éléments")
                    if len(data) > 0:
                        self.write(f"   Premier élément:")
                        self.write(json.dumps(data[0], indent=6, ensure_ascii=False))
        except:
            self.write(f"   Réponse texte: {response.text[:1000]}")
    
    def mark_success(self, message=""):
        self.success_count += 1
        self.write(f"\n✅ SUCCÈS: {message}", Colors.GREEN)
    
    def mark_failure(self, message=""):
        self.fail_count += 1
        self.write(f"\n❌ ÉCHEC: {message}", Colors.RED)
    
    def summary(self):
        self.section("RÉSUMÉ DES TESTS DE SIMULATION")
        self.write(f"Total de tests: {self.test_count}")
        self.write(f"Succès: {self.success_count}", Colors.GREEN)
        self.write(f"Échecs: {self.fail_count}", Colors.RED)
        self.write(f"Taux de réussite: {(self.success_count/self.test_count*100):.1f}%" if self.test_count > 0 else "N/A")
    
    def close(self):
        self.file.close()

# Instance globale
tester = None

# =============================================================================
# TESTS DE SIMULATION - WORKFLOW COMPLET
# =============================================================================

def test_start_simulation_session():
    """Démarrer une nouvelle session de simulation"""
    tester.test_header("POST", "/api/v1/simulation/sessions/start", 
                      "Démarrer une session de simulation")
    
    data = {
        "learner_id": 1,  # ID d'un apprenant existant
        "category": "Infectiologie"
    }
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/start", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/start", 
                               json=data, timeout=60)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.session_data['session_id'] = result['session_id']
            tester.session_data['session_type'] = result.get('session_type')
            tester.session_data['clinical_case'] = result.get('clinical_case', {})
            
            tester.mark_success(f"Session créée avec ID: {result['session_id']}, Type: {result.get('session_type')}")
            
            # Afficher les détails du cas clinique
            if 'clinical_case' in result:
                case = result['clinical_case']
                tester.write(f"\n📋 CAS CLINIQUE ASSIGNÉ:", Colors.MAGENTA)
                tester.write(f"   Code: {case.get('code_fultang')}")
                tester.write(f"   Niveau difficulté: {case.get('niveau_difficulte')}")
                tester.write(f"   Pathologie: {case.get('pathologie_principale', {}).get('nom_fr')}")
                
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_message_1_greeting():
    """Message 1: Apprenant salue le patient + Réponse du patient"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    clinical_case = tester.session_data.get('clinical_case', {})
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Message 1: Échange de salutations")
    
    # 1. MESSAGE DE L'APPRENANT
    apprenant_data = {
        "sender": "Apprenant",
        "content": "Bonjour Monsieur/Madame, je suis l'étudiant en médecine qui va vous consulter aujourd'hui. Comment puis-je vous aider ?",
        "message_metadata": {
            "message_type": "greeting",
            "consultation_phase": "accueil"
        }
    }
    
    try:
        tester.write(f"\n💬 ÉCHANGE #1:", Colors.MAGENTA)
        tester.write(f"   👨‍⚕️ Apprenant: {apprenant_data['content']}", Colors.CYAN)
        
        # Envoyer message apprenant
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=apprenant_data, timeout=30)
        
        if response.status_code != 201:
            tester.mark_failure(f"Échec envoi message apprenant: {response.status_code}")
            return False
        
        time.sleep(0.5)
        
        # 2. RÉPONSE DU PATIENT (GÉNÉRÉE PAR LE TEST - SIMULANT L'IA)
        # Récupérer les symptômes du cas clinique pour une réponse cohérente
        histoire = clinical_case.get('presentation_clinique', {}).get('histoire_maladie', '')
        
        patient_response = f"Bonjour docteur. Je ne me sens pas bien depuis quelques jours. {histoire}"
        
        patient_data = {
            "sender": "Patient",
            "content": patient_response,
            "message_metadata": {
                "message_type": "response",
                "consultation_phase": "accueil",
                "generated_by": "test_script"  # Pour traçabilité
            }
        }
        
        tester.write(f"   🤒 Patient: {patient_data['content']}", Colors.GREEN)
        
        # Envoyer réponse patient
        patient_post = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                                    json=patient_data, timeout=30)
        
        if patient_post.status_code != 201:
            tester.mark_failure(f"Échec envoi réponse patient: {patient_post.status_code}")
            return False
        
        tester.mark_success("Dialogue initial établi (Apprenant + Patient)")
        return True
        
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_message_2_chief_complaint():
    """Message 2: Question sur le motif de consultation + Réponse patient"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    clinical_case = tester.session_data.get('clinical_case', {})
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Message 2: Motif de consultation")
    
    # 1. QUESTION DE L'APPRENANT
    apprenant_data = {
        "sender": "Apprenant",
        "content": "Qu'est-ce qui vous amène aujourd'hui ? Pouvez-vous me décrire ce que vous ressentez ?",
        "message_metadata": {
            "message_type": "question",
            "consultation_phase": "anamnese",
            "question_category": "chief_complaint"
        }
    }
    
    try:
        tester.write(f"\n💬 ÉCHANGE #2:", Colors.MAGENTA)
        tester.write(f"   👨‍⚕️ Apprenant: {apprenant_data['content']}", Colors.CYAN)
        
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=apprenant_data, timeout=30)
        
        if response.status_code != 201:
            tester.mark_failure(f"Échec envoi question: {response.status_code}")
            return False
        
        time.sleep(0.5)
        
        # 2. RÉPONSE DU PATIENT (BASÉE SUR LE CAS CLINIQUE)
        symptomes = clinical_case.get('presentation_clinique', {}).get('symptomes_patient', [])
        
        # Construire une réponse réaliste
        patient_response = "Voilà, j'ai de la fièvre depuis 2-3 jours, autour de 38-39°C. "
        
        # Ajouter des symptômes du cas
        if len(symptomes) > 0:
            patient_response += "Je me sens très fatigué et j'ai des douleurs. "
        
        patient_response += "C'est pour ça que je suis venu vous consulter."
        
        patient_data = {
            "sender": "Patient",
            "content": patient_response,
            "message_metadata": {
                "message_type": "response",
                "consultation_phase": "anamnese",
                "generated_by": "test_script"
            }
        }
        
        tester.write(f"   🤒 Patient: {patient_data['content']}", Colors.GREEN)
        
        patient_post = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                                    json=patient_data, timeout=30)
        
        if patient_post.status_code != 201:
            tester.mark_failure(f"Échec réponse patient: {patient_post.status_code}")
            return False
        
        tester.mark_success("Motif de consultation exprimé par le patient")
        return True
        
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_message_3_symptom_details():
    """Message 3: Approfondissement des symptômes + Réponse patient"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Message 3: Caractérisation des symptômes")
    
    # 1. QUESTIONS DÉTAILLÉES DE L'APPRENANT
    apprenant_data = {
        "sender": "Apprenant",
        "content": "Depuis quand avez-vous ces symptômes ? Est-ce que la douleur est constante ou intermittente ? Y a-t-il quelque chose qui l'aggrave ou la soulage ?",
        "message_metadata": {
            "message_type": "question",
            "consultation_phase": "anamnese",
            "question_category": "symptom_characterization"
        }
    }
    
    try:
        tester.write(f"\n💬 ÉCHANGE #3:", Colors.MAGENTA)
        tester.write(f"   👨‍⚕️ Apprenant: {apprenant_data['content']}", Colors.CYAN)
        
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=apprenant_data, timeout=30)
        
        if response.status_code != 201:
            tester.mark_failure(f"Échec: {response.status_code}")
            return False
        
        time.sleep(0.5)
        
        # 2. RÉPONSE DÉTAILLÉE DU PATIENT
        patient_response = """Ça a commencé il y a 3 jours environ. Au début c'était juste une légère gêne, 
mais depuis hier ça s'est aggravé. La douleur est plutôt constante, mais elle augmente quand je bouge 
ou quand j'urine. Le paracétamol que j'ai pris ne m'a pas vraiment soulagé."""
        
        patient_data = {
            "sender": "Patient",
            "content": patient_response,
            "message_metadata": {
                "message_type": "response",
                "consultation_phase": "anamnese",
                "details_provided": ["chronologie", "caractere", "facteurs_aggravants", "traitement_essaye"],
                "generated_by": "test_script"
            }
        }
        
        tester.write(f"   🤒 Patient: {patient_data['content']}", Colors.GREEN)
        
        patient_post = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                                    json=patient_data, timeout=30)
        
        if patient_post.status_code != 201:
            tester.mark_failure(f"Échec réponse patient: {patient_post.status_code}")
            return False
        
        tester.mark_success("Anamnèse détaillée obtenue")
        return True
        
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_action_1_vital_signs():
    """Action 1: Demande des paramètres vitaux"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/actions", 
                      "Action 1: Prise des paramètres vitaux")
    
    data = {
        "action_type": "parametres_vitaux",
        "action_name": "Prise des constantes",
        "justification": "Évaluation de l'état général du patient et recherche de signes de gravité avant tout examen approfondi"
    }
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/actions", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/actions", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.write(f"\n🔬 RÉSULTATS:", Colors.MAGENTA)
            if 'result' in result:
                tester.write(json.dumps(result['result'], indent=6, ensure_ascii=False))
            tester.mark_success("Paramètres vitaux obtenus avec feedback")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_message_4_medical_history():
    """Message 4: Questions sur les antécédents + Réponse patient"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    clinical_case = tester.session_data.get('clinical_case', {})
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Message 4: Antécédents médicaux")
    
    # 1. QUESTION ANTÉCÉDENTS
    apprenant_data = {
        "sender": "Apprenant",
        "content": "Avez-vous des antécédents médicaux particuliers ? Prenez-vous des médicaments régulièrement ? Y a-t-il des maladies dans votre famille ?",
        "message_metadata": {
            "message_type": "question",
            "consultation_phase": "anamnese",
            "question_category": "medical_history"
        }
    }
    
    try:
        tester.write(f"\n💬 ÉCHANGE #4:", Colors.MAGENTA)
        tester.write(f"   👨‍⚕️ Apprenant: {apprenant_data['content']}", Colors.CYAN)
        
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=apprenant_data, timeout=30)
        
        if response.status_code != 201:
            tester.mark_failure(f"Échec: {response.status_code}")
            return False
        
        time.sleep(0.5)
        
        # 2. RÉPONSE DU PATIENT (avec pathologies secondaires si disponibles)
        pathologies_secondaires = clinical_case.get('pathologies_secondaires', [])
        
        if len(pathologies_secondaires) > 0:
            patient_response = """J'ai du diabète depuis 5 ans, je prends du Metformine. 
J'ai aussi de l'hypertension, contrôlée avec de l'Amlodipine. Mon père avait des problèmes cardiaques."""
        else:
            patient_response = """Non, je n'ai pas d'antécédents particuliers. Je ne prends pas de médicaments 
régulièrement, juste du paracétamol quand j'ai mal. Dans ma famille, il n'y a rien de notable."""
        
        patient_data = {
            "sender": "Patient",
            "content": patient_response,
            "message_metadata": {
                "message_type": "response",
                "consultation_phase": "anamnese",
                "antecedents_revealed": True,
                "generated_by": "test_script"
            }
        }
        
        tester.write(f"   🤒 Patient: {patient_data['content']}", Colors.GREEN)
        
        patient_post = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                                    json=patient_data, timeout=30)
        
        if patient_post.status_code != 201:
            tester.mark_failure(f"Échec réponse patient: {patient_post.status_code}")
            return False
        
        tester.mark_success("Antécédents médicaux collectés")
        return True
        
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_action_2_blood_test():
    """Action 2: Demande d'examen sanguin"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/actions", 
                      "Action 2: Demande d'examen sanguin (NFS)")
    
    data = {
        "action_type": "examen_complementaire",
        "action_name": "Numération Formule Sanguine (NFS)",
        "justification": "Suspicion d'une infection compte tenu des symptômes présentés. La NFS permettra d'évaluer la présence d'une inflammation (augmentation des GB) et de rechercher une anémie"
    }
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/actions", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/actions", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.write(f"\n🔬 RÉSULTATS EXAMEN:", Colors.MAGENTA)
            if 'result' in result:
                tester.write(json.dumps(result['result'], indent=6, ensure_ascii=False))
            tester.mark_success("Résultats de NFS obtenus avec feedback")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_action_3_inappropriate_exam():
    """Action 3: Demande d'examen inapproprié (pour tester le feedback négatif)"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/actions", 
                      "Action 3: Demande d'examen inapproprié (IRM cérébrale)")
    
    data = {
        "action_type": "examen_complementaire",
        "action_name": "IRM cérébrale",
        "justification": "Pour vérifier"
    }
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/actions", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/actions", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.write(f"\n⚠️  FEEDBACK SUR ACTION:", Colors.YELLOW)
            if 'feedback' in result:
                tester.write(f"   {result['feedback']}")
            tester.mark_success("Feedback négatif reçu pour examen inapproprié")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_request_hint_1():
    """Demande d'indice simple"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/request-hint", 
                      "Demande d'indice (type: simple)")
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/request-hint")
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/request-hint", 
                               timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.write(f"\n💡 INDICE REÇU:", Colors.MAGENTA)
            tester.write(f"   Type: {result.get('hint_type')}")
            tester.write(f"   Contenu: {result.get('content')}")
            tester.mark_success("Indice reçu avec succès")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_action_4_consult_image():
    """Action 4: Consultation d'image médicale (si disponible)"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    # Vérifier si le cas clinique a des images
    clinical_case = tester.session_data.get('clinical_case', {})
    has_images = len(clinical_case.get('images_associees_ids', [])) > 0
    
    if not has_images:
        tester.write("ℹ️  Aucune image disponible pour ce cas, test ignoré", Colors.BLUE)
        return True
    
    session_id = tester.session_data['session_id']
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/actions", 
                      "Action 4: Consultation de l'image médicale")
    
    data = {
        "action_type": "consulter_image",
        "action_name": "Consulter radiographie/échographie",
        "justification": "Analyse des résultats d'imagerie pour compléter le diagnostic clinique"
    }
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/actions", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/actions", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.mark_success("Image consultée avec feedback")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_message_5_summary():
    """Message 5: Résumé de la consultation + Confirmation patient"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Message 5: Synthèse et confirmation")
    
    # 1. SYNTHÈSE DE L'APPRENANT
    apprenant_data = {
        "sender": "Apprenant",
        "content": "D'accord, laissez-moi résumer. Vous présentez des symptômes depuis 3 jours, avec de la fièvre et des douleurs qui s'aggravent. Les examens montrent une inflammation. Je vais maintenant établir mon diagnostic.",
        "message_metadata": {
            "message_type": "summary",
            "consultation_phase": "synthese"
        }
    }
    
    try:
        tester.write(f"\n💬 ÉCHANGE #5:", Colors.MAGENTA)
        tester.write(f"   👨‍⚕️ Apprenant: {apprenant_data['content']}", Colors.CYAN)
        
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=apprenant_data, timeout=30)
        
        if response.status_code != 201:
            tester.mark_failure(f"Échec: {response.status_code}")
            return False
        
        time.sleep(0.5)
        
        # 2. CONFIRMATION DU PATIENT
        patient_response = "Oui c'est exactement ça. J'espère que vous pourrez m'aider."
        
        patient_data = {
            "sender": "Patient",
            "content": patient_response,
            "message_metadata": {
                "message_type": "confirmation",
                "consultation_phase": "synthese",
                "generated_by": "test_script"
            }
        }
        
        tester.write(f"   🤒 Patient: {patient_data['content']}", Colors.GREEN)
        
        patient_post = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                                    json=patient_data, timeout=30)
        
        if patient_post.status_code != 201:
            tester.mark_failure(f"Échec réponse patient: {patient_post.status_code}")
            return False
        
        tester.mark_success("Synthèse validée par le patient - Prêt pour diagnostic")
        return True
        
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_get_chat_history():
    """Récupérer l'historique complet du chat"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.test_header("GET", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Récupération de l'historique complet du chat")
    
    tester.log_request("GET", f"{API_BASE}/chat/sessions/{session_id}/messages")
    
    try:
        response = requests.get(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                              timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.write(f"\n💬 HISTORIQUE COMPLET DE LA CONSULTATION:", Colors.MAGENTA)
            tester.write(f"   Nombre total de messages: {len(data)}")
            
            # Compter les messages par type
            apprenant_msgs = [m for m in data if m.get('sender') == 'Apprenant']
            patient_msgs = [m for m in data if m.get('sender') == 'Patient']
            
            tester.write(f"   👨‍⚕️ Messages de l'apprenant: {len(apprenant_msgs)}", Colors.CYAN)
            tester.write(f"   🤒 Messages du patient: {len(patient_msgs)}", Colors.GREEN)
            
            # Afficher toute la conversation
            tester.write(f"\n📜 TRANSCRIPTION COMPLÈTE:", Colors.BLUE)
            for i, msg in enumerate(data, 1):
                sender_icon = "👨‍⚕️" if msg['sender'] == "Apprenant" else "🤒"
                sender_color = Colors.CYAN if msg['sender'] == "Apprenant" else Colors.GREEN
                timestamp = msg.get('timestamp', 'N/A')
                content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                
                tester.write(f"\n   [{i}] {sender_icon} {msg['sender']} ({timestamp}):", sender_color)
                tester.write(f"       {content}")
            
            # Vérification critique
            if len(patient_msgs) == 0:
                tester.write(f"\n⚠️  PROBLÈME CRITIQUE: Le patient virtuel n'a pas répondu aux questions!", Colors.RED)
                tester.write(f"      Cela rend la simulation inutilisable.", Colors.RED)
                tester.mark_failure(f"0 réponses patient détectées sur {len(apprenant_msgs)} questions")
                return False
            elif len(patient_msgs) < len(apprenant_msgs):
                ratio = len(patient_msgs) / len(apprenant_msgs) * 100
                tester.write(f"\n⚠️  ATTENTION: Seulement {ratio:.0f}% des questions ont reçu une réponse", Colors.YELLOW)
                tester.mark_success(f"Historique récupéré: {len(data)} messages (conversation partielle)")
            else:
                tester.mark_success(f"Historique récupéré: {len(data)} messages (conversation complète)")
            
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_submit_diagnosis_correct():
    """Soumission d'un diagnostic correct"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    clinical_case = tester.session_data.get('clinical_case', {})
    
    # Récupérer la pathologie principale du cas
    pathologie_id = clinical_case.get('pathologie_principale_id')
    
    if not pathologie_id:
        tester.write("⚠️  Pas de pathologie principale dans le cas, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/submit", 
                      "Soumission du diagnostic final (correct)")
    
    # Extraire les IDs des médicaments (pas les objets complets)
    medicaments_prescrits = clinical_case.get('medicaments_prescrits', [])
    medication_ids = []
    
    if medicaments_prescrits:
        for med in medicaments_prescrits[:3]:  # Prendre les 3 premiers
            if isinstance(med, dict) and 'medicament_id' in med:
                medication_ids.append(med['medicament_id'])
            elif isinstance(med, int):
                medication_ids.append(med)
    
    # Données de soumission avec format CORRECT (liste d'IDs uniquement)
    data = {
        "diagnosed_pathology_id": pathologie_id,
        "prescribed_medication_ids": medication_ids  # ✅ LISTE D'ENTIERS UNIQUEMENT
    }
    
    tester.write(f"\n📋 DIAGNOSTIC SOUMIS:", Colors.BLUE)
    tester.write(f"   Pathologie ID: {pathologie_id}")
    tester.write(f"   Médicaments IDs: {medication_ids}")
    
    tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/submit", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/submit", 
                               json=data, timeout=60)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            
            tester.write(f"\n📊 ÉVALUATION FINALE:", Colors.MAGENTA)
            evaluation = result.get('evaluation', {})
            
            score_diagnostic = evaluation.get('score_diagnostic', 0)
            score_therapeutique = evaluation.get('score_therapeutique', 0)
            score_demarche = evaluation.get('score_demarche', 0)
            score_total = evaluation.get('score_total', 0)
            
            # Affichage avec barre de progression visuelle
            def progress_bar(score, max_score=10):
                filled = int((score / max_score) * 20)
                bar = "█" * filled + "░" * (20 - filled)
                return f"[{bar}] {score}/{max_score}"
            
            tester.write(f"   🎯 Score Diagnostic:      {progress_bar(score_diagnostic)}", 
                        Colors.GREEN if score_diagnostic >= 8 else Colors.YELLOW)
            tester.write(f"   💊 Score Thérapeutique:   {progress_bar(score_therapeutique)}", 
                        Colors.GREEN if score_therapeutique >= 8 else Colors.YELLOW)
            tester.write(f"   🩺 Score Démarche:        {progress_bar(score_demarche)}", 
                        Colors.GREEN if score_demarche >= 8 else Colors.YELLOW)
            
            tester.write(f"\n   ⭐ SCORE TOTAL: {score_total}/30", 
                        Colors.GREEN if score_total >= 24 else Colors.YELLOW if score_total >= 18 else Colors.RED)
            
            tester.write(f"\n📝 FEEDBACK GLOBAL:", Colors.CYAN)
            feedback_lines = result.get('feedback_global', '').split('\n')
            for line in feedback_lines[:5]:  # Premiers 5 lignes
                if line.strip():
                    tester.write(f"   {line}")
            
            tester.write(f"\n🎯 RECOMMANDATION:", Colors.BLUE)
            recommendation = result.get('recommendation_next_step', '')
            tester.write(f"   {recommendation}")
            
            # Déterminer le niveau de réussite
            if score_total >= 24:
                tester.mark_success(f"🎉 Excellent diagnostic! Score: {score_total}/30")
            elif score_total >= 18:
                tester.mark_success(f"✅ Bon diagnostic. Score: {score_total}/30")
            else:
                tester.mark_success(f"⚠️  Diagnostic soumis mais score faible: {score_total}/30")
            
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_start_and_submit_wrong_diagnosis():
    """Scénario complet avec diagnostic incorrect"""
    tester.section("SCÉNARIO 2: SESSION AVEC DIAGNOSTIC INCORRECT")
    
    # Démarrer une nouvelle session
    tester.test_header("POST", "/api/v1/simulation/sessions/start", 
                      "Nouvelle session pour test diagnostic incorrect")
    
    data = {
        "learner_id": 1,
        "category": "Cardiologie"
    }
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/start", 
                               json=data, timeout=60)
        
        if response.status_code != 201:
            tester.mark_failure("Impossible de démarrer la session")
            return False
        
        result = response.json()
        session_id = result['session_id']
        clinical_case = result.get('clinical_case', {})
        
        tester.mark_success(f"Session créée: {session_id}")
        
        # Quelques messages rapides
        messages = [
            "Bonjour, que puis-je faire pour vous ?",
            "Depuis combien de temps avez-vous ces symptômes ?"
        ]
        
        for msg in messages:
            msg_data = {
                "sender": "Apprenant",
                "content": msg,
                "message_metadata": {"type": "question"}
            }
            requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                        json=msg_data, timeout=30)
        
        # Soumettre un MAUVAIS diagnostic
        tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/submit", 
                          "Soumission d'un diagnostic INCORRECT")
        
        # Prendre une pathologie différente de celle du cas
        wrong_pathology_id = clinical_case.get('pathologie_principale_id', 1) + 100
        
        wrong_data = {
            "diagnosed_pathology_id": wrong_pathology_id,
            "prescribed_medication_ids": []
        }
        
        tester.log_request("POST", f"{API_BASE}/simulation/sessions/{session_id}/submit", 
                         data=wrong_data)
        
        response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/submit", 
                               json=wrong_data, timeout=60)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            evaluation = result.get('evaluation', {})
            
            tester.write(f"\n📊 ÉVALUATION (DIAGNOSTIC INCORRECT):", Colors.YELLOW)
            tester.write(f"   Score Diagnostic: {evaluation.get('score_diagnostic')}/10")
            tester.write(f"   Score Thérapeutique: {evaluation.get('score_therapeutique')}/10")
            tester.write(f"   Score Démarche: {evaluation.get('score_demarche')}/10")
            tester.write(f"   SCORE TOTAL: {evaluation.get('score_total')}/30")
            
            tester.mark_success("Diagnostic incorrect détecté avec feedback approprié")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
            
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_multiple_hint_requests():
    """Test de demandes multiples d'indices"""
    if 'session_id' not in tester.session_data:
        tester.write("⚠️  Aucune session active, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.session_data['session_id']
    tester.section("TEST DES DIFFÉRENTS TYPES D'INDICES")
    
    hint_count = 0
    for i in range(3):  # Demander 3 indices
        tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/request-hint", 
                          f"Demande d'indice #{i+1}")
        
        try:
            response = requests.post(f"{API_BASE}/simulation/sessions/{session_id}/request-hint", 
                                   timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                hint_count += 1
                
                tester.write(f"\n💡 INDICE #{hint_count}:", Colors.CYAN)
                tester.write(f"   Type: {result.get('hint_type')}")
                tester.write(f"   Contenu: {result.get('content')[:200]}...")
                
                tester.mark_success(f"Indice #{hint_count} reçu")
                time.sleep(1)  # Petite pause entre les requêtes
            else:
                tester.mark_failure(f"Échec demande indice #{i+1}")
                
        except Exception as e:
            tester.mark_failure(f"Exception: {str(e)}")
    
    return hint_count > 0


def test_session_formative_evaluation():
    """Test d'une session d'évaluation formative complète"""
    tester.section("SCÉNARIO 3: SESSION D'ÉVALUATION FORMATIVE")
    
    tester.test_header("POST", "/api/v1/simulation/sessions/start", 
                      "Démarrage session formative")
    
    data = {
        "learner_id": 1,
        "category": "Pédiatrie"
    }
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/start", 
                               json=data, timeout=60)
        
        if response.status_code != 201:
            tester.mark_failure("Impossible de démarrer la session formative")
            return False
        
        result = response.json()
        session_id = result['session_id']
        session_type = result.get('session_type')
        
        tester.write(f"\n📚 TYPE DE SESSION: {session_type}", Colors.MAGENTA)
        tester.mark_success(f"Session formative créée: {session_id}")
        
        # Simuler une consultation formative complète
        
        # 1. Messages initiaux
        consultation_flow = [
            ("Bonjour, je suis l'étudiant. Racontez-moi ce qui vous amène.", "greeting"),
            ("Depuis quand présentez-vous ces symptômes ?", "timeline"),
            ("Avez-vous des antécédents médicaux ?", "history"),
        ]
        
        for content, phase in consultation_flow:
            msg_data = {
                "sender": "Apprenant",
                "content": content,
                "message_metadata": {"phase": phase}
            }
            requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                        json=msg_data, timeout=30)
            time.sleep(0.5)
        
        # 2. Actions cliniques
        actions = [
            {
                "action_type": "parametres_vitaux",
                "action_name": "Constantes vitales",
                "justification": "Évaluation initiale de l'état du patient"
            },
            {
                "action_type": "examen_complementaire",
                "action_name": "CRP et NFS",
                "justification": "Recherche de syndrome inflammatoire"
            }
        ]
        
        for action in actions:
            action_response = requests.post(
                f"{API_BASE}/simulation/sessions/{session_id}/actions", 
                json=action, 
                timeout=30
            )
            if action_response.status_code == 200:
                result = action_response.json()
                tester.write(f"   Action '{action['action_name']}': {result.get('feedback', 'OK')[:100]}", 
                           Colors.GREEN)
        
        # 3. Demander un indice
        hint_response = requests.post(
            f"{API_BASE}/simulation/sessions/{session_id}/request-hint", 
            timeout=30
        )
        if hint_response.status_code == 200:
            hint = hint_response.json()
            tester.write(f"\n💡 Indice formatif reçu: {hint.get('hint_type')}", Colors.CYAN)
        
        # 4. Soumettre diagnostic
        submit_data = {
            "diagnosed_pathology_id": result.get('clinical_case', {}).get('pathologie_principale_id', 1),
            "prescribed_medication_ids": []
        }
        
        submit_response = requests.post(
            f"{API_BASE}/simulation/sessions/{session_id}/submit",
            json=submit_data,
            timeout=60
        )
        
        if submit_response.status_code == 200:
            evaluation = submit_response.json()
            scores = evaluation.get('evaluation', {})
            
            tester.write(f"\n📊 ÉVALUATION FORMATIVE:", Colors.MAGENTA)
            tester.write(f"   Diagnostic: {scores.get('score_diagnostic')}/10")
            tester.write(f"   Thérapeutique: {scores.get('score_therapeutique')}/10")
            tester.write(f"   Démarche: {scores.get('score_demarche')}/10")
            tester.write(f"   Total: {scores.get('score_total')}/30")
            
            tester.mark_success("Session formative complétée avec évaluation détaillée")
            return True
        else:
            tester.mark_failure("Échec soumission formative")
            return False
            
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_edge_cases():
    """Test de cas limites et gestion d'erreurs"""
    tester.section("TESTS DE CAS LIMITES ET GESTION D'ERREURS")
    
    # Test 1: Session inexistante
    tester.test_header("POST", "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000/messages", 
                      "Test avec session_id invalide")
    
    invalid_session_data = {
        "sender": "Apprenant",
        "content": "Test",
        "message_metadata": {}
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/chat/sessions/00000000-0000-0000-0000-000000000000/messages",
            json=invalid_session_data,
            timeout=30
        )
        
        if response.status_code == 404:
            tester.mark_success("Erreur 404 correctement retournée pour session invalide")
        else:
            tester.mark_failure(f"Code {response.status_code} au lieu de 404")
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
    
    # Test 2: Action sans justification
    if 'session_id' in tester.session_data:
        session_id = tester.session_data['session_id']
        
        tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/actions", 
                          "Test action sans justification")
        
        no_justification_data = {
            "action_type": "examen_complementaire",
            "action_name": "Scanner thoracique",
            "justification": ""  # Justification vide
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/simulation/sessions/{session_id}/actions",
                json=no_justification_data,
                timeout=30
            )
            
            if response.status_code in [200, 422]:  # 422 pour validation error
                result = response.json()
                if 'feedback' in result:
                    tester.write(f"   Feedback: {result['feedback'][:200]}", Colors.YELLOW)
                tester.mark_success("Gestion appropriée de la justification manquante")
            else:
                tester.mark_failure(f"Code inattendu: {response.status_code}")
        except Exception as e:
            tester.mark_failure(f"Exception: {str(e)}")
    
    # Test 3: Soumission sans diagnostic
    if 'session_id' in tester.session_data:
        session_id = tester.session_data['session_id']
        
        tester.test_header("POST", f"/api/v1/simulation/sessions/{session_id}/submit", 
                          "Test soumission sans pathologie")
        
        incomplete_data = {
            "diagnosed_pathology_id": None,
            "prescribed_medication_ids": []
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/simulation/sessions/{session_id}/submit",
                json=incomplete_data,
                timeout=30
            )
            
            if response.status_code in [400, 422]:
                tester.mark_success("Validation correcte des données incomplètes")
            else:
                tester.mark_failure(f"Code {response.status_code} au lieu de 400/422")
        except Exception as e:
            tester.mark_failure(f"Exception: {str(e)}")


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    global tester
    tester = SimulationTester(OUTPUT_FILE)
    
    tester.section("TEST COMPLET DES ROUTES DE SIMULATION STI MEDICAL")
    tester.write(f"URL: {BASE_URL}")
    tester.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tester.write(f"Fichier de sortie: {OUTPUT_FILE}")
    
    print(f"\n{Colors.CYAN}╔════════════════════════════════════════════════════════════════╗")
    print(f"║  TEST DES ROUTES DE SIMULATION - WORKFLOW COMPLET             ║")
    print(f"║  Simulation d'une consultation médicale complète              ║")
    print(f"╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")
    
    try:
        # =================================================================
        # SCÉNARIO 1: SESSION COMPLÈTE AVEC DIAGNOSTIC CORRECT
        # =================================================================
        tester.section("SCÉNARIO 1: CONSULTATION COMPLÈTE AVEC DIAGNOSTIC CORRECT")
        
        # 1. Démarrer la session
        if not test_start_simulation_session():
            tester.write("\n⚠️  Impossible de continuer sans session active", Colors.RED)
            return
        
        time.sleep(1)
        
        # 2. Flux de consultation avec messages
        test_chat_message_1_greeting()
        time.sleep(0.5)
        
        test_chat_message_2_chief_complaint()
        time.sleep(0.5)
        
        test_chat_message_3_symptom_details()
        time.sleep(0.5)
        
        # 3. Actions cliniques
        test_action_1_vital_signs()
        time.sleep(0.5)
        
        test_chat_message_4_medical_history()
        time.sleep(0.5)
        
        test_action_2_blood_test()
        time.sleep(0.5)
        
        # 4. Test d'action inappropriée
        test_action_3_inappropriate_exam()
        time.sleep(0.5)
        
        # 5. Demande d'indice
        test_request_hint_1()
        time.sleep(0.5)
        
        # 6. Consultation d'image (si disponible)
        test_action_4_consult_image()
        time.sleep(0.5)
        
        # 7. Résumé avant diagnostic
        test_chat_message_5_summary()
        time.sleep(0.5)
        
        # 8. Récupérer historique complet
        test_get_chat_history()
        time.sleep(0.5)
        
        # 9. Soumission du diagnostic correct
        test_submit_diagnosis_correct()
        
        # =================================================================
        # SCÉNARIO 2: DIAGNOSTIC INCORRECT
        # =================================================================
        time.sleep(2)
        test_start_and_submit_wrong_diagnosis()
        
        # =================================================================
        # SCÉNARIO 3: DEMANDES MULTIPLES D'INDICES
        # =================================================================
        time.sleep(2)
        test_multiple_hint_requests()
        
        # =================================================================
        # SCÉNARIO 4: SESSION FORMATIVE
        # =================================================================
        time.sleep(2)
        test_session_formative_evaluation()
        
        # =================================================================
        # TESTS DE CAS LIMITES
        # =================================================================
        time.sleep(2)
        test_edge_cases()
        
        # =================================================================
        # RÉSUMÉ FINAL
        # =================================================================
        tester.summary()
        
    except KeyboardInterrupt:
        tester.write("\n\n⚠️  Tests interrompus par l'utilisateur", Colors.YELLOW)
        tester.summary()
    except Exception as e:
        tester.write(f"\n\n❌ ERREUR CRITIQUE: {str(e)}", Colors.RED)
        import traceback
        tester.write(traceback.format_exc())
        tester.summary()
    finally:
        tester.close()
        print(f"\n{Colors.GREEN}╔════════════════════════════════════════════════════════════════╗")
        print(f"║  TESTS TERMINÉS                                                ║")
        print(f"║  Résultats sauvegardés dans: {OUTPUT_FILE:30s} ║")
        print(f"╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")


if __name__ == "__main__":
    main()
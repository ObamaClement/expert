import requests
import json
from datetime import datetime
import time
import uuid

# Configuration
BASE_URL = "https://appren-docker.onrender.com"
OUTPUT_FILE = f"test_api_learner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

class APITester:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8')
        self.test_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.created_ids = {}
        
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
                else:
                    self.write(f"   Données reçues:")
                    self.write(json.dumps(data, indent=6, ensure_ascii=False))
        except:
            self.write(f"   Réponse texte: {response.text[:500]}")
    
    def mark_success(self, message=""):
        self.success_count += 1
        self.write(f"\n✅ SUCCÈS: {message}", Colors.GREEN)
    
    def mark_failure(self, message=""):
        self.fail_count += 1
        self.write(f"\n❌ ÉCHEC: {message}", Colors.RED)
    
    def summary(self):
        self.section("RÉSUMÉ DES TESTS")
        self.write(f"Total de tests: {self.test_count}")
        self.write(f"Succès: {self.success_count}", Colors.GREEN)
        self.write(f"Échecs: {self.fail_count}", Colors.RED)
        self.write(f"Taux de réussite: {(self.success_count/self.test_count*100):.1f}%" if self.test_count > 0 else "N/A")
        
        if self.created_ids:
            self.write("\n📝 IDs créés pendant les tests:")
            for key, value in self.created_ids.items():
                self.write(f"   {key}: {value}")
    
    def close(self):
        self.file.close()
    
    def wait_for_user(self):
        """Attend que l'utilisateur appuie sur Entrée"""
        input(f"\n{Colors.YELLOW}⏸  Appuyez sur Entrée pour continuer...{Colors.END}")

# Instance globale
tester = None

# =============================================================================
# TESTS LEARNERS
# =============================================================================

def test_learners_create():
    tester.test_header("POST", "/learners/", "Créer un nouvel apprenant")
    
    data = {
        "matricule": f"TEST_{int(time.time())}",
        "nom": "Étudiant Test API",
        "email": f"test_{int(time.time())}@example.com",
        "niveau_etudes": "M2",
        "specialite_visee": "Médecine Générale",
        "langue_preferee": "Français",
        "date_inscription": datetime.now().isoformat()
    }
    
    tester.log_request("POST", f"{BASE_URL}/learners/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/learners/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['learner'] = result['id']
            tester.mark_success(f"Apprenant créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_learners_list():
    tester.test_header("GET", "/learners/", "Récupérer la liste des apprenants")
    
    tester.log_request("GET", f"{BASE_URL}/learners/")
    
    try:
        response = requests.get(f"{BASE_URL}/learners/", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} apprenants")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_learners_read():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/learners/{learner_id}", "Récupérer un apprenant par ID")
    
    tester.log_request("GET", f"{BASE_URL}/learners/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/learners/{learner_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Apprenant récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS COGNITIVE PROFILE
# =============================================================================

def test_cognitive_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/cognitive/", "Créer un profil cognitif")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "vitesse_assimilation": 7,
        "capacite_memoire_travail": 8,
        "tendance_impulsivite": 3,
        "prefer_visual": True
    }
    
    tester.log_request("POST", f"{BASE_URL}/cognitive/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/cognitive/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Profil cognitif créé")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_cognitive_read():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/cognitive/{learner_id}", "Récupérer le profil cognitif")
    
    tester.log_request("GET", f"{BASE_URL}/cognitive/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/cognitive/{learner_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Profil cognitif récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_cognitive_update():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("PUT", f"/cognitive/{learner_id}", "Mettre à jour le profil cognitif")
    
    data = {
        "learner_id": learner_id,
        "vitesse_assimilation": 9,
        "capacite_memoire_travail": 8,
        "tendance_impulsivite": 2,
        "prefer_visual": True
    }
    
    tester.log_request("PUT", f"{BASE_URL}/cognitive/{learner_id}", data=data)
    
    try:
        response = requests.put(f"{BASE_URL}/cognitive/{learner_id}", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Profil cognitif mis à jour")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS AFFECTIVE STATE
# =============================================================================

def test_affective_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/affective/", "Créer un état affectif")
    
    session_id = str(uuid.uuid4())
    tester.created_ids['session'] = session_id
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "stress_level": 3,
        "confidence_level": 7,
        "motivation_level": 8,
        "frustration_level": 2
    }
    
    tester.log_request("POST", f"{BASE_URL}/affective/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/affective/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("État affectif créé")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_affective_read_session():
    if 'session' not in tester.created_ids:
        tester.write("⚠️  Aucune session créée, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.created_ids['session']
    tester.test_header("GET", f"/affective/session/{session_id}", "Récupérer l'état affectif d'une session")
    
    tester.log_request("GET", f"{BASE_URL}/affective/session/{session_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/affective/session/{session_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("État affectif de session récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_affective_latest():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/affective/learner/{learner_id}/latest", "Récupérer le dernier état affectif")
    
    tester.log_request("GET", f"{BASE_URL}/affective/learner/{learner_id}/latest")
    
    try:
        response = requests.get(f"{BASE_URL}/affective/learner/{learner_id}/latest", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Dernier état affectif récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_affective_history():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/affective/learner/{learner_id}/history", "Récupérer l'historique affectif")
    
    tester.log_request("GET", f"{BASE_URL}/affective/learner/{learner_id}/history")
    
    try:
        response = requests.get(f"{BASE_URL}/affective/learner/{learner_id}/history", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Historique récupéré: {len(data)} entrées")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS COMPETENCY MASTERY
# =============================================================================

def test_mastery_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/competency-mastery/", "Créer une maîtrise de compétence")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "competence_id": 1,
        "mastery_level": 7,
        "confidence": 8,
        "last_practice_date": datetime.now().isoformat(),
        "nb_success": 5,
        "nb_failures": 2,
        "streak_correct": 3
    }
    
    tester.log_request("POST", f"{BASE_URL}/competency-mastery/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/competency-mastery/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.created_ids['competence'] = 1
            tester.mark_success("Maîtrise de compétence créée")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_mastery_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/competency-mastery/learner/{learner_id}", "Lister les compétences maîtrisées")
    
    tester.log_request("GET", f"{BASE_URL}/competency-mastery/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/competency-mastery/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} compétences")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_mastery_read():
    if 'learner' not in tester.created_ids or 'competence' not in tester.created_ids:
        tester.write("⚠️  Données manquantes, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    competence_id = tester.created_ids['competence']
    tester.test_header("GET", f"/competency-mastery/{learner_id}/{competence_id}", 
                      "Récupérer une compétence spécifique")
    
    tester.log_request("GET", f"{BASE_URL}/competency-mastery/{learner_id}/{competence_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/competency-mastery/{learner_id}/{competence_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Compétence récupérée")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS GOALS
# =============================================================================

def test_goals_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/goals/", "Créer un objectif d'apprentissage")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "type_objectif": "Maîtriser le diagnostic différentiel",
        "domaine_cible": "Cardiologie",
        "date_limite": "2026-06-30T00:00:00",
        "statut": "En cours"
    }
    
    tester.log_request("POST", f"{BASE_URL}/goals/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/goals/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['goal'] = result['id']
            tester.mark_success(f"Objectif créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_goals_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/goals/learner/{learner_id}", "Lister les objectifs d'un apprenant")
    
    tester.log_request("GET", f"{BASE_URL}/goals/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/goals/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} objectifs")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS MISCONCEPTIONS
# =============================================================================

def test_misconceptions_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/misconceptions/", "Créer une erreur conceptuelle")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "type_erreur": "Confusion entre insuffisance cardiaque et infarctus",
        "frequence_apparition": 3,
        "resistance_correction": 2,
        "detected_at": datetime.now().isoformat()
    }
    
    tester.log_request("POST", f"{BASE_URL}/misconceptions/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/misconceptions/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['misconception'] = result['id']
            tester.mark_success(f"Erreur conceptuelle créée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_misconceptions_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/misconceptions/learner/{learner_id}", 
                      "Lister les erreurs conceptuelles")
    
    tester.log_request("GET", f"{BASE_URL}/misconceptions/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/misconceptions/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} erreurs")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS PREFERENCES
# =============================================================================

def test_preferences_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/preferences/", "Créer une préférence")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "cle": "theme",
        "valeur": "dark"
    }
    
    tester.log_request("POST", f"{BASE_URL}/preferences/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/preferences/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['preference'] = result['id']
            tester.mark_success(f"Préférence créée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_preferences_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/preferences/learner/{learner_id}", "Lister les préférences")
    
    tester.log_request("GET", f"{BASE_URL}/preferences/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/preferences/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} préférences")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS STRATEGIES
# =============================================================================

def test_strategies_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/strategies/", "Créer une stratégie d'apprentissage")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "strategy_name": "Répétition espacée",
        "frequency": 8,
        "effectiveness": 9
    }
    
    tester.log_request("POST", f"{BASE_URL}/strategies/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/strategies/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['strategy'] = result['id']
            tester.mark_success(f"Stratégie créée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_strategies_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/strategies/learner/{learner_id}", "Lister les stratégies")
    
    tester.log_request("GET", f"{BASE_URL}/strategies/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/strategies/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} stratégies")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS ACHIEVEMENTS
# =============================================================================

def test_achievements_create():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/achievements/", "Créer un achievement/badge")
    
    data = {
        "learner_id": tester.created_ids['learner'],
        "badge_id": "first_diagnosis",
        "date_obtention": datetime.now().isoformat()
    }
    
    tester.log_request("POST", f"{BASE_URL}/achievements/", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/achievements/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            tester.created_ids['achievement'] = result['id']
            tester.mark_success(f"Achievement créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_achievements_list():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("GET", f"/achievements/learner/{learner_id}", "Lister les achievements")
    
    tester.log_request("GET", f"{BASE_URL}/achievements/learner/{learner_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/achievements/learner/{learner_id}", timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} achievements")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS AUTH
# =============================================================================

def test_auth_login():
    tester.test_header("POST", "/learner/auth/login", "Connexion d'un apprenant")
    
    # Utiliser un apprenant existant de la liste
    data = {
        "email": "marie.tchuente@univ-test.cm",
        "matricule": "MED-2025-0042"
    }
    
    tester.log_request("POST", f"{BASE_URL}/learner/auth/login", data=data)
    
    try:
        response = requests.post(f"{BASE_URL}/learner/auth/login", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            result = response.json()
            if 'access_token' in result:
                tester.created_ids['access_token'] = result['access_token']
                tester.mark_success("Connexion réussie, token obtenu")
                return True
            else:
                tester.mark_failure("Pas de token dans la réponse")
                return False
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_auth_me():
    if 'access_token' not in tester.created_ids:
        tester.write("⚠️  Pas de token, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("GET", "/learner/auth/me", "Récupérer profil utilisateur authentifié")
    
    headers = {"Authorization": f"Bearer {tester.created_ids['access_token']}"}
    tester.log_request("GET", f"{BASE_URL}/learner/auth/me")
    
    try:
        response = requests.get(f"{BASE_URL}/learner/auth/me", headers=headers, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Profil utilisateur récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS LEARNER TRACE
# =============================================================================

def test_traces_get():
    tester.test_header("GET", "/learner/traces", "Récupérer les traces d'apprentissage")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{BASE_URL}/learner/traces", params=params)
    
    try:
        response = requests.get(f"{BASE_URL}/learner/traces", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            if 'learners' in data:
                tester.mark_success(f"Traces récupérées: {len(data['learners'])} apprenants")
                return True
            else:
                tester.mark_success("Traces récupérées")
                return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_traces_update():
    if 'learner' not in tester.created_ids:
        tester.write("⚠️  Aucun apprenant créé, test ignoré", Colors.YELLOW)
        return False
    
    learner_id = tester.created_ids['learner']
    tester.test_header("PATCH", f"/learner/traces/{learner_id}", "Mettre à jour les traces")
    
    data = {
        "identification": {
            "matricule": f"TEST_{int(time.time())}",
            "nom": "Étudiant Test API Updated",
            "email": f"test_{int(time.time())}@example.com",
            "niveau_etudes": "M2",
            "specialite_visee": "Médecine Générale",
            "langue_preferee": "Français"
        },
        "cognitive_profile": {
            "vitesse_assimilation": 8,
            "capacite_memoire_travail": 7,
            "tendance_impulsivite": 2,
            "prefer_visual": True
        }
    }
    
    tester.log_request("PATCH", f"{BASE_URL}/learner/traces/{learner_id}", data=data)
    
    try:
        response = requests.patch(f"{BASE_URL}/learner/traces/{learner_id}", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Traces mises à jour")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# NETTOYAGE
# =============================================================================

def cleanup_test_data():
    """Supprime les données de test créées"""
    tester.section("NETTOYAGE DES DONNÉES DE TEST")
    
    cleanup_order = [
        ('achievement', 'achievements', 'Achievement'),
        ('strategy', 'strategies', 'Stratégie'),
        ('preference', 'preferences', 'Préférence'),
        ('misconception', 'misconceptions', 'Erreur conceptuelle'),
        ('goal', 'goals', 'Objectif'),
        # Note: cognitive profile se supprime automatiquement avec learner
        # Note: affective states restent pour historique
    ]
    
    for key, endpoint, name in cleanup_order:
        if key in tester.created_ids:
            item_id = tester.created_ids[key]
            tester.write(f"\n🗑️  Suppression {name} ID {item_id}...", Colors.YELLOW)
            
            try:
                response = requests.delete(f"{BASE_URL}/{endpoint}/{item_id}", timeout=30)
                if response.status_code == 200:
                    tester.write(f"✅ {name} supprimé", Colors.GREEN)
                else:
                    tester.write(f"⚠️  Erreur {response.status_code}", Colors.YELLOW)
            except Exception as e:
                tester.write(f"❌ Exception: {str(e)}", Colors.RED)

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    global tester
    tester = APITester(OUTPUT_FILE)
    
    tester.section("TEST SYSTÉMATIQUE COMPLET DE L'API APPRENANT STI")
    tester.write(f"URL: {BASE_URL}")
    tester.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tester.write(f"Fichier de sortie: {OUTPUT_FILE}")
    
    print(f"\n{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗")
    print(f"║  TEST AUTOMATIQUE API MODULE APPRENANT                        ║")
    print(f"║  Chaque test s'exécutera et attendra votre validation        ║")
    print(f"╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")
    
    try:
        # =====================================================================
        # MODULE 1: LEARNERS (3 tests)
        # =====================================================================
        tester.section("MODULE 1: LEARNERS - Gestion des apprenants")
        
        test_learners_create()
        tester.wait_for_user()
        
        test_learners_list()
        tester.wait_for_user()
        
        test_learners_read()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 2: COGNITIVE PROFILE (3 tests)
        # =====================================================================
        tester.section("MODULE 2: COGNITIVE PROFILE - Profil cognitif")
        
        test_cognitive_create()
        tester.wait_for_user()
        
        test_cognitive_read()
        tester.wait_for_user()
        
        test_cognitive_update()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 3: AFFECTIVE STATE (4 tests)
        # =====================================================================
        tester.section("MODULE 3: AFFECTIVE STATE - État affectif")
        
        test_affective_create()
        tester.wait_for_user()
        
        test_affective_read_session()
        tester.wait_for_user()
        
        test_affective_latest()
        tester.wait_for_user()
        
        test_affective_history()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 4: COMPETENCY MASTERY (3 tests)
        # =====================================================================
        tester.section("MODULE 4: COMPETENCY MASTERY - Maîtrise des compétences")
        
        test_mastery_create()
        tester.wait_for_user()
        
        test_mastery_list()
        tester.wait_for_user()
        
        test_mastery_read()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 5: GOALS (2 tests)
        # =====================================================================
        tester.section("MODULE 5: GOALS - Objectifs d'apprentissage")
        
        test_goals_create()
        tester.wait_for_user()
        
        test_goals_list()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 6: MISCONCEPTIONS (2 tests)
        # =====================================================================
        tester.section("MODULE 6: MISCONCEPTIONS - Erreurs conceptuelles")
        
        test_misconceptions_create()
        tester.wait_for_user()
        
        test_misconceptions_list()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 7: PREFERENCES (2 tests)
        # =====================================================================
        tester.section("MODULE 7: PREFERENCES - Préférences utilisateur")
        
        test_preferences_create()
        tester.wait_for_user()
        
        test_preferences_list()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 8: STRATEGIES (2 tests)
        # =====================================================================
        tester.section("MODULE 8: STRATEGIES - Stratégies d'apprentissage")
        
        test_strategies_create()
        tester.wait_for_user()
        
        test_strategies_list()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 9: ACHIEVEMENTS (2 tests)
        # =====================================================================
        tester.section("MODULE 9: ACHIEVEMENTS - Badges et récompenses")
        
        test_achievements_create()
        tester.wait_for_user()
        
        test_achievements_list()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 10: AUTH (2 tests)
        # =====================================================================
        tester.section("MODULE 10: AUTH - Authentification")
        
        test_auth_login()
        tester.wait_for_user()
        
        test_auth_me()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 11: LEARNER TRACE (2 tests)
        # =====================================================================
        tester.section("MODULE 11: LEARNER TRACE - Traces d'apprentissage")
        
        test_traces_get()
        tester.wait_for_user()
        
        test_traces_update()
        tester.wait_for_user()
        
        # =====================================================================
        # RÉSUMÉ FINAL
        # =====================================================================
        tester.summary()
        
        # =====================================================================
        # NETTOYAGE OPTIONNEL
        # =====================================================================
        print(f"\n{Colors.YELLOW}╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  NETTOYAGE DES DONNÉES DE TEST                                ║")
        print(f"╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")
        print(f"{Colors.YELLOW}Voulez-vous supprimer les données de test créées? (o/n): {Colors.END}", end='')
        
        if input().lower() == 'o':
            cleanup_test_data()
        else:
            tester.write("\n⚠️  Données de test conservées", Colors.YELLOW)
            tester.write("IDs conservés pour référence future:")
            for key, value in tester.created_ids.items():
                tester.write(f"   - {key}: {value}")
        
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
        print(f"\n{Colors.GREEN}╔═══════════════════════════════════════════════════════════════╗")
        print(f"║  TESTS TERMINÉS                                               ║")
        print(f"║  Résultats sauvegardés dans: {OUTPUT_FILE:31s} ║")
        print(f"╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")


# =====================================================================
# POINT D'ENTRÉE
# =====================================================================

if __name__ == "__main__":
    main()
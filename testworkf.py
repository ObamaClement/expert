import requests
import json
from datetime import datetime
import time
import sys

# ==============================================================================
# CONFIGURATION HYBRIDE
# ==============================================================================
# URL pour la gestion des apprenants (Stable / Déployé)
LEARNER_BASE_URL = "https://appren-docker.onrender.com/api/v1"

# URL pour la simulation et le tuteur (En cours de dev / Local)
SIMULATION_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Fichier de log
OUTPUT_FILE = f"test_hybrid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Catégorie cible
TARGET_CATEGORY = "Infectiologie"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

class WorkflowTester:
    def __init__(self, filename):
        self.file = open(filename, 'w', encoding='utf-8')
        self.learner_id = None
        self.step_count = 0
        
    def log(self, message, color=None, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        self.file.write(formatted_msg + '\n')
        self.file.flush()
        
        if color:
            print(f"{color}{formatted_msg}{Colors.END}")
        else:
            print(formatted_msg)

    def fail(self, message):
        self.log(f"❌ {message}", Colors.RED, "FAIL")
        return False

    def success(self, message):
        self.log(f"✅ {message}", Colors.GREEN, "SUCCESS")
        return True

tester = WorkflowTester(OUTPUT_FILE)

def step_1_create_learner_remote():
    """Crée l'apprenant sur le serveur Render."""
    tester.step_count += 1
    tester.log(f"\n--- ÉTAPE {tester.step_count}: CRÉATION APPRENANT (DISTANT) ---", Colors.CYAN)
    tester.log(f"Cible: {LEARNER_BASE_URL}")
    
    unique_id = int(time.time())
    data = {
        "matricule": f"HYBRID_TEST_{unique_id}",
        "nom": f"Hybrid Tester {unique_id}",
        "email": f"hybrid_{unique_id}@test.com",
        "niveau_etudes": "Interne",
        "specialite_visee": "Médecine Générale",
        "langue_preferee": "fr"
    }
    
    try:
        response = requests.post(f"{LEARNER_BASE_URL}/learners/", json=data, timeout=30)
        
        if response.status_code == 201:
            res = response.json()
            tester.learner_id = res['id']
            return tester.success(f"Apprenant créé sur Render avec ID: {tester.learner_id}")
        else:
            return tester.fail(f"Erreur création Render ({response.status_code}): {response.text}")
            
    except Exception as e:
        return tester.fail(f"Exception connexion Render: {str(e)}")

def step_run_session_local(expected_type=None, session_label=""):
    """Exécute une session complète sur le serveur Local."""
    tester.step_count += 1
    tester.log(f"\n--- ÉTAPE {tester.step_count}: SESSION {session_label} (LOCAL) ---", Colors.BLUE)
    
    # 1. START
    start_data = {"learner_id": tester.learner_id, "category": TARGET_CATEGORY}
    try:
        res_start = requests.post(f"{SIMULATION_BASE_URL}/simulation/sessions/start", json=start_data)
        
        if res_start.status_code not in [200, 201]:
            return tester.fail(f"Erreur Start Local ({res_start.status_code}): {res_start.text}")
        
        session = res_start.json()
        session_id = session['session_id']
        actual_type = session['session_type']
        case = session.get('clinical_case', {})
        difficulty = case.get('niveau_difficulte')
        patho_id = case.get('pathologie_principale', {}).get('id')
        
        tester.log(f"   Session ID: {session_id}")
        tester.log(f"   Type: {actual_type}")
        tester.log(f"   Niveau: {difficulty}/30")
        
        if expected_type and actual_type != expected_type:
            tester.log(f"⚠️ TYPE INATTENDU: Attendu '{expected_type}', Reçu '{actual_type}'", Colors.YELLOW)
        
        # 2. CHAT (Simulé pour activer le système)
        requests.post(f"{SIMULATION_BASE_URL}/chat/sessions/{session_id}/messages", json={
            "sender": "Apprenant", "content": "Je commence l'examen."
        })
        
        # 3. ACTION (Simulé pour loguer une activité)
        requests.post(f"{SIMULATION_BASE_URL}/simulation/sessions/{session_id}/actions", json={
            "action_type": "examen", "action_name": "NFS", "justification": "Test"
        })

        # 4. SUBMIT (Forcer la réussite)
        # On soumet le bon ID de pathologie pour garantir une bonne note
        submit_data = {
            "diagnosed_pathology_id": patho_id,
            "prescribed_medication_ids": [] # Liste vide ok pour le test
        }
        
        time.sleep(1) # Petite pause
        
        res_submit = requests.post(f"{SIMULATION_BASE_URL}/simulation/sessions/{session_id}/submit", json=submit_data)
        
        if res_submit.status_code == 200:
            eval_data = res_submit.json()
            score = eval_data['evaluation']['score_total']
            
            # Afficher résultat
            color = Colors.GREEN if score >= 12 else Colors.RED
            tester.log(f"   Note finale: {score}/20", color)
            
            return {
                "success": True,
                "score": score,
                "difficulty": difficulty,
                "type": actual_type
            }
        else:
            return tester.fail(f"Erreur Submit Local ({res_submit.status_code}): {res_submit.text}")

    except Exception as e:
        return tester.fail(f"Exception locale: {str(e)}")

def main():
    tester.log("🚀 DÉMARRAGE DU TEST HYBRIDE (RENDER + LOCAL)", Colors.MAGENTA)
    tester.log("====================================================")
    
    # 1. Création Apprenant (Render)
    if not step_1_create_learner_remote():
        tester.log("❌ Arrêt du test : Impossible de créer l'apprenant.", Colors.RED)
        return

    # 2. Session Test Positionnement (Local)
    res_test = step_run_session_local(expected_type="test", session_label="Test Positionnement")
    if not res_test or not res_test['success']: return
    
    initial_level = res_test['difficulty']
    tester.log(f"🏁 NIVEAU INITIAL: {initial_level}", Colors.YELLOW)
    
    # 3. Cycle Formatif (3 Sessions) (Local)
    for i in range(1, 4):
        res = step_run_session_local(expected_type="formative", session_label=f"Formative #{i}")
        if not res or not res['success']: return
        time.sleep(1)

    # 4. Session Sommative (Local)
    res_exam = step_run_session_local(expected_type="sommative", session_label="EXAMEN SOMMATIF")
    if not res_exam or not res_exam['success']: return
    
    exam_score = res_exam['score']
    
    # 5. Vérification Progression (Local)
    tester.log("\n--- VÉRIFICATION DE LA PROGRESSION ---", Colors.CYAN)
    
    res_check = step_run_session_local(expected_type="formative", session_label="Post-Examen")
    if not res_check or not res_check['success']: return
    
    new_level = res_check['difficulty']
    
    tester.log(f"\n📊 BILAN:", Colors.MAGENTA)
    tester.log(f"   Niveau Avant: {initial_level}")
    tester.log(f"   Note Examen:  {exam_score}/20")
    tester.log(f"   Niveau Après: {new_level}")
    
    if exam_score >= 12:
        if new_level > initial_level:
            tester.success("🎉 PROGRESSION VALIDÉE : Le niveau a augmenté après réussite !")
        else:
            tester.fail("⛔ BUG : Note suffisante mais le niveau n'a pas augmenté.")
    else:
        if new_level <= initial_level:
            tester.success("🛡️ SÉCURITÉ VALIDÉE : Note insuffisante, pas de progression (ou maintien).")
        else:
            tester.fail("⛔ BUG : Le niveau a augmenté malgré une note insuffisante.")

if __name__ == "__main__":
    main()
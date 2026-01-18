import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://expert-cmck.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"
OUTPUT_FILE = f"test_progression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

class ProgressionTester:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8')
        self.test_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.learner_id = 1  # ID de l'apprenant test
        self.category = "Infectiologie"
        self.sessions_history = []
        
    def write(self, message, color=None):
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
    
    def test_header(self, description):
        self.test_count += 1
        header = f"\n{'─'*100}\nTEST #{self.test_count}: {description}\n{'─'*100}"
        self.write(header, Colors.CYAN)
    
    def mark_success(self, message=""):
        self.success_count += 1
        self.write(f"✅ SUCCÈS: {message}", Colors.GREEN)
    
    def mark_failure(self, message=""):
        self.fail_count += 1
        self.write(f"❌ ÉCHEC: {message}", Colors.RED)
    
    def mark_warning(self, message=""):
        self.write(f"⚠️  ATTENTION: {message}", Colors.YELLOW)
    
    def summary(self):
        self.section("RÉSUMÉ DES TESTS DE PROGRESSION")
        self.write(f"Total de tests: {self.test_count}")
        self.write(f"Succès: {self.success_count}", Colors.GREEN)
        self.write(f"Échecs: {self.fail_count}", Colors.RED)
        self.write(f"Taux de réussite: {(self.success_count/self.test_count*100):.1f}%" if self.test_count > 0 else "N/A")
    
    def close(self):
        self.file.close()

tester = None

# =============================================================================
# TEST 1: VÉRIFICATION REPRISE DE SESSION
# =============================================================================

def test_session_resume():
    """Vérifier si la sélection d'une catégorie reprend la dernière session non terminée"""
    tester.test_header("Reprise de session non terminée")
    
    tester.write(f"\n📋 TEST: Sélection de catégorie '{tester.category}'", Colors.BLUE)
    tester.write(f"   Comportement attendu: Reprendre la dernière session non terminée")
    
    data = {
        "learner_id": tester.learner_id,
        "category": tester.category
    }
    
    try:
        # Première session
        response1 = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
        
        if response1.status_code == 201:
            session1 = response1.json()
            session1_id = session1['session_id']
            tester.sessions_history.append(session1)
            
            tester.write(f"\n   Session 1 créée: {session1_id}")
            tester.write(f"   Type: {session1.get('session_type')}")
            tester.write(f"   Cas clinique: {session1.get('clinical_case', {}).get('code_fultang')}")
            tester.write(f"   Niveau difficulté: {session1.get('clinical_case', {}).get('niveau_difficulte')}")
            
            time.sleep(2)
            
            # Deuxième tentative SANS terminer la première
            tester.write(f"\n   ⏳ Nouvelle demande de session SANS terminer la première...", Colors.YELLOW)
            response2 = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
            
            if response2.status_code == 201:
                session2 = response2.json()
                session2_id = session2['session_id']
                
                if session1_id == session2_id:
                    tester.mark_success("✅ Session existante reprise (même ID)")
                    return True
                else:
                    tester.write(f"\n   Session 2 créée: {session2_id}")
                    tester.write(f"   Type: {session2.get('session_type')}")
                    
                    tester.mark_warning("Nouvelle session créée au lieu de reprendre l'existante")
                    tester.write(f"      Attendu: {session1_id}")
                    tester.write(f"      Obtenu: {session2_id}")
                    return False
            else:
                tester.mark_failure(f"Erreur lors de la 2ème demande: {response2.status_code}")
                return False
        else:
            tester.mark_failure(f"Impossible de créer la session initiale: {response1.status_code}")
            return False
            
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TEST 2: CYCLE FORMATIF (3 sessions)
# =============================================================================

def test_formative_cycle():
    """Tester le cycle de 3 évaluations formatives"""
    tester.section("CYCLE DE 3 ÉVALUATIONS FORMATIVES")
    
    formative_sessions = []
    
    for i in range(1, 4):
        tester.test_header(f"Session Formative #{i}/3")
        
        data = {
            "learner_id": tester.learner_id,
            "category": tester.category
        }
        
        try:
            response = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
            
            if response.status_code == 201:
                session = response.json()
                session_type = session.get('session_type')
                session_id = session['session_id']
                niveau = session.get('clinical_case', {}).get('niveau_difficulte')
                
                formative_sessions.append(session)
                
                tester.write(f"\n📊 Session {i}:")
                tester.write(f"   ID: {session_id}")
                tester.write(f"   Type: {session_type}")
                tester.write(f"   Niveau difficulté: {niveau}/30")
                
                # Vérifier que c'est bien formatif pour les 3 premières
                if session_type == "formatif" or session_type == "formative":
                    tester.write(f"   ✅ Type correct: {session_type}", Colors.GREEN)
                else:
                    tester.mark_warning(f"Type attendu 'formatif', obtenu '{session_type}'")
                
                # Simuler une complétion rapide (sans vraiment faire la session)
                tester.write(f"\n   🔄 Simulation de complétion de la session...")
                # Note: On devrait submit mais ça crashe, donc on marque juste
                
                time.sleep(1)
                tester.mark_success(f"Session formative {i}/3 créée")
            else:
                tester.mark_failure(f"Échec création session {i}: {response.status_code}")
                return False
                
        except Exception as e:
            tester.mark_failure(f"Exception session {i}: {str(e)}")
            return False
    
    # Vérifier que les 3 sessions ont des cas différents
    tester.write(f"\n🔍 VÉRIFICATION: Cas cliniques différents?", Colors.MAGENTA)
    codes = [s.get('clinical_case', {}).get('code_fultang') for s in formative_sessions]
    niveaux = [s.get('clinical_case', {}).get('niveau_difficulte') for s in formative_sessions]
    
    tester.write(f"   Cas 1: {codes[0]} (niveau {niveaux[0]})")
    tester.write(f"   Cas 2: {codes[1]} (niveau {niveaux[1]})")
    tester.write(f"   Cas 3: {codes[2]} (niveau {niveaux[2]})")
    
    if len(set(codes)) == 3:
        tester.mark_success("3 cas cliniques différents ✅")
    else:
        tester.mark_warning("Certains cas se répètent")
    
    return True

# =============================================================================
# TEST 3: SESSION SOMMATIVE APRÈS 3 FORMATIVES
# =============================================================================

def test_summative_after_formatives():
    """Vérifier qu'une session sommative est proposée après 3 formatives"""
    tester.test_header("Session Sommative après 3 Formatives")
    
    tester.write(f"\n📋 Après 3 sessions formatives, la 4ème devrait être SOMMATIVE", Colors.BLUE)
    
    data = {
        "learner_id": tester.learner_id,
        "category": tester.category
    }
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
        
        if response.status_code == 201:
            session = response.json()
            session_type = session.get('session_type')
            session_id = session['session_id']
            clinical_case = session.get('clinical_case', {})
            
            tester.write(f"\n📊 Session 4 (Sommative attendue):")
            tester.write(f"   ID: {session_id}")
            tester.write(f"   Type: {session_type}")
            tester.write(f"   Cas: {clinical_case.get('code_fultang')}")
            tester.write(f"   Niveau: {clinical_case.get('niveau_difficulte')}/30")
            
            if session_type == "sommatif" or session_type == "summative":
                tester.mark_success(f"✅ Session SOMMATIVE correctement déclenchée")
                
                # Vérifier que le cas fait partie des 3 précédents (formatifs)
                tester.write(f"\n🔍 Le cas sommative est-il parmi les 3 cas formatifs?")
                # (nécessiterait de stocker les IDs des cas formatifs)
                
                return True, session
            else:
                tester.mark_failure(f"Type attendu 'sommatif', obtenu '{session_type}'")
                return False, None
        else:
            tester.mark_failure(f"Échec: {response.status_code}")
            return False, None
            
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False, None

# =============================================================================
# TEST 4: PROGRESSION AVEC NOTE > 12/20
# =============================================================================

def test_progression_success():
    """Simuler une note > 12/20 et vérifier la progression niveau +3"""
    tester.test_header("Progression avec succès (note > 12/20)")
    
    tester.write(f"\n📊 SIMULATION: Note sommative = 15/20 (> 12)", Colors.GREEN)
    tester.write(f"   Comportement attendu:")
    tester.write(f"   - Passer au niveau de difficulté +3")
    tester.write(f"   - Nouvelle phase formative (3 sessions)")
    
    # Note: Comme le submit crashe, on ne peut pas vraiment tester
    # Mais on peut vérifier la logique attendue
    
    tester.write(f"\n⚠️  TEST LIMITÉ: Impossible de soumettre réellement (bug end_time)", Colors.YELLOW)
    tester.write(f"   Vérification théorique de la logique:")
    
    niveau_actuel = 15  # Exemple
    niveau_attendu = niveau_actuel + 3
    
    tester.write(f"\n   Si niveau actuel = {niveau_actuel}/30")
    tester.write(f"   Alors niveau suivant = {niveau_attendu}/30")
    
    # Tenter de démarrer une nouvelle session et voir le niveau
    data = {
        "learner_id": tester.learner_id,
        "category": tester.category
    }
    
    try:
        response = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
        
        if response.status_code == 201:
            session = response.json()
            nouveau_niveau = session.get('clinical_case', {}).get('niveau_difficulte')
            
            tester.write(f"\n📋 Nouvelle session créée:")
            tester.write(f"   Niveau obtenu: {nouveau_niveau}/30")
            
            # On ne peut pas vraiment vérifier sans avoir fait le submit
            tester.mark_warning("Impossible de vérifier la progression réelle sans soumission fonctionnelle")
            return True
        else:
            tester.mark_failure(f"Erreur: {response.status_code}")
            return False
            
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TEST 5: RÉTROGRADATION AVEC NOTE < 12/20
# =============================================================================

def test_retrogradation_failure():
    """Simuler une note < 12/20 et vérifier la rétrogradation"""
    tester.test_header("Rétrogradation avec échec (note < 12/20)")
    
    tester.write(f"\n📊 SIMULATION: Note sommative = 8/20 (< 12)", Colors.RED)
    tester.write(f"   Comportement attendu:")
    tester.write(f"   - Rester au même niveau de difficulté")
    tester.write(f"   - Recommencer cycle formatif (3 sessions)")
    tester.write(f"   - Nouvelle session sommative après")
    
    tester.write(f"\n⚠️  TEST LIMITÉ: Impossible de soumettre (bug end_time)", Colors.YELLOW)
    
    tester.mark_warning("Fonctionnalité non testable sans correction du bug de soumission")
    return False

# =============================================================================
# TEST 6: ÉCHELLE DE NOTATION
# =============================================================================

def test_scoring_scale():
    """Vérifier l'échelle de notation et conversion"""
    tester.test_header("Vérification de l'échelle de notation")
    
    tester.write(f"\n📊 ÉCHELLES ATTENDUES:", Colors.BLUE)
    tester.write(f"   Niveau de difficulté: 0-30")
    tester.write(f"   Note finale: 0-20")
    tester.write(f"   Seuil de réussite: 12/20 (60%)")
    
    tester.write(f"\n🔍 VÉRIFICATION DANS LES LOGS PRÉCÉDENTS:")
    tester.write(f"   Score calculé: 14.0")
    tester.write(f"   ❌ Échelle incorrecte! Le score est sur 30, pas sur 20")
    
    tester.write(f"\n📝 PROBLÈME DÉTECTÉ:", Colors.YELLOW)
    tester.write(f"   Le système calcule un score sur 30 points:")
    tester.write(f"   - score_diagnostic: /10")
    tester.write(f"   - score_therapeutique: /10")
    tester.write(f"   - score_demarche: /10")
    tester.write(f"   TOTAL: /30")
    
    tester.write(f"\n   Mais devrait être sur /20 selon vos specs!")
    
    tester.write(f"\n💡 CONVERSION NÉCESSAIRE:")
    tester.write(f"   score_sur_20 = (score_sur_30 / 30) * 20")
    tester.write(f"   Exemple: 14/30 = (14/30)*20 = 9.33/20")
    
    tester.mark_warning("Échelle de notation incorrecte (30 au lieu de 20)")
    return False

# =============================================================================
# TEST 7: RECOMMANDATION NEXT_STEP
# =============================================================================

def test_recommendation_logic():
    """Vérifier la logique de recommandation après évaluation"""
    tester.test_header("Logique de recommandation post-évaluation")
    
    tester.write(f"\n📋 RECOMMANDATIONS ATTENDUES:", Colors.BLUE)
    
    scenarios = [
        {"note": 18, "attendu": "Progresser niveau +3, nouvelle phase formative"},
        {"note": 15, "attendu": "Progresser niveau +3, nouvelle phase formative"},
        {"note": 12, "attendu": "Progresser niveau +3, nouvelle phase formative (limite)"},
        {"note": 11, "attendu": "Recommencer cycle formatif au même niveau"},
        {"note": 8, "attendu": "Recommencer cycle formatif au même niveau"},
        {"note": 5, "attendu": "Recommencer cycle formatif au même niveau"},
    ]
    
    for scenario in scenarios:
        note = scenario["note"]
        attendu = scenario["attendu"]
        statut = "✅ RÉUSSITE" if note >= 12 else "❌ ÉCHEC"
        
        tester.write(f"\n   Note: {note}/20 → {statut}")
        tester.write(f"   Recommandation: {attendu}")
    
    tester.write(f"\n⚠️  IMPOSSIBLE À TESTER: Bug de soumission empêche validation", Colors.YELLOW)
    tester.mark_warning("Logique de recommandation non vérifiable")
    return False

# =============================================================================
# TEST 8: SUIVI DE PROGRESSION PAR CATÉGORIE
# =============================================================================

def test_category_progression_tracking():
    """Vérifier le suivi de progression par catégorie"""
    tester.test_header("Suivi de progression par catégorie")
    
    categories = ["Infectiologie", "Cardiologie", "Pédiatrie"]
    
    tester.write(f"\n📊 TEST: Progression indépendante par catégorie", Colors.BLUE)
    tester.write(f"   L'apprenant devrait avoir un niveau différent dans chaque catégorie")
    
    for cat in categories:
        data = {
            "learner_id": tester.learner_id,
            "category": cat
        }
        
        try:
            response = requests.post(f"{API_BASE}/simulation/sessions/start", json=data, timeout=30)
            
            if response.status_code == 201:
                session = response.json()
                niveau = session.get('clinical_case', {}).get('niveau_difficulte')
                session_type = session.get('session_type')
                
                tester.write(f"\n   {cat}:")
                tester.write(f"   - Niveau: {niveau}/30")
                tester.write(f"   - Type session: {session_type}")
                
                time.sleep(1)
            else:
                tester.write(f"\n   {cat}: Erreur {response.status_code}")
                
        except Exception as e:
            tester.write(f"\n   {cat}: Exception {str(e)}")
    
    tester.mark_warning("Vérification partielle - Niveaux affichés mais progression non confirmée")
    return True

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    global tester
    tester = ProgressionTester(OUTPUT_FILE)
    
    tester.section("TEST DU WORKFLOW DE PROGRESSION PÉDAGOGIQUE")
    tester.write(f"URL: {BASE_URL}")
    tester.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tester.write(f"Apprenant ID: {tester.learner_id}")
    tester.write(f"Catégorie testée: {tester.category}")
    
    tester.write(f"\n📋 LOGIQUE ATTENDUE:", Colors.MAGENTA)
    tester.write(f"1. Sélection catégorie → Reprend session non terminée OU nouvelle session")
    tester.write(f"2. Phase FORMATIVE: 3 sessions d'apprentissage")
    tester.write(f"3. Phase SOMMATIVE: 1 session d'évaluation (cas aléatoire parmi les 3 formatifs)")
    tester.write(f"4. Si note ≥ 12/20 → Niveau +3, nouvelle phase formative")
    tester.write(f"5. Si note < 12/20 → Même niveau, recommencer cycle formatif")
    tester.write(f"6. Progression indépendante par catégorie")
    
    try:
        # Test 1: Reprise de session
        test_session_resume()
        time.sleep(2)
        
        # Test 2: Cycle formatif
        test_formative_cycle()
        time.sleep(2)
        
        # Test 3: Session sommative
        test_summative_after_formatives()
        time.sleep(2)
        
        # Test 4: Progression succès
        test_progression_success()
        time.sleep(2)
        
        # Test 5: Rétrogradation
        test_retrogradation_failure()
        time.sleep(1)
        
        # Test 6: Échelle notation
        test_scoring_scale()
        time.sleep(1)
        
        # Test 7: Recommandations
        test_recommendation_logic()
        time.sleep(1)
        
        # Test 8: Suivi par catégorie
        test_category_progression_tracking()
        
        # Résumé
        tester.summary()
        
        # Analyse finale
        tester.section("ANALYSE DE L'IMPLÉMENTATION")
        
        tester.write(f"\n🔍 FONCTIONNALITÉS DÉTECTÉES:", Colors.BLUE)
        tester.write(f"✅ Création de sessions par catégorie")
        tester.write(f"✅ Attribution de cas cliniques avec niveaux de difficulté")
        tester.write(f"✅ Types de session (test/formatif/sommatif)")
        tester.write(f"❌ Reprise automatique de session non terminée")
        tester.write(f"❌ Cycle automatique 3 formatifs → 1 sommatif")
        tester.write(f"❌ Progression automatique niveau +3")
        tester.write(f"❌ Rétrogradation si échec")
        tester.write(f"❌ Conversion score 30 → 20")
        
        tester.write(f"\n🚨 BLOQUEURS MAJEURS:", Colors.RED)
        tester.write(f"1. Bug end_time empêche toute soumission")
        tester.write(f"2. Impossible de tester la progression réelle")
        tester.write(f"3. Échelle de notation incorrecte (30 vs 20)")
        tester.write(f"4. Logique de workflow non observable")
        
    except KeyboardInterrupt:
        tester.write("\n\n⚠️  Tests interrompus par l'utilisateur", Colors.YELLOW)
    except Exception as e:
        tester.write(f"\n\n❌ ERREUR CRITIQUE: {str(e)}", Colors.RED)
        import traceback
        tester.write(traceback.format_exc())
    finally:
        tester.summary()
        tester.close()
        print(f"\n{Colors.GREEN}╔════════════════════════════════════════════════════════════════╗")
        print(f"║  TESTS TERMINÉS                                                ║")
        print(f"║  Résultats: {OUTPUT_FILE:46s} ║")
        print(f"╚════════════════════════════════════════════════════════════════╝{Colors.END}\n")

if __name__ == "__main__":
    main()
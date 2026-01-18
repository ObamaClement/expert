import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://expert-cmck.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"
OUTPUT_FILE = f"test_api_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

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
# TESTS SYMPTOMS
# =============================================================================

def test_symptoms_create():
    tester.test_header("POST", "/api/v1/symptoms/", "Créer un nouveau symptôme")
    
    data = {
        "nom": "Céphalée Test API",
        "nom_local": "Mal de tête (Ewondo)",
        "categorie": "Neurologique",
        "type_symptome": "Subjectif",
        "description": "Douleur au niveau de la tête",
        "questions_anamnese": {
            "localisation": "Où se situe la douleur ?",
            "intensite": "Sur une échelle de 1 à 10 ?",
            "caractere": "Pulsatile, constrictive ?"
        },
        "signes_alarme": True
    }
    
    tester.log_request("POST", f"{API_BASE}/symptoms/", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/symptoms/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['symptom'] = result['id']
            tester.mark_success(f"Symptôme créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_symptoms_list():
    tester.test_header("GET", "/api/v1/symptoms/", "Récupérer la liste des symptômes")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{API_BASE}/symptoms/", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/symptoms/", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} symptômes")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_symptoms_read():
    if 'symptom' not in tester.created_ids:
        tester.write("⚠️  Aucun symptôme créé, test ignoré", Colors.YELLOW)
        return False
    
    symptom_id = tester.created_ids['symptom']
    tester.test_header("GET", f"/api/v1/symptoms/{symptom_id}", "Récupérer un symptôme par ID")
    
    tester.log_request("GET", f"{API_BASE}/symptoms/{symptom_id}")
    
    try:
        response = requests.get(f"{API_BASE}/symptoms/{symptom_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Symptôme récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_symptoms_update():
    if 'symptom' not in tester.created_ids:
        tester.write("⚠️  Aucun symptôme créé, test ignoré", Colors.YELLOW)
        return False
    
    symptom_id = tester.created_ids['symptom']
    tester.test_header("PATCH", f"/api/v1/symptoms/{symptom_id}", "Mettre à jour un symptôme")
    
    data = {
        "description": "Description mise à jour - Douleur céphalique modérée à sévère",
        "signes_alarme": False
    }
    
    tester.log_request("PATCH", f"{API_BASE}/symptoms/{symptom_id}", data=data)
    
    try:
        response = requests.patch(f"{API_BASE}/symptoms/{symptom_id}", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Symptôme mis à jour")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS DISEASES
# =============================================================================

def test_diseases_create():
    tester.test_header("POST", "/api/v1/diseases/", "Créer une nouvelle pathologie")
    
    data = {
        "nom_fr": "Méningite Test API",
        "code_icd10": "G03.9",
        "nom_en": "Meningitis Test",
        "nom_local": "Inflammation cerveau (Bulu)",
        "categorie": "Infectiologie",
        "prevalence_cameroun": 5.2,
        "niveau_gravite": 4,
        "description": "Inflammation des méninges",
        "physiopathologie": "Infection bactérienne ou virale des méninges",
        "evolution_naturelle": "Urgence médicale nécessitant un traitement rapide",
        "complications": {
            "neurologiques": ["Séquelles neurologiques", "Décès"],
            "autres": ["Septicémie"]
        },
        "facteurs_risque": {
            "age": ["Nourrissons", "Jeunes adultes"],
            "immunitaires": ["Immunodépression"]
        },
        "prevention": "Vaccination, hygiène"
    }
    
    tester.log_request("POST", f"{API_BASE}/diseases/", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/diseases/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['disease'] = result['id']
            tester.mark_success(f"Pathologie créée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_diseases_list():
    tester.test_header("GET", "/api/v1/diseases/", "Récupérer la liste des pathologies")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{API_BASE}/diseases/", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/diseases/", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} pathologies")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_diseases_read():
    if 'disease' not in tester.created_ids:
        tester.write("⚠️  Aucune pathologie créée, test ignoré", Colors.YELLOW)
        return False
    
    disease_id = tester.created_ids['disease']
    tester.test_header("GET", f"/api/v1/diseases/{disease_id}", "Récupérer une pathologie par ID")
    
    tester.log_request("GET", f"{API_BASE}/diseases/{disease_id}")
    
    try:
        response = requests.get(f"{API_BASE}/diseases/{disease_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Pathologie récupérée")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS MEDICATIONS
# =============================================================================

def test_medications_create():
    tester.test_header("POST", "/api/v1/medications/", "Créer un nouveau médicament")
    
    data = {
        "dci": "Amoxicilline Test API",
        "nom_commercial": "Clamoxyl Test",
        "classe_therapeutique": "Antibiotique - Pénicilline",
        "forme_galenique": "Gélule",
        "dosage": "1g",
        "voie_administration": "Orale",
        "mecanisme_action": "Inhibition de la synthèse de la paroi bactérienne",
        "indications": {
            "principales": ["Infections respiratoires", "Infections ORL"]
        },
        "contre_indications": {
            "absolues": ["Allergie aux pénicillines"]
        },
        "effets_secondaires": {
            "digestifs": ["Diarrhée", "Nausées"]
        },
        "interactions_medicamenteuses": {
            "attention": ["Méthotrexate"]
        },
        "precautions_emploi": "Surveiller fonction rénale",
        "posologie_standard": {
            "adulte": "1g x 3/jour"
        },
        "disponibilite_cameroun": "Disponible",
        "cout_moyen_fcfa": 2500,
        "statut_prescription": "Sur ordonnance"
    }
    
    tester.log_request("POST", f"{API_BASE}/medications/", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/medications/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['medication'] = result['id']
            tester.mark_success(f"Médicament créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_medications_list():
    tester.test_header("GET", "/api/v1/medications/", "Récupérer la liste des médicaments")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{API_BASE}/medications/", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/medications/", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} médicaments")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_medications_read():
    if 'medication' not in tester.created_ids:
        tester.write("⚠️  Aucun médicament créé, test ignoré", Colors.YELLOW)
        return False
    
    medication_id = tester.created_ids['medication']
    tester.test_header("GET", f"/api/v1/medications/{medication_id}", "Récupérer un médicament par ID")
    
    tester.log_request("GET", f"{API_BASE}/medications/{medication_id}")
    
    try:
        response = requests.get(f"{API_BASE}/medications/{medication_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Médicament récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS RELATIONS
# =============================================================================

def test_add_symptom_to_disease():
    if 'disease' not in tester.created_ids or 'symptom' not in tester.created_ids:
        tester.write("⚠️  Pathologie ou symptôme manquant, test ignoré", Colors.YELLOW)
        return False
    
    disease_id = tester.created_ids['disease']
    tester.test_header("POST", f"/api/v1/diseases/{disease_id}/symptoms", 
                      "Associer un symptôme à une pathologie")
    
    data = {
        "pathologie_id": disease_id,
        "symptome_id": tester.created_ids['symptom'],
        "probabilite": 0.90,
        "sensibilite": 0.85,
        "specificite": 0.75,
        "phase_maladie": "Initiale",
        "frequence": "Très fréquent",
        "est_pathognomonique": False,
        "importance_diagnostique": 9
    }
    
    tester.log_request("POST", f"{API_BASE}/diseases/{disease_id}/symptoms", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/diseases/{disease_id}/symptoms", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            tester.mark_success("Symptôme associé à la pathologie")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_get_symptoms_for_disease():
    if 'disease' not in tester.created_ids:
        tester.write("⚠️  Aucune pathologie créée, test ignoré", Colors.YELLOW)
        return False
    
    disease_id = tester.created_ids['disease']
    tester.test_header("GET", f"/api/v1/diseases/{disease_id}/symptoms", 
                      "Récupérer les symptômes d'une pathologie")
    
    tester.log_request("GET", f"{API_BASE}/diseases/{disease_id}/symptoms")
    
    try:
        response = requests.get(f"{API_BASE}/diseases/{disease_id}/symptoms", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"{len(data)} symptômes trouvés")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_add_treatment_to_disease():
    if 'disease' not in tester.created_ids or 'medication' not in tester.created_ids:
        tester.write("⚠️  Pathologie ou médicament manquant, test ignoré", Colors.YELLOW)
        return False
    
    disease_id = tester.created_ids['disease']
    tester.test_header("POST", f"/api/v1/diseases/{disease_id}/treatments", 
                      "Associer un traitement à une pathologie")
    
    data = {
        "pathologie_id": disease_id,
        "medicament_id": tester.created_ids['medication'],
        "type_traitement": "Curatif",
        "ligne_traitement": 1,
        "indication_precise": "Traitement de première intention",
        "efficacite_taux": 92.5,
        "duree_traitement_jours": 10,
        "posologie_detaillee": {
            "dose": "1g x 3/jour",
            "duree": "10 jours"
        },
        "niveau_preuve": "A",
        "guidelines_source": "OMS 2024",
        "rang_preference": 1
    }
    
    tester.log_request("POST", f"{API_BASE}/diseases/{disease_id}/treatments", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/diseases/{disease_id}/treatments", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            tester.mark_success("Traitement associé à la pathologie")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

# =============================================================================
# TESTS CLINICAL CASES
# =============================================================================

def test_clinical_cases_create():
    if 'disease' not in tester.created_ids:
        tester.write("⚠️  Aucune pathologie créée, test ignoré", Colors.YELLOW)
        return False
    
    tester.test_header("POST", "/api/v1/clinical-cases/", "Créer un cas clinique")
    
    data = {
        "code_fultang": f"TEST_API_{int(time.time())}",
        "pathologie_principale_id": tester.created_ids['disease'],
        "pathologies_secondaires_ids": [],
        "presentation_clinique": {
            "histoire_maladie": "Patient de 28 ans consultant pour céphalées intenses",
            "symptomes_patient": [
                {
                    "symptome_id": tester.created_ids.get('symptom', 1),
                    "details": "Céphalée intense"
                }
            ],
            "antecedents": {
                "medicaux": ["RAS"]
            }
        },
        "donnees_paracliniques": {},
        "evolution_patient": "Amélioration",
        "images_associees_ids": [],
        "sons_associes_ids": [],
        "medicaments_prescrits": [],
        "niveau_difficulte": 3,
        "duree_estimee_resolution_min": 45,
        "objectifs_apprentissage": ["Diagnostic"],
        "competences_requises": {}
    }
    
    tester.log_request("POST", f"{API_BASE}/clinical-cases/", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/clinical-cases/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['clinical_case'] = result['id']
            tester.mark_success(f"Cas clinique créé avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False

def test_clinical_cases_list():
    tester.test_header("GET", "/api/v1/clinical-cases/", "Récupérer la liste des cas cliniques")
    
    params = {"skip": 0, "limit": 5}
    tester.log_request("GET", f"{API_BASE}/clinical-cases/", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/clinical-cases/", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} cas cliniques")
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
        ('clinical_case', 'clinical-cases', 'Cas clinique'),
        ('symptom', 'symptoms', 'Symptôme'),
        ('medication', 'medications', 'Médicament'),
        ('disease', 'diseases', 'Pathologie'),
    ]
    
    for key, endpoint, name in cleanup_order:
        if key in tester.created_ids:
            item_id = tester.created_ids[key]
            tester.write(f"\n🗑️  Suppression {name} ID {item_id}...", Colors.YELLOW)
            
            try:
                response = requests.delete(f"{API_BASE}/{endpoint}/{item_id}", timeout=30)
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
    
    tester.section("TEST SYSTÉMATIQUE COMPLET DE L'API STI MEDICAL EXPERT")
    tester.write(f"URL: {BASE_URL}")
    tester.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tester.write(f"Fichier de sortie: {OUTPUT_FILE}")
    
    print(f"\n{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗")
    print(f"║  TEST AUTOMATIQUE DE TOUTES LES ROUTES DE L'API              ║")
    print(f"║  Chaque test s'exécutera et attendra votre validation        ║")
    print(f"╚═══════════════════════════════════════════════════════════════╝{Colors.END}\n")
    
    try:
        # =====================================================================
        # MODULE 1: SYMPTOMS
        # =====================================================================
        tester.section("MODULE 1: SYMPTOMS - Tests CRUD complets")
        
        # 1.1 Créer un symptôme
        test_symptoms_create()
        tester.wait_for_user()
        
        # 1.2 Lister les symptômes
        test_symptoms_list()
        tester.wait_for_user()
        
        # 1.3 Récupérer un symptôme spécifique
        test_symptoms_read()
        tester.wait_for_user()
        
        # 1.4 Mettre à jour le symptôme
        test_symptoms_update()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 2: DISEASES
        # =====================================================================
        tester.section("MODULE 2: DISEASES - Tests CRUD complets")
        
        # 2.1 Créer une pathologie
        test_diseases_create()
        tester.wait_for_user()
        
        # 2.2 Lister les pathologies
        test_diseases_list()
        tester.wait_for_user()
        
        # 2.3 Récupérer une pathologie spécifique
        test_diseases_read()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 3: MEDICATIONS
        # =====================================================================
        tester.section("MODULE 3: MEDICATIONS - Tests CRUD complets")
        
        # 3.1 Créer un médicament
        test_medications_create()
        tester.wait_for_user()
        
        # 3.2 Lister les médicaments
        test_medications_list()
        tester.wait_for_user()
        
        # 3.3 Récupérer un médicament spécifique
        test_medications_read()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 4: RELATIONS SYMPTÔMES-PATHOLOGIES
        # =====================================================================
        tester.section("MODULE 4: RELATIONS SYMPTÔMES-PATHOLOGIES")
        
        # 4.1 Associer un symptôme à une pathologie
        test_add_symptom_to_disease()
        tester.wait_for_user()
        
        # 4.2 Récupérer les symptômes d'une pathologie
        test_get_symptoms_for_disease()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 5: RELATIONS TRAITEMENTS-PATHOLOGIES
        # =====================================================================
        tester.section("MODULE 5: RELATIONS TRAITEMENTS-PATHOLOGIES")
        
        # 5.1 Associer un traitement à une pathologie
        test_add_treatment_to_disease()
        tester.wait_for_user()
        
        # 5.2 Récupérer les traitements d'une pathologie (nouveau test)
        test_get_treatments_for_disease()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 6: RELATIONS TRAITEMENTS-SYMPTÔMES
        # =====================================================================
        tester.section("MODULE 6: RELATIONS TRAITEMENTS SYMPTOMATIQUES")
        
        # 6.1 Associer un traitement à un symptôme
        test_add_treatment_to_symptom()
        tester.wait_for_user()
        
        # 6.2 Récupérer les traitements d'un symptôme
        test_get_treatments_for_symptom()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 7: CLINICAL CASES
        # =====================================================================
        tester.section("MODULE 7: CLINICAL CASES - Cas cliniques")
        
        # 7.1 Créer un cas clinique
        test_clinical_cases_create()
        tester.wait_for_user()
        
        # 7.2 Lister les cas cliniques
        test_clinical_cases_list()
        tester.wait_for_user()
        
        # 7.3 Récupérer un cas clinique complet
        test_clinical_cases_read()
        tester.wait_for_user()
        
        # 7.4 Récupérer un cas clinique simplifié
        test_clinical_cases_read_simple()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 8: EXPERT STRATEGIES
        # =====================================================================
        tester.section("MODULE 8: EXPERT STRATEGIES - Règles expertes")
        
        # 8.1 Créer une règle experte
        test_expert_strategies_create()
        tester.wait_for_user()
        
        # 8.2 Lister les règles expertes
        test_expert_strategies_list()
        tester.wait_for_user()
        
        # 8.3 Récupérer une règle experte
        test_expert_strategies_read()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 9: DIAGNOSTIC ENGINE
        # =====================================================================
        tester.section("MODULE 9: DIAGNOSTIC ENGINE - Moteur de diagnostic")
        
        # 9.1 Exécuter le moteur de diagnostic
        test_diagnostic_engine_run()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 10: MEDIA (IMAGES)
        # =====================================================================
        tester.section("MODULE 10: MEDIA - Gestion des images médicales")
        
        # 10.1 Créer une image fictive et l'uploader
        test_media_upload_image()
        tester.wait_for_user()
        
        # 10.2 Lister les images
        test_media_list_images()
        tester.wait_for_user()
        
        # 10.3 Récupérer une image spécifique
        test_media_read_image()
        tester.wait_for_user()
        
        # =====================================================================
        # MODULE 11: CHAT
        # =====================================================================
        tester.section("MODULE 11: CHAT - Système de messagerie")
        
        # 11.1 Créer une session de chat et envoyer des messages
        test_chat_send_message()
        tester.wait_for_user()
        
        # 11.2 Récupérer l'historique du chat
        test_chat_get_history()
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
# FONCTIONS DE TEST SUPPLÉMENTAIRES
# =====================================================================

def test_get_treatments_for_disease():
    """Récupère les traitements d'une pathologie"""
    if 'disease' not in tester.created_ids:
        tester.write("⚠️  Aucune pathologie créée, test ignoré", Colors.YELLOW)
        return False
    
    disease_id = tester.created_ids['disease']
    tester.test_header("GET", f"/api/v1/diseases/{disease_id}/treatments", 
                      "Récupérer les traitements d'une pathologie")
    
    tester.log_request("GET", f"{API_BASE}/diseases/{disease_id}/treatments")
    
    try:
        response = requests.get(f"{API_BASE}/diseases/{disease_id}/treatments", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"{len(data)} traitements trouvés")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_add_treatment_to_symptom():
    """Associe un traitement à un symptôme"""
    if 'symptom' not in tester.created_ids or 'medication' not in tester.created_ids:
        tester.write("⚠️  Symptôme ou médicament manquant, test ignoré", Colors.YELLOW)
        return False
    
    symptom_id = tester.created_ids['symptom']
    tester.test_header("POST", f"/api/v1/symptoms/{symptom_id}/treatments", 
                      "Associer un traitement symptomatique")
    
    data = {
        "symptome_id": symptom_id,
        "medicament_id": tester.created_ids['medication'],
        "efficacite": "Bonne",
        "rapidite_action": "15-30 minutes",
        "posologie_recommandee": "1g toutes les 6h si besoin",
        "rang_preference": 1
    }
    
    tester.log_request("POST", f"{API_BASE}/symptoms/{symptom_id}/treatments", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/symptoms/{symptom_id}/treatments", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            tester.mark_success("Traitement symptomatique associé")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_get_treatments_for_symptom():
    """Récupère les traitements d'un symptôme"""
    if 'symptom' not in tester.created_ids:
        tester.write("⚠️  Aucun symptôme créé, test ignoré", Colors.YELLOW)
        return False
    
    symptom_id = tester.created_ids['symptom']
    tester.test_header("GET", f"/api/v1/symptoms/{symptom_id}/treatments", 
                      "Récupérer les traitements symptomatiques")
    
    tester.log_request("GET", f"{API_BASE}/symptoms/{symptom_id}/treatments")
    
    try:
        response = requests.get(f"{API_BASE}/symptoms/{symptom_id}/treatments", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"{len(data)} traitements trouvés")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_clinical_cases_read():
    """Récupère un cas clinique complet"""
    if 'clinical_case' not in tester.created_ids:
        tester.write("⚠️  Aucun cas clinique créé, test ignoré", Colors.YELLOW)
        return False
    
    case_id = tester.created_ids['clinical_case']
    tester.test_header("GET", f"/api/v1/clinical-cases/{case_id}", 
                      "Récupérer un cas clinique complet")
    
    tester.log_request("GET", f"{API_BASE}/clinical-cases/{case_id}")
    
    try:
        response = requests.get(f"{API_BASE}/clinical-cases/{case_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Cas clinique complet récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_clinical_cases_read_simple():
    """Récupère un cas clinique en version simplifiée"""
    if 'clinical_case' not in tester.created_ids:
        tester.write("⚠️  Aucun cas clinique créé, test ignoré", Colors.YELLOW)
        return False
    
    case_id = tester.created_ids['clinical_case']
    tester.test_header("GET", f"/api/v1/clinical-cases/{case_id}/simple", 
                      "Récupérer un cas clinique simplifié")
    
    tester.log_request("GET", f"{API_BASE}/clinical-cases/{case_id}/simple")
    
    try:
        response = requests.get(f"{API_BASE}/clinical-cases/{case_id}/simple", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Cas clinique simplifié récupéré")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_expert_strategies_create():
    """Crée une règle experte"""
    tester.test_header("POST", "/api/v1/expert-strategies/", "Créer une règle experte")
    
    data = {
        "code_regle": f"RULE_TEST_{int(time.time())}",
        "categorie": "Diagnostic",
        "priorite": 8,
        "conditions": {
            "symptomes": ["fièvre", "céphalée", "raideur nuque"],
            "age_min": 0
        },
        "actions": [
            {"type": "alerte", "message": "Suspicion de méningite - Urgence"},
            {"type": "examen", "nom": "Ponction lombaire"}
        ],
        "description_naturelle": "Si fièvre + céphalée + raideur de nuque → suspecter méningite",
        "justification_medicale": "Triade classique de la méningite",
        "expert_auteur": "Dr. Test API",
        "date_validation": "2025-01-17",
        "est_active": True
    }
    
    tester.log_request("POST", f"{API_BASE}/expert-strategies/", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/expert-strategies/", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['expert_strategy'] = result['id']
            tester.mark_success(f"Règle experte créée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_expert_strategies_list():
    """Liste les règles expertes"""
    tester.test_header("GET", "/api/v1/expert-strategies/", "Lister les règles expertes")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{API_BASE}/expert-strategies/", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/expert-strategies/", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} règles")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_expert_strategies_read():
    """Récupère une règle experte"""
    if 'expert_strategy' not in tester.created_ids:
        tester.write("⚠️  Aucune règle experte créée, test ignoré", Colors.YELLOW)
        return False
    
    strategy_id = tester.created_ids['expert_strategy']
    tester.test_header("GET", f"/api/v1/expert-strategies/{strategy_id}", 
                      "Récupérer une règle experte")
    
    tester.log_request("GET", f"{API_BASE}/expert-strategies/{strategy_id}")
    
    try:
        response = requests.get(f"{API_BASE}/expert-strategies/{strategy_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Règle experte récupérée")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_diagnostic_engine_run():
    """Exécute le moteur de diagnostic"""
    tester.test_header("POST", "/api/v1/diagnostic-engine/run", 
                      "Exécuter le moteur de diagnostic")
    
    data = {
        "symptoms": ["fièvre", "céphalée intense", "raideur de nuque"],
        "context": ["adulte jeune", "début brutal"],
        "age": 25
    }
    
    tester.log_request("POST", f"{API_BASE}/diagnostic-engine/run", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/diagnostic-engine/run", json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Moteur de diagnostic exécuté")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_media_upload_image():
    """Upload une image médicale fictive"""
    tester.test_header("POST", "/api/v1/media/images/upload", "Upload d'une image médicale")
    
    # Créer une image fictive (pixel blanc 1x1)
    import io
    from PIL import Image
    
    img = Image.new('RGB', (100, 100), color='white')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    files = {'file': ('test_image.png', img_byte_arr, 'image/png')}
    data = {
        'type_examen': 'Radiographie',
        'sous_type': 'Thorax',
        'description': 'Image de test API'
    }
    
    if 'disease' in tester.created_ids:
        data['pathologie_id'] = tester.created_ids['disease']
    
    tester.log_request("POST", f"{API_BASE}/media/images/upload", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/media/images/upload", 
                               files=files, data=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            result = response.json()
            tester.created_ids['image'] = result['id']
            tester.mark_success(f"Image uploadée avec ID: {result['id']}")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_media_list_images():
    """Liste les images médicales"""
    tester.test_header("GET", "/api/v1/media/images", "Lister les images médicales")
    
    params = {"skip": 0, "limit": 10}
    tester.log_request("GET", f"{API_BASE}/media/images", params=params)
    
    try:
        response = requests.get(f"{API_BASE}/media/images", params=params, timeout=30)
        tester.log_response(response, show_full=False)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Liste récupérée: {len(data)} images")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_media_read_image():
    """Récupère les métadonnées d'une image"""
    if 'image' not in tester.created_ids:
        tester.write("⚠️  Aucune image créée, test ignoré", Colors.YELLOW)
        return False
    
    image_id = tester.created_ids['image']
    tester.test_header("GET", f"/api/v1/media/images/{image_id}", 
                      "Récupérer les métadonnées d'une image")
    
    tester.log_request("GET", f"{API_BASE}/media/images/{image_id}")
    
    try:
        response = requests.get(f"{API_BASE}/media/images/{image_id}", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            tester.mark_success("Métadonnées image récupérées")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_send_message():
    """Envoie un message dans une session de chat"""
    import uuid
    
    session_id = str(uuid.uuid4())
    tester.created_ids['chat_session'] = session_id
    
    tester.test_header("POST", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Envoyer un message dans le chat")
    
    data = {
        "sender": "Etudiant",
        "content": "Bonjour, je souhaite discuter de ce cas clinique",
        "message_metadata": {"type": "question"}
    }
    
    tester.log_request("POST", f"{API_BASE}/chat/sessions/{session_id}/messages", data=data)
    
    try:
        response = requests.post(f"{API_BASE}/chat/sessions/{session_id}/messages", 
                               json=data, timeout=30)
        tester.log_response(response)
        
        if response.status_code == 201:
            tester.mark_success("Message envoyé")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 201")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


def test_chat_get_history():
    """Récupère l'historique d'une session de chat"""
    if 'chat_session' not in tester.created_ids:
        tester.write("⚠️  Aucune session de chat créée, test ignoré", Colors.YELLOW)
        return False
    
    session_id = tester.created_ids['chat_session']
    tester.test_header("GET", f"/api/v1/chat/sessions/{session_id}/messages", 
                      "Récupérer l'historique du chat")
    
    tester.log_request("GET", f"{API_BASE}/chat/sessions/{session_id}/messages")
    
    try:
        response = requests.get(f"{API_BASE}/chat/sessions/{session_id}/messages", timeout=30)
        tester.log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            tester.mark_success(f"Historique récupéré: {len(data)} messages")
            return True
        else:
            tester.mark_failure(f"Code {response.status_code} attendu 200")
            return False
    except Exception as e:
        tester.mark_failure(f"Exception: {str(e)}")
        return False


# =====================================================================
# POINT D'ENTRÉE
# =====================================================================

if __name__ == "__main__":
    main()
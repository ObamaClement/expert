import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://expert-cmck.onrender.com/api/v1"
OUTPUT_FILE = f"update_categories_priority_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Mapping des catégories basé sur les mots-clés
CATEGORY_MAPPINGS = {
    'Cardiologie': [
        'heart', 'cardiac', 'cardio', 'myocard', 'pericardium', 'endocardium',
        'atrial', 'ventricular', 'coronary', 'angina', 'infarction', 'ischemic',
        'arrhythmia', 'tachycardia', 'bradycardia', 'fibrillation', 'hypertension',
        'valve', 'valvular', 'mitral', 'aortic', 'tricuspid', 'pulmonary',
        'congestive', 'failure', 'cardiomyopathy', 'stenosis', 'systolic', 'diastolic'
    ],
    'Pédiatrie': [
        'neonatal', 'newborn', 'infant', 'congenital', 'birth', 'fetal',
        'pediatric', 'childhood', 'developmental', 'baby'
    ],
    'ORL': [
        'ear', 'nose', 'throat', 'pharynx', 'larynx', 'tonsil', 'adenoid',
        'sinus', 'nasal', 'otitis', 'pharyngitis', 'laryngitis', 'rhinitis',
        'mastoid', 'auditory', 'hearing', 'olfactory', 'voice', 'vocal'
    ],
    'Neurologie': [
        'brain', 'cerebral', 'cerebr', 'neurological', 'neurol', 'nervous',
        'epilep', 'seizure', 'stroke', 'hemorrhage', 'hematoma', 'meningitis',
        'encephalitis', 'skull', 'cranial', 'paralysis', 'parkinson', 'dementia',
        'alzheimer', 'multiple sclerosis', 'neuropathy', 'spinal', 'vertebra',
        'intracranial', 'subarachnoid', 'subdural', 'extradural', 'concussion',
        'coma', 'consciousness'
    ],
    'Ophtalmologie': [
        'eye', 'ocular', 'ophthalm', 'vision', 'visual', 'retina', 'cornea',
        'lens', 'pupil', 'iris', 'glaucoma', 'cataract', 'conjunctiv', 'eyelid',
        'blindness', 'optic', 'lacrimal'
    ],
    'Orthopédie': [
        'bone', 'fracture', 'orthopedic', 'skeletal', 'joint', 'arthritis',
        'osteo', 'femur', 'tibia', 'fibula', 'humerus', 'radius', 'ulna',
        'vertebra', 'spine', 'spinal', 'hip', 'knee', 'ankle', 'shoulder',
        'elbow', 'wrist', 'ligament', 'tendon', 'cartilage', 'meniscus',
        'dislocation', 'sprain', 'musculoskeletal', 'limb', 'amputation',
        'intertrochanteric', 'cervical', 'lumbar'
    ],
    'Pneumologie': [
        'lung', 'pulmonary', 'respiratory', 'bronch', 'pneumonia', 'asthma',
        'pleura', 'thorax', 'chest', 'breathing', 'dyspnea', 'emphysema',
        'tuberculosis', 'copd', 'alveolar', 'trachea', 'mediastin', 'ventilat'
    ],
    'Urgences': [
        'emergency', 'trauma', 'injury', 'wound', 'shock', 'poisoning',
        'burn', 'acute', 'severe', 'critical', 'sepsis',
        'septic', 'anaphylaxis', 'overdose', 'accident', 'multiple injuries'
    ],
    'Infectiologie': [
        'infection', 'infectious', 'bacterial', 'viral', 'fungal', 'parasite',
        'abscess', 'cellulitis', 'tuberculosis', 'hiv', 'aids',
        'hepatitis', 'bacilli', 'bacteriological'
    ],
    'Gastroentérologie': [
        'gastro', 'intestin', 'stomach', 'bowel', 'colon', 'rectum', 'anus',
        'esophag', 'duoden', 'ileum', 'jejunum', 'liver', 'hepatic', 'cirrhosis',
        'pancrea', 'gallbladder', 'cholecyst', 'bile', 'biliary', 'ulcer',
        'crohn', 'colitis', 'diverticu', 'hernia', 'peritonitis', 'ascites',
        'fistula', 'tracheoesophageal', 'cholangitis'
    ],
    'Néphrologie': [
        'kidney', 'renal', 'urinary', 'bladder', 'ureter', 'urethra',
        'nephritis', 'nephrotic', 'dialysis', 'uremia', 'proteinuria',
        'hematuria', 'cystitis', 'pyelonephritis'
    ],
    'Dermatologie': [
        'skin', 'derma', 'cutaneous', 'subcutaneous', 'rash', 'lesion',
        'wound', 'cellulitis', 'erythema', 'psoriasis',
        'eczema', 'melanoma', 'carcinoma', 'tissue', 'nodosum'
    ],
    'Endocrinologie': [
        'diabetes', 'diabetic', 'thyroid', 'goiter', 'hormone', 'endocrine',
        'pituitary', 'adrenal', 'pancreatic', 'metabolic', 'gland', 'multinodular'
    ],
    'Hématologie': [
        'blood', 'anemia', 'leukemia', 'lymphoma', 'coagulation', 'bleeding',
        'hemorrhag', 'thrombosis', 'embolism', 'platelet', 'hemophilia'
    ],
    'Rhumatologie': [
        'arthritis', 'rheumat', 'gout', 'lupus', 'spondylitis', 'inflammatory'
    ],
    'Vasculaire': [
        'vascular', 'artery', 'vein', 'carotid', 'occlusion', 'stenosis',
        'atherosclerosis', 'aneurysm'
    ]
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

def print_color(message, color=None, end='\n'):
    if color:
        print(f"{color}{message}{Colors.END}", end=end)
    else:
        print(message, end=end)

def normalize_text(text):
    if not text:
        return ""
    return text.lower().strip()

def determine_category(disease_name):
    """Détermine la catégorie basée sur le nom de la pathologie"""
    if not disease_name:
        return None
    
    normalized_name = normalize_text(disease_name)
    category_scores = {}
    
    for category, keywords in CATEGORY_MAPPINGS.items():
        score = 0
        for keyword in keywords:
            if keyword in normalized_name:
                # Score pondéré selon la longueur du keyword
                score += len(keyword)
        
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    
    return None

def fetch_all_clinical_cases():
    """Récupère tous les cas cliniques"""
    print_color("\n📥 Étape 1: Récupération des cas cliniques...", Colors.CYAN)
    
    all_cases = []
    skip = 0
    limit = 100
    page = 1
    
    while True:
        try:
            params = {"skip": skip, "limit": limit}
            response = requests.get(f"{BASE_URL}/clinical-cases/", params=params, timeout=60)
            
            if response.status_code == 200:
                cases = response.json()
                if not cases:
                    break
                
                all_cases.extend(cases)
                print_color(f"   Page {page}: +{len(cases)} cas (Total: {len(all_cases)})", Colors.BLUE)
                
                if len(cases) < limit:
                    break
                
                skip += limit
                page += 1
            else:
                break
        except Exception as e:
            print_color(f"   ❌ Erreur: {str(e)}", Colors.RED)
            break
    
    print_color(f"✅ Total: {len(all_cases)} cas cliniques\n", Colors.GREEN)
    return all_cases

def fetch_all_diseases():
    """Récupère toutes les pathologies"""
    print_color("\n📥 Étape 2: Récupération des pathologies...", Colors.CYAN)
    
    all_diseases = []
    skip = 0
    limit = 100
    page = 1
    
    while True:
        try:
            params = {"skip": skip, "limit": limit}
            response = requests.get(f"{BASE_URL}/diseases/", params=params, timeout=60)
            
            if response.status_code == 200:
                diseases = response.json()
                if not diseases:
                    break
                
                all_diseases.extend(diseases)
                print_color(f"   Page {page}: +{len(diseases)} pathologies (Total: {len(all_diseases)})", Colors.BLUE)
                
                if len(diseases) < limit:
                    break
                
                skip += limit
                page += 1
            else:
                break
        except Exception as e:
            print_color(f"   ❌ Erreur: {str(e)}", Colors.RED)
            break
    
    print_color(f"✅ Total: {len(all_diseases)} pathologies\n", Colors.GREEN)
    return all_diseases

def update_disease_category(disease_id, new_category):
    """Met à jour la catégorie d'une pathologie"""
    try:
        data = {"categorie": new_category}
        response = requests.patch(
            f"{BASE_URL}/diseases/{disease_id}",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print_color("\n" + "="*100, Colors.CYAN)
    print_color("MISE À JOUR DES CATÉGORIES AVEC PRIORITÉ CAS CLINIQUES", Colors.CYAN)
    print_color("="*100, Colors.CYAN)
    print_color(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as log_file:
        
        def log(message):
            log_file.write(message + '\n')
            log_file.flush()
        
        log("="*100)
        log(f"MISE À JOUR AVEC PRIORITÉ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("="*100)
        
        # Étape 1: Récupérer les cas cliniques
        clinical_cases = fetch_all_clinical_cases()
        
        # Étape 2: Récupérer toutes les pathologies
        all_diseases = fetch_all_diseases()
        
        if not all_diseases:
            print_color("❌ Aucune pathologie récupérée", Colors.RED)
            return
        
        # Créer un dict pour accès rapide
        diseases_dict = {d['id']: d for d in all_diseases}
        
        # Étape 3: Identifier les pathologies principales des cas
        print_color("🔍 Étape 3: Identification des pathologies principales...\n", Colors.YELLOW)
        
        priority_disease_ids = set()
        for case in clinical_cases:
            patho_principale = case.get('pathologie_principale')
            if isinstance(patho_principale, dict):
                priority_disease_ids.add(patho_principale['id'])
        
        print_color(f"✅ {len(priority_disease_ids)} pathologies prioritaires identifiées\n", Colors.GREEN)
        log(f"\nPathologies prioritaires (cas cliniques): {len(priority_disease_ids)}")
        
        # Étape 4: Séparer en prioritaires et secondaires
        print_color("📋 Étape 4: Analyse et classification...\n", Colors.YELLOW)
        
        priority_updates = []
        secondary_updates = []
        category_stats = {}
        
        for disease in all_diseases:
            disease_id = disease['id']
            disease_name = disease.get('nom_fr', '')
            current_category = disease.get('categorie', '')
            
            new_category = determine_category(disease_name)
            
            if new_category:
                if new_category not in category_stats:
                    category_stats[new_category] = 0
                category_stats[new_category] += 1
                
                if current_category != new_category:
                    update_info = {
                        'id': disease_id,
                        'name': disease_name,
                        'old_category': current_category,
                        'new_category': new_category
                    }
                    
                    if disease_id in priority_disease_ids:
                        priority_updates.append(update_info)
                    else:
                        secondary_updates.append(update_info)
        
        # Afficher statistiques
        print_color("📊 Statistiques:", Colors.CYAN)
        print_color(f"   • Pathologies prioritaires à mettre à jour: {len(priority_updates)}", Colors.MAGENTA)
        print_color(f"   • Pathologies secondaires à mettre à jour: {len(secondary_updates)}", Colors.BLUE)
        print_color(f"   • Total à mettre à jour: {len(priority_updates) + len(secondary_updates)}\n", Colors.YELLOW)
        
        log(f"\nPathologies prioritaires à MAJ: {len(priority_updates)}")
        log(f"Pathologies secondaires à MAJ: {len(secondary_updates)}")
        
        # Afficher répartition par catégorie
        print_color("📈 Répartition par catégorie:", Colors.CYAN)
        for category in sorted(category_stats.keys()):
            count = category_stats[category]
            print_color(f"   • {category}: {count} pathologies", Colors.BLUE)
        
        # Demander confirmation
        print_color(f"\n⚠️  Continuer avec la mise à jour? (o/n): ", Colors.YELLOW, end='')
        confirm = input().strip().lower()
        
        if confirm != 'o':
            print_color("❌ Mise à jour annulée", Colors.RED)
            return
        
        # Mise à jour avec priorité
        stats = {
            'priority_success': 0,
            'priority_failed': 0,
            'secondary_success': 0,
            'secondary_failed': 0
        }
        
        # PHASE 1: Pathologies prioritaires (cas cliniques)
        if priority_updates:
            print_color(f"\n🎯 PHASE 1: Mise à jour des pathologies PRIORITAIRES ({len(priority_updates)})", Colors.MAGENTA)
            print_color("="*100, Colors.MAGENTA)
            log("\n" + "="*100)
            log("PHASE 1: PATHOLOGIES PRIORITAIRES (CAS CLINIQUES)")
            log("="*100 + "\n")
            
            for idx, update in enumerate(priority_updates, 1):
                if idx % 10 == 0:
                    print_color(f"   [{idx}/{len(priority_updates)}] Progression: {(idx/len(priority_updates)*100):.1f}%", Colors.BLUE)
                
                log(f"\n[P-{idx}/{len(priority_updates)}] ID: {update['id']}")
                log(f"Nom: {update['name'][:80]}")
                log(f"{update['old_category']} → {update['new_category']}")
                
                success, message = update_disease_category(update['id'], update['new_category'])
                
                if success:
                    stats['priority_success'] += 1
                    log("✅ Succès")
                else:
                    stats['priority_failed'] += 1
                    log(f"❌ Échec: {message}")
                
                time.sleep(0.1)
            
            print_color(f"\n✅ Phase 1 terminée: {stats['priority_success']}/{len(priority_updates)} succès\n", Colors.GREEN)
        
        # PHASE 2: Pathologies secondaires
        if secondary_updates:
            print_color(f"\n📚 PHASE 2: Mise à jour des pathologies SECONDAIRES ({len(secondary_updates)})", Colors.BLUE)
            print_color("="*100, Colors.BLUE)
            log("\n" + "="*100)
            log("PHASE 2: PATHOLOGIES SECONDAIRES")
            log("="*100 + "\n")
            
            for idx, update in enumerate(secondary_updates, 1):
                if idx % 50 == 0:
                    print_color(f"   [{idx}/{len(secondary_updates)}] Progression: {(idx/len(secondary_updates)*100):.1f}%", Colors.BLUE)
                
                log(f"\n[S-{idx}/{len(secondary_updates)}] ID: {update['id']}")
                log(f"{update['old_category']} → {update['new_category']}")
                
                success, message = update_disease_category(update['id'], update['new_category'])
                
                if success:
                    stats['secondary_success'] += 1
                else:
                    stats['secondary_failed'] += 1
                
                time.sleep(0.05)  # Pause plus courte pour les secondaires
            
            print_color(f"\n✅ Phase 2 terminée: {stats['secondary_success']}/{len(secondary_updates)} succès\n", Colors.GREEN)
        
        # Résumé final
        print_color(f"\n{'='*100}", Colors.CYAN)
        print_color("RÉSUMÉ FINAL", Colors.CYAN)
        print_color(f"{'='*100}", Colors.CYAN)
        
        total_success = stats['priority_success'] + stats['secondary_success']
        total_failed = stats['priority_failed'] + stats['secondary_failed']
        total = total_success + total_failed
        
        summary = f"""
🎯 PATHOLOGIES PRIORITAIRES (Cas cliniques):
   • Traitées: {len(priority_updates)}
   • Succès: {stats['priority_success']}
   • Échecs: {stats['priority_failed']}
   • Taux: {(stats['priority_success']/max(len(priority_updates),1)*100):.1f}%

📚 PATHOLOGIES SECONDAIRES:
   • Traitées: {len(secondary_updates)}
   • Succès: {stats['secondary_success']}
   • Échecs: {stats['secondary_failed']}
   • Taux: {(stats['secondary_success']/max(len(secondary_updates),1)*100):.1f}%

📊 TOTAL GLOBAL:
   • Total traité: {total}
   • Succès: {total_success}
   • Échecs: {total_failed}
   • Taux global: {(total_success/max(total,1)*100):.1f}%
"""
        print_color(summary, Colors.GREEN)
        log("\n" + "="*100)
        log("RÉSUMÉ FINAL")
        log("="*100)
        log(summary)
        
        log(f"\n📄 Fichier de log: {OUTPUT_FILE}")
        log(f"📅 Date fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("="*100)
    
    print_color(f"\n📄 Rapport complet: {OUTPUT_FILE}", Colors.CYAN)
    print_color(f"{'='*100}\n", Colors.CYAN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n⚠️  Script interrompu", Colors.YELLOW)
    except Exception as e:
        print_color(f"\n\n❌ ERREUR: {str(e)}", Colors.RED)
        import traceback
        traceback.print_exc()
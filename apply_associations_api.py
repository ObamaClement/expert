import requests
import json
import csv
import io
from datetime import datetime
import time

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BASE_URL = "https://expert-cmck.onrender.com/api/v1"
OUTPUT_FILE = f"application_associations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Seuil de score minimum pour qu'une association soit appliquée
SCORE_THRESHOLD = 10

# Les données CSV extraites du rapport
CSV_DATA = """case_id,pathologie_id,pathologie_name,image_id,image_type,score,type_association
1041,25579,"Closed fracture of surgical neck of humerus",198,"Radio Épaule",40,PROPOSITION
1041,25579,"Closed fracture of surgical neck of humerus",203,"Radio Coude",20,PROPOSITION
1041,25579,"Closed fracture of surgical neck of humerus",204,"Radio Coude",20,PROPOSITION
1043,19789,"Intracerebral hemorrhage",199,"Scanner Cérébral",40,PROPOSITION
1043,19789,"Intracerebral hemorrhage",233,"Scanner Cérébral",40,PROPOSITION
1044,19759,"Congestive heart failure, unspecified",200,"Radio Thorax",40,PROPOSITION
1044,19759,"Congestive heart failure, unspecified",201,"Radio Thorax",20,PROPOSITION
1044,19759,"Congestive heart failure, unspecified",202,"Radio Thorax",20,PROPOSITION
1046,25597,"Other closed fracture of lower end of humerus",198,"Radio Épaule",20,PROPOSITION
1046,25597,"Other closed fracture of lower end of humerus",203,"Radio Coude",20,PROPOSITION
1046,25597,"Other closed fracture of lower end of humerus",204,"Radio Coude",20,PROPOSITION
1047,17069,"Toxic multinodular goiter without mention of thyrotoxic crisis or storm",205,"Écho Thyroïde",30,PROPOSITION
1047,17069,"Toxic multinodular goiter without mention of thyrotoxic crisis or storm",206,"Écho Thyroïde",30,PROPOSITION
1048,19795,"Occlusion and stenosis of carotid artery without mention of cerebral infarction",207,"Echo-Doppler",30,PROPOSITION
1048,19795,"Occlusion and stenosis of carotid artery without mention of cerebral infarction",208,"Echo-Doppler",30,PROPOSITION
1048,19795,"Occlusion and stenosis of carotid artery without mention of cerebral infarction",209,"Echo-Doppler",30,PROPOSITION
1050,26912,"Infection and inflammatory reaction due to other internal orthopedic device, implant, and graft",210,"Radio",20,PROPOSITION
1050,26912,"Infection and inflammatory reaction due to other internal orthopedic device, implant, and graft",211,"Radio",20,PROPOSITION
1051,19596,"Unspecified hypertensive heart disease with heart failure",200,"Radio Thorax",30,PROPOSITION
1051,19596,"Unspecified hypertensive heart disease with heart failure",201,"Radio Thorax",30,PROPOSITION
1051,19596,"Unspecified hypertensive heart disease with heart failure",202,"Radio Thorax",30,PROPOSITION
1058,21090,"Cirrhosis of liver without mention of alcohol",219,"Écho Abdo",20,PROPOSITION
1058,21090,"Cirrhosis of liver without mention of alcohol",270,"Écho Abdo",20,PROPOSITION
1059,21090,"Cirrhosis of liver without mention of alcohol",219,"Écho Abdo",20,PROPOSITION
1059,21090,"Cirrhosis of liver without mention of alcohol",270,"Écho Abdo",20,PROPOSITION
1060,19759,"Congestive heart failure, unspecified",200,"Radio Thorax",40,PROPOSITION
1060,19759,"Congestive heart failure, unspecified",201,"Radio Thorax",20,PROPOSITION
1060,19759,"Congestive heart failure, unspecified",202,"Radio Thorax",20,PROPOSITION
1061,23049,"Closed fracture of base of skull with subarachnoid, subdural, and extradural hemorrhage, with prolonged [more than 24 hours] loss of consciousness, without return to pre-existing conscious level",221,"Scanner Cérébral",30,PROPOSITION
1061,23049,"Closed fracture of base of skull with subarachnoid, subdural, and extradural hemorrhage, with prolonged [more than 24 hours] loss of consciousness, without return to pre-existing conscious level",235,"Scanner Cérébral",20,PROPOSITION
1071,19789,"Intracerebral hemorrhage",199,"Scanner Cérébral",40,PROPOSITION
1071,19789,"Intracerebral hemorrhage",233,"Scanner Cérébral",40,PROPOSITION
1076,24386,"Other open skull fracture with subarachnoid, subdural, and extradural hemorrhage, with prolonged [more than 24 hours] loss of consciousness, without return to pre-existing conscious level",235,"Scanner Cérébral",30,PROPOSITION
1076,24386,"Other open skull fracture with subarachnoid, subdural, and extradural hemorrhage, with prolonged [more than 24 hours] loss of consciousness, without return to pre-existing conscious level",221,"Scanner Cérébral",20,PROPOSITION
1081,19759,"Congestive heart failure, unspecified",200,"Radio Thorax",40,PROPOSITION
1081,19759,"Congestive heart failure, unspecified",201,"Radio Thorax",20,PROPOSITION
1081,19759,"Congestive heart failure, unspecified",202,"Radio Thorax",20,PROPOSITION
1083,19759,"Congestive heart failure, unspecified",200,"Radio Thorax",40,PROPOSITION
1083,19759,"Congestive heart failure, unspecified",201,"Radio Thorax",20,PROPOSITION
1083,19759,"Congestive heart failure, unspecified",202,"Radio Thorax",20,PROPOSITION
1086,21128,"Acute cholecystitis",242,"Écho Abdo",40,PROPOSITION
1087,21334,"Chronic or unspecified duodenal ulcer with hemorrhage, without mention of obstruction",243,"Gastroscopie",20,PROPOSITION
1087,21334,"Chronic or unspecified duodenal ulcer with hemorrhage, without mention of obstruction",244,"Gastroscopie",20,PROPOSITION
1087,21334,"Chronic or unspecified duodenal ulcer with hemorrhage, without mention of obstruction",245,"Gastroscopie",20,PROPOSITION
1089,22193,"Closed fracture of intertrochanteric section of neck of femur",198,"Radio Épaule",20,PROPOSITION
1089,22193,"Closed fracture of intertrochanteric section of neck of femur",246,"Radio Bassin",20,PROPOSITION
1097,21140,"Cholangitis",255,"Scanner/Écho",30,PROPOSITION
1097,21140,"Cholangitis",256,"Scanner/Écho",30,PROPOSITION
1099,24405,"Subarachnoid hemorrhage following injury without mention of open intracranial wound, with loss of consciousness of unspecified duration",257,"Scanner Cérébral",40,PROPOSITION
1104,19764,"Acute on chronic systolic heart failure",200,"Radio Thorax",20,PROPOSITION
1104,19764,"Acute on chronic systolic heart failure",201,"Radio Thorax",20,PROPOSITION
1104,19764,"Acute on chronic systolic heart failure",202,"Radio Thorax",20,PROPOSITION
1106,21302,"Tracheoesophageal fistula",260,"Transit",40,PROPOSITION
1108,21128,"Acute cholecystitis",242,"Écho Abdo",40,PROPOSITION
1113,27653,"Ventilator associated pneumonia",261,"Radio Thorax",50,PROPOSITION
1129,27723,"Closed fracture of first cervical vertebra",247,"Scanner Rachis",20,PROPOSITION
1130,19762,"Acute systolic heart failure",200,"Radio Thorax",20,PROPOSITION
1130,19762,"Acute systolic heart failure",201,"Radio Thorax",20,PROPOSITION
1130,19762,"Acute systolic heart failure",202,"Radio Thorax",20,PROPOSITION
"""

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

def print_color(message, color=None):
    """Affiche un message en couleur"""
    if color:
        print(f"{color}{message}{Colors.END}")
    else:
        print(message)

def get_clinical_case(case_id):
    """Récupère un cas clinique complet"""
    try:
        response = requests.get(f"{BASE_URL}/clinical-cases/{case_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print_color(f"   ⚠️ Erreur {response.status_code} pour le cas {case_id}", Colors.YELLOW)
            return None
    except Exception as e:
        print_color(f"   ❌ Exception lors de la récupération du cas {case_id}: {str(e)}", Colors.RED)
        return None

def update_image_pathology(image_id, pathologie_id):
    """Met à jour la pathologie associée à une image"""
    try:
        data = {"pathologie_id": pathologie_id}
        response = requests.patch(
            f"{BASE_URL}/media/images/{image_id}",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def update_clinical_case(case_id, images_associees_ids):
    """Met à jour les images associées à un cas clinique"""
    try:
        data = {"images_associees_ids": images_associees_ids}
        response = requests.patch(
            f"{BASE_URL}/clinical-cases/{case_id}",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def apply_associations():
    """Script principal pour lire le CSV et appliquer les associations via API"""
    
    print_color("\n" + "="*100, Colors.CYAN)
    print_color("APPLICATION DES ASSOCIATIONS VIA API", Colors.CYAN)
    print_color("="*100, Colors.CYAN)
    print_color(f"\n🎯 Seuil de score minimum: {SCORE_THRESHOLD}", Colors.BLUE)
    print_color(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.BLUE)
    print_color("-" * 100, Colors.CYAN)
    
    csv_file = io.StringIO(CSV_DATA)
    reader = csv.DictReader(csv_file)
    
    # Grouper les associations par cas clinique
    associations_by_case = {}
    for row in reader:
        case_id = int(row['case_id'])
        pathologie_id = int(row['pathologie_id'])
        image_id = int(row['image_id'])
        score = int(row['score'])
        
        if score < SCORE_THRESHOLD:
            continue
        
        if case_id not in associations_by_case:
            associations_by_case[case_id] = {
                'pathologie_id': pathologie_id,
                'images': []
            }
        
        associations_by_case[case_id]['images'].append({
            'image_id': image_id,
            'score': score
        })
    
    print_color(f"\n📊 Statistiques initiales:", Colors.YELLOW)
    print_color(f"   • {len(associations_by_case)} cas cliniques à traiter", Colors.BLUE)
    total_images = sum(len(v['images']) for v in associations_by_case.values())
    print_color(f"   • {total_images} images à associer", Colors.BLUE)
    
    # Ouvrir le fichier de log
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as log_file:
        
        def log(message):
            log_file.write(message + '\n')
            log_file.flush()
        
        log("="*100)
        log(f"APPLICATION DES ASSOCIATIONS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log("="*100)
        log(f"\nSeuil de score: {SCORE_THRESHOLD}")
        log(f"Cas à traiter: {len(associations_by_case)}")
        log(f"Images à associer: {total_images}\n")
        
        # Statistiques
        stats = {
            'cases_processed': 0,
            'cases_success': 0,
            'cases_failed': 0,
            'images_updated': 0,
            'images_failed': 0,
            'already_associated': 0
        }
        
        # Traiter chaque cas
        for idx, (case_id, data) in enumerate(associations_by_case.items(), 1):
            pathologie_id = data['pathologie_id']
            images = data['images']
            
            print_color(f"\n{'─'*100}", Colors.CYAN)
            print_color(f"[{idx}/{len(associations_by_case)}] CAS #{case_id}", Colors.CYAN)
            print_color(f"{'─'*100}", Colors.CYAN)
            
            log(f"\n{'─'*100}")
            log(f"CAS #{case_id} - Pathologie #{pathologie_id}")
            log(f"{'─'*100}")
            
            # Récupérer le cas actuel
            print_color(f"   📥 Récupération du cas clinique...", Colors.BLUE)
            case = get_clinical_case(case_id)
            
            if not case:
                print_color(f"   ❌ Impossible de récupérer le cas {case_id}", Colors.RED)
                log(f"❌ ERREUR: Cas non trouvé")
                stats['cases_failed'] += 1
                continue
            
            stats['cases_processed'] += 1
            
            # Récupérer les images actuellement associées
            current_images = case.get('images_associees_ids', []) or []
            new_images = list(current_images)  # Copie
            
            print_color(f"   📋 Images actuellement associées: {len(current_images)}", Colors.BLUE)
            log(f"Images actuelles: {current_images}")
            
            # Traiter chaque image
            images_to_add = []
            for img_data in images:
                image_id = img_data['image_id']
                score = img_data['score']
                
                print_color(f"\n   🖼️  Image #{image_id} (Score: {score})", Colors.MAGENTA)
                log(f"\n   Image #{image_id} (Score: {score})")
                
                # 1. Mettre à jour la pathologie de l'image
                print_color(f"      → Mise à jour pathologie_id...", Colors.BLUE)
                success, message = update_image_pathology(image_id, pathologie_id)
                
                if success:
                    print_color(f"      ✅ Pathologie associée à l'image", Colors.GREEN)
                    log(f"      ✅ Image {image_id}: pathologie_id = {pathologie_id}")
                    stats['images_updated'] += 1
                else:
                    print_color(f"      ❌ Échec: {message}", Colors.RED)
                    log(f"      ❌ Erreur pathologie: {message}")
                    stats['images_failed'] += 1
                    continue
                
                # 2. Ajouter à la liste si pas déjà présente
                if image_id not in new_images:
                    new_images.append(image_id)
                    images_to_add.append(image_id)
                    print_color(f"      ➕ Image ajoutée à la liste d'association", Colors.GREEN)
                    log(f"      ➕ Image {image_id} ajoutée")
                else:
                    print_color(f"      ℹ️  Image déjà associée au cas", Colors.YELLOW)
                    log(f"      ℹ️  Image {image_id} déjà présente")
                    stats['already_associated'] += 1
                
                # Pause pour éviter de surcharger l'API
                time.sleep(0.2)
            
            # 3. Mettre à jour le cas clinique si de nouvelles images
            if images_to_add:
                print_color(f"\n   💾 Mise à jour du cas clinique...", Colors.BLUE)
                print_color(f"      Images à ajouter: {images_to_add}", Colors.BLUE)
                log(f"\n   Mise à jour cas {case_id}")
                log(f"   Nouvelles images: {images_to_add}")
                log(f"   Total images après: {new_images}")
                
                success, message = update_clinical_case(case_id, new_images)
                
                if success:
                    print_color(f"   ✅ Cas clinique mis à jour avec succès!", Colors.GREEN)
                    log(f"   ✅ Cas mis à jour avec succès")
                    stats['cases_success'] += 1
                else:
                    print_color(f"   ❌ Échec mise à jour: {message}", Colors.RED)
                    log(f"   ❌ Erreur mise à jour cas: {message}")
                    stats['cases_failed'] += 1
            else:
                print_color(f"\n   ℹ️  Aucune nouvelle image à ajouter", Colors.YELLOW)
                log(f"   ℹ️  Pas de nouvelles images")
                stats['cases_success'] += 1
            
            # Pause entre chaque cas
            time.sleep(0.5)
        
        # Résumé final
        print_color(f"\n{'='*100}", Colors.CYAN)
        print_color("RÉSUMÉ DE L'OPÉRATION", Colors.CYAN)
        print_color(f"{'='*100}", Colors.CYAN)
        
        log(f"\n{'='*100}")
        log("RÉSUMÉ FINAL")
        log(f"{'='*100}")
        
        summary = f"""
📊 Cas cliniques:
   • Traités: {stats['cases_processed']}
   • Succès: {stats['cases_success']}
   • Échecs: {stats['cases_failed']}

🖼️  Images:
   • Mises à jour: {stats['images_updated']}
   • Échecs: {stats['images_failed']}
   • Déjà associées: {stats['already_associated']}

✅ Taux de réussite: {(stats['cases_success']/max(stats['cases_processed'],1)*100):.1f}%
"""
        print_color(summary, Colors.GREEN)
        log(summary)
        
        log(f"\n{'='*100}")
        log(f"Fichier de log: {OUTPUT_FILE}")
        log(f"Date fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log(f"{'='*100}")
    
    print_color(f"\n📄 Rapport complet sauvegardé dans: {OUTPUT_FILE}", Colors.CYAN)
    print_color(f"{'='*100}\n", Colors.CYAN)

if __name__ == "__main__":
    try:
        apply_associations()
    except KeyboardInterrupt:
        print_color("\n\n⚠️  Script interrompu par l'utilisateur", Colors.YELLOW)
    except Exception as e:
        print_color(f"\n\n❌ ERREUR CRITIQUE: {str(e)}", Colors.RED)
        import traceback
        traceback.print_exc()
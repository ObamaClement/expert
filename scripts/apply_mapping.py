import sys
import os
import io
import csv
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Assurer que le script peut trouver les modules de l'application
# Ce bloc est important car le script est exécuté depuis le répertoire racine du projet
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from app.database import SessionLocal
from app import models

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Seuil de score minimum pour qu'une association soit appliquée.
# Ajustez cette valeur si nécessaire. Un score de 30 semble un bon début.
SCORE_THRESHOLD = 10

# Les données CSV extraites de votre rapport.
# Coller directement les données ici rend le script autonome.
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

def apply_associations():
    """
    Script principal pour lire le CSV et appliquer les associations
    à la base de données.
    """
    db: Session = SessionLocal()
    
    csv_file = io.StringIO(CSV_DATA)
    reader = csv.DictReader(csv_file)
    
    associations_applied = 0
    associations_skipped = 0
    errors = 0
    
    print("🚀 Démarrage du script d'application des associations...")
    print(f"Seuil de score minimum pour l'association : {SCORE_THRESHOLD}")
    print("-" * 50)
    
    try:
        for row in reader:
            case_id = int(row['case_id'])
            pathologie_id = int(row['pathologie_id'])
            image_id = int(row['image_id'])
            score = int(row['score'])

            if score < SCORE_THRESHOLD:
                print(f"⏩ Cas {case_id} -> Image {image_id}: Score ({score}) trop bas. Ignoré.")
                associations_skipped += 1
                continue

            print(f" APPLYING: Cas #{case_id} → Pathologie #{pathologie_id} → Image #{image_id} (Score: {score})")

            db_case = db.query(models.ClinicalCase).filter(models.ClinicalCase.id == case_id).first()
            db_image = db.query(models.ImageMedicale).filter(models.ImageMedicale.id == image_id).first()
            
            if not db_case or not db_image:
                print(f"   ❌ ERREUR: Cas #{case_id} ou Image #{image_id} non trouvé(e) dans la base de données.")
                errors += 1
                continue

            db_image.pathologie_id = pathologie_id
            print(f"   ✅ Image #{image_id}: pathologie_id mis à jour avec {pathologie_id}.")

            if db_case.images_associees_ids is None:
                db_case.images_associees_ids = []
            
            current_ids = list(db_case.images_associees_ids)
            if image_id not in current_ids:
                current_ids.append(image_id)
                db_case.images_associees_ids = current_ids
                print(f"   ✅ Cas #{case_id}: Image #{image_id} ajoutée à images_associees_ids.")
            else:
                print(f"   ℹ️ Cas #{case_id}: L'image #{image_id} était déjà associée.")

            associations_applied += 1

        print("-" * 50)
        print("Toutes les lignes ont été traitées. Validation des changements...")
        db.commit()
        print("✅ Changements validés dans la base de données.")

    except SQLAlchemyError as e:
        print(f"\n❌ ERREUR DE BASE DE DONNÉES: {e}")
        print("Annulation de toutes les modifications (rollback).")
        db.rollback()
        errors += 1
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        print("Annulation des modifications (rollback).")
        db.rollback()
        errors += 1
    finally:
        print("\n" + "=" * 50)
        print("RÉSUMÉ DE L'OPÉRATION")
        print(f"   Associations appliquées : {associations_applied}")
        print(f"   Associations ignorées (score bas) : {associations_skipped}")
        print(f"   Erreurs rencontrées : {errors}")
        print("=" * 50)
        db.close()
        print("Connexion à la base de données fermée.")

if __name__ == "__main__":
    apply_associations()
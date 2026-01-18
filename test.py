import requests
import json
from datetime import datetime
from collections import defaultdict

# Configuration
BASE_URL = "https://expert-cmck.onrender.com/api/v1"
OUTPUT_FILE = f"associations_cas_patho_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

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

def fetch_all_paginated(endpoint, params_base=None, show_progress=True):
    """Récupère toutes les données paginées d'un endpoint"""
    all_data = []
    skip = 0
    limit = 100
    page = 1
    
    while True:
        try:
            params = params_base.copy() if params_base else {}
            params.update({"skip": skip, "limit": limit})
            
            response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if not data or len(data) == 0:
                    break
                
                all_data.extend(data)
                
                if show_progress:
                    print_color(f"      Page {page}: +{len(data)} items (Total: {len(all_data)})", Colors.BLUE)
                
                # Si on a reçu moins que la limite, c'est la dernière page
                if len(data) < limit:
                    break
                
                skip += limit
                page += 1
            else:
                print_color(f"   ❌ Erreur HTTP {response.status_code}", Colors.RED)
                break
        except Exception as e:
            print_color(f"   ❌ Erreur: {str(e)}", Colors.RED)
            break
    
    return all_data

def get_case_details(case_id):
    """Récupère les détails complets d'un cas clinique"""
    try:
        response = requests.get(f"{BASE_URL}/clinical-cases/{case_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def normalize_text(text):
    """Normalise le texte pour la comparaison"""
    if not text:
        return ""
    return text.lower().strip()

def calculate_match_score(disease_name, image_description, image_type, image_subtype):
    """Calcule un score de correspondance entre une pathologie et une image"""
    score = 0
    disease_lower = normalize_text(disease_name)
    desc_lower = normalize_text(image_description)
    type_lower = normalize_text(image_type)
    subtype_lower = normalize_text(image_subtype)
    
    # Mots-clés importants dans le nom de la pathologie
    disease_keywords = disease_lower.split()
    
    # Vérifier les correspondances dans la description
    for keyword in disease_keywords:
        if len(keyword) > 3:  # Ignorer les mots courts
            if keyword in desc_lower:
                score += 10
            if keyword in type_lower:
                score += 15
            if keyword in subtype_lower:
                score += 15
    
    # Bonus si correspondance exacte
    if disease_lower in desc_lower or desc_lower in disease_lower:
        score += 20
    
    return score

def main():
    print_color("\n" + "="*100, Colors.CYAN)
    print_color("ASSOCIATION CAS CLINIQUES → PATHOLOGIES → IMAGES", Colors.CYAN)
    print_color("="*100, Colors.CYAN)
    
    # 1. Récupérer toutes les données
    print_color("\n📥 ÉTAPE 1: Récupération des données...", Colors.YELLOW)
    
    print_color("   → Récupération des cas cliniques...", Colors.BLUE)
    clinical_cases = fetch_all_paginated("clinical-cases")
    print_color(f"   ✓ {len(clinical_cases)} cas cliniques récupérés", Colors.GREEN)
    
    print_color("   → Récupération des pathologies...", Colors.BLUE)
    diseases = fetch_all_paginated("diseases")
    print_color(f"   ✓ {len(diseases)} pathologies récupérées", Colors.GREEN)
    
    print_color("   → Récupération des images médicales...", Colors.BLUE)
    images = fetch_all_paginated("media/images")
    print_color(f"   ✓ {len(images)} images récupérées", Colors.GREEN)
    
    # 2. Créer des dictionnaires pour accès rapide
    diseases_dict = {d['id']: d for d in diseases}
    images_by_pathology = defaultdict(list)
    unassigned_images = []
    
    for img in images:
        if img.get('pathologie_id'):
            images_by_pathology[img['pathologie_id']].append(img)
        else:
            unassigned_images.append(img)
    
    # 3. Analyse et associations
    print_color("\n🔍 ÉTAPE 2: Analyse et associations...", Colors.YELLOW)
    
    associations = []
    pathologies_in_cases = set()
    cases_without_images = []
    
    for case in clinical_cases:
        case_id = case['id']
        pathologie_id = case.get('pathologie_principale', {}).get('id') if isinstance(case.get('pathologie_principale'), dict) else None
        
        if not pathologie_id:
            continue
        
        pathologies_in_cases.add(pathologie_id)
        pathologie = diseases_dict.get(pathologie_id)
        
        if not pathologie:
            continue
        
        pathologie_name = pathologie.get('nom_fr', 'N/A')
        nb_images = case.get('nb_images', 0)
        
        # Cas avec images déjà associées
        if nb_images > 0:
            # Récupérer les détails du cas pour avoir les IDs des images
            case_details = get_case_details(case_id)
            if case_details and case_details.get('images_associees'):
                for img in case_details['images_associees']:
                    associations.append({
                        'type': 'EXISTANT',
                        'case_id': case_id,
                        'case_code': case.get('code_fultang', 'N/A'),
                        'pathologie_id': pathologie_id,
                        'pathologie_name': pathologie_name,
                        'image_id': img['id'],
                        'image_type': img.get('type_examen', 'N/A'),
                        'image_subtype': img.get('sous_type', 'N/A'),
                        'image_url': img.get('fichier_url', 'N/A'),
                        'score': 100  # Score parfait pour association existante
                    })
        
        # Chercher des images déjà associées à cette pathologie
        if pathologie_id in images_by_pathology:
            for img in images_by_pathology[pathologie_id]:
                # Vérifier si cette image n'est pas déjà dans les associations existantes
                already_associated = any(
                    a['case_id'] == case_id and a['image_id'] == img['id'] 
                    for a in associations
                )
                
                if not already_associated:
                    associations.append({
                        'type': 'PATHOLOGIE_DIRECTE',
                        'case_id': case_id,
                        'case_code': case.get('code_fultang', 'N/A'),
                        'pathologie_id': pathologie_id,
                        'pathologie_name': pathologie_name,
                        'image_id': img['id'],
                        'image_type': img.get('type_examen', 'N/A'),
                        'image_subtype': img.get('sous_type', 'N/A'),
                        'image_url': img.get('fichier_url', 'N/A'),
                        'score': 90  # Score très élevé
                    })
        
        # Chercher des correspondances dans les images non assignées
        if nb_images == 0:  # Seulement pour les cas sans images
            cases_without_images.append({
                'case_id': case_id,
                'case_code': case.get('code_fultang', 'N/A'),
                'pathologie_id': pathologie_id,
                'pathologie_name': pathologie_name
            })
            
            best_matches = []
            for img in unassigned_images:
                score = calculate_match_score(
                    pathologie_name,
                    img.get('description', ''),
                    img.get('type_examen', ''),
                    img.get('sous_type', '')
                )
                
                if score > 10:  # Seuil minimum
                    best_matches.append({
                        'type': 'PROPOSITION',
                        'case_id': case_id,
                        'case_code': case.get('code_fultang', 'N/A'),
                        'pathologie_id': pathologie_id,
                        'pathologie_name': pathologie_name,
                        'image_id': img['id'],
                        'image_type': img.get('type_examen', 'N/A'),
                        'image_subtype': img.get('sous_type', 'N/A'),
                        'image_description': img.get('description', 'N/A'),
                        'image_url': img.get('fichier_url', 'N/A'),
                        'score': score
                    })
            
            # Garder les 3 meilleures propositions
            best_matches.sort(key=lambda x: x['score'], reverse=True)
            associations.extend(best_matches[:3])
    
    # 4. Propositions pour pathologies sans cas cliniques mais avec images
    print_color("\n🔍 ÉTAPE 3: Propositions pour autres pathologies...", Colors.YELLOW)
    
    other_pathologies_with_images = []
    for pathologie_id, imgs in images_by_pathology.items():
        if pathologie_id not in pathologies_in_cases:
            pathologie = diseases_dict.get(pathologie_id)
            if pathologie:
                other_pathologies_with_images.append({
                    'pathologie_id': pathologie_id,
                    'pathologie_name': pathologie.get('nom_fr', 'N/A'),
                    'pathologie_code': pathologie.get('code_icd10', 'N/A'),
                    'nb_images': len(imgs),
                    'images': imgs
                })
    
    # 5. Écriture du rapport
    print_color("\n📝 ÉTAPE 4: Génération du rapport...", Colors.YELLOW)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # En-tête
        separator = "="*100
        f.write(separator + '\n')
        f.write("RAPPORT D'ASSOCIATION: CAS CLINIQUES → PATHOLOGIES → IMAGES\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(separator + '\n')
        
        # Statistiques globales
        f.write(f"\n📊 STATISTIQUES GLOBALES\n")
        f.write("-" * 100 + '\n')
        f.write(f"Total cas cliniques: {len(clinical_cases)}\n")
        f.write(f"Cas avec pathologie principale: {len([c for c in clinical_cases if c.get('pathologie_principale')])}\n")
        f.write(f"Pathologies uniques dans les cas: {len(pathologies_in_cases)}\n")
        f.write(f"Cas sans images: {len(cases_without_images)}\n")
        f.write(f"Total d'images: {len(images)}\n")
        f.write(f"Images non assignées: {len(unassigned_images)}\n")
        f.write(f"Associations trouvées/proposées: {len(associations)}\n")
        
        # Section 1: Associations existantes
        existing = [a for a in associations if a['type'] == 'EXISTANT']
        f.write(f"\n\n{'='*100}\n")
        f.write(f"SECTION 1: ASSOCIATIONS EXISTANTES ({len(existing)})\n")
        f.write(f"{'='*100}\n")
        
        if existing:
            for idx, assoc in enumerate(existing, 1):
                f.write(f"\n{idx}. Cas #{assoc['case_id']} ({assoc['case_code']})\n")
                f.write(f"   → Pathologie #{assoc['pathologie_id']}: {assoc['pathologie_name']}\n")
                f.write(f"   → Image #{assoc['image_id']}: {assoc['image_type']}")
                if assoc['image_subtype'] != 'N/A':
                    f.write(f" - {assoc['image_subtype']}")
                f.write(f"\n   → URL: {assoc['image_url']}\n")
                f.write(f"   ✅ SCORE: {assoc['score']}/100 (Association confirmée)\n")
        else:
            f.write("\n⚠️  Aucune association existante trouvée\n")
        
        # Section 2: Associations directes par pathologie
        direct = [a for a in associations if a['type'] == 'PATHOLOGIE_DIRECTE']
        f.write(f"\n\n{'='*100}\n")
        f.write(f"SECTION 2: IMAGES LIÉES À LA PATHOLOGIE (À ASSOCIER) ({len(direct)})\n")
        f.write(f"{'='*100}\n")
        
        if direct:
            for idx, assoc in enumerate(direct, 1):
                f.write(f"\n{idx}. Cas #{assoc['case_id']} ({assoc['case_code']})\n")
                f.write(f"   → Pathologie #{assoc['pathologie_id']}: {assoc['pathologie_name']}\n")
                f.write(f"   → Image #{assoc['image_id']}: {assoc['image_type']}")
                if assoc['image_subtype'] != 'N/A':
                    f.write(f" - {assoc['image_subtype']}")
                f.write(f"\n   → URL: {assoc['image_url']}\n")
                f.write(f"   🔗 SCORE: {assoc['score']}/100 (Image déjà liée à cette pathologie)\n")
        else:
            f.write("\n⚠️  Aucune image directement liée aux pathologies des cas\n")
        
        # Section 3: Propositions intelligentes
        propositions = [a for a in associations if a['type'] == 'PROPOSITION']
        f.write(f"\n\n{'='*100}\n")
        f.write(f"SECTION 3: PROPOSITIONS D'ASSOCIATIONS ({len(propositions)})\n")
        f.write(f"{'='*100}\n")
        
        if propositions:
            current_case = None
            for idx, assoc in enumerate(sorted(propositions, key=lambda x: (x['case_id'], -x['score'])), 1):
                if current_case != assoc['case_id']:
                    current_case = assoc['case_id']
                    f.write(f"\n{'─'*100}\n")
                    f.write(f"CAS #{assoc['case_id']} ({assoc['case_code']})\n")
                    f.write(f"Pathologie: {assoc['pathologie_name']}\n")
                    f.write(f"{'─'*100}\n")
                
                f.write(f"\n   Proposition #{idx}:\n")
                f.write(f"   → Image #{assoc['image_id']}: {assoc['image_type']}")
                if assoc['image_subtype'] != 'N/A':
                    f.write(f" - {assoc['image_subtype']}")
                f.write(f"\n   → Description: {assoc['image_description']}\n")
                f.write(f"   → URL: {assoc['image_url']}\n")
                f.write(f"   💡 SCORE: {assoc['score']}/100 (Correspondance suggérée)\n")
        else:
            f.write("\n⚠️  Aucune proposition d'association trouvée\n")
        
        # Section 4: Autres pathologies avec images (sans cas cliniques)
        f.write(f"\n\n{'='*100}\n")
        f.write(f"SECTION 4: PATHOLOGIES AVEC IMAGES (SANS CAS CLINIQUE) ({len(other_pathologies_with_images)})\n")
        f.write(f"{'='*100}\n")
        
        if other_pathologies_with_images:
            for idx, patho in enumerate(other_pathologies_with_images, 1):
                f.write(f"\n{idx}. Pathologie #{patho['pathologie_id']}: {patho['pathologie_name']}\n")
                f.write(f"   Code ICD-10: {patho['pathologie_code']}\n")
                f.write(f"   Nombre d'images: {patho['nb_images']}\n")
                for img_idx, img in enumerate(patho['images'][:5], 1):  # Max 5 images
                    f.write(f"   → Image #{img['id']}: {img.get('type_examen', 'N/A')}")
                    if img.get('sous_type'):
                        f.write(f" - {img['sous_type']}")
                    f.write(f"\n")
                if patho['nb_images'] > 5:
                    f.write(f"   ... et {patho['nb_images'] - 5} autres images\n")
        
        # Résumé des actions recommandées
        f.write(f"\n\n{'='*100}\n")
        f.write("RÉSUMÉ ET ACTIONS RECOMMANDÉES\n")
        f.write(f"{'='*100}\n")
        f.write(f"\n✅ {len(existing)} associations déjà en place\n")
        f.write(f"🔗 {len(direct)} images à associer directement (même pathologie)\n")
        f.write(f"💡 {len(propositions)} propositions d'associations intelligentes\n")
        f.write(f"📋 {len(other_pathologies_with_images)} pathologies avec images (potentiel pour nouveaux cas)\n")
        
        # Format CSV pour import
        f.write(f"\n\n{'='*100}\n")
        f.write("FORMAT CSV POUR IMPORT\n")
        f.write(f"{'='*100}\n")
        f.write("\ncase_id,pathologie_id,pathologie_name,image_id,image_type,score,type_association\n")
        
        for assoc in sorted(associations, key=lambda x: (x['case_id'], -x['score'])):
            f.write(f"{assoc['case_id']},{assoc['pathologie_id']},\"{assoc['pathologie_name']}\",")
            f.write(f"{assoc['image_id']},\"{assoc['image_type']}\",{assoc['score']},{assoc['type']}\n")
    
    print_color(f"\n✅ Rapport généré avec succès!", Colors.GREEN)
    print_color(f"📄 Fichier: {OUTPUT_FILE}", Colors.CYAN)
    print_color(f"\n📊 Résumé:", Colors.YELLOW)
    print_color(f"   • {len(existing)} associations existantes", Colors.GREEN)
    print_color(f"   • {len(direct)} images liées à la pathologie", Colors.BLUE)
    print_color(f"   • {len(propositions)} propositions intelligentes", Colors.MAGENTA)
    print_color(f"   • {len(other_pathologies_with_images)} pathologies avec images (sans cas)", Colors.YELLOW)
    print_color(f"\n{'='*100}\n", Colors.CYAN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n⚠️  Analyse interrompue", Colors.YELLOW)
    except Exception as e:
        print_color(f"\n\n❌ ERREUR: {str(e)}", Colors.RED)
        import traceback
        traceback.print_exc()
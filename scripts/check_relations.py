import sys
import os
from sqlalchemy import inspect

# Ajoute la racine du projet au path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
# Importez tous les modèles pour être sûr qu'ils sont enregistrés
from app import models 

def check_db_relations():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    print(f"\n--- AUDIT DE LA BASE DE DONNÉES ({len(table_names)} tables trouvées) ---\n")
    
    # 1. Vérification des Tables
    print("📋 LISTE DES TABLES :")
    for table in sorted(table_names):
        print(f"  - {table}")
        
    print("\n🔗 VÉRIFICATION DES RELATIONS (Clés Étrangères) :")
    
    # 2. Vérification des Clés Étrangères
    relations_found = 0
    for table_name in sorted(table_names):
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print(f"\n  TABLE '{table_name}' est liée à :")
            for fk in fks:
                referred_table = fk.get('referred_table')
                constrained_columns = fk['constrained_columns'] # La colonne source (ex: learner_id)
                referred_columns = fk['referred_columns'] # La colonne cible (ex: id)
                
                print(f"    -> {referred_table} (via {constrained_columns[0]} -> {referred_columns[0]})")
                relations_found += 1
    
    print(f"\n✨ Total de {relations_found} relations de clé étrangère trouvées.")
    
    if relations_found > 10: # On en attend beaucoup
        print("✅ La structure relationnelle semble riche et interconnectée.")
    else:
        print("⚠️ Attention : Peu de relations trouvées. Vérifiez vos modèles.")

if __name__ == "__main__":
    check_db_relations()
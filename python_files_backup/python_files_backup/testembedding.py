from app.services.embedding_service import embedding_service

text = "Pneumonie avec fièvre élevée"
vector = embedding_service.get_text_embedding(text)

print(f"Texte : {text}")
print(f"Taille du vecteur : {len(vector)}")
print(f"Aperçu : {vector[:5]}...")
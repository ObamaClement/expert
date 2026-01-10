from app.database import SessionLocal
from app.services.rag_service import MedicalRAGService

def test_rag():
    db = SessionLocal()
    rag = MedicalRAGService(db)

    # Question de test
    question = "Quels sont les signes et comment soigner une Pneumonie ?"
    
    print("-" * 50)
    response = rag.answer_question(question)
    print("-" * 50)
    print("🤖 RÉPONSE DU LLM :")
    print(response)
    
    db.close()

if __name__ == "__main__":
    test_rag()
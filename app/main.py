from fastapi import FastAPI
from .api.v1 import symptoms,diseases,medications,media,clinical_cases,expert_strategies,diagnostic

app = FastAPI(
    title="STI Medical Expert Module",
    description="Base de connaissances et moteur de raisonnement pour le STI médical.",
    version="0.1.0"
)


app.include_router(symptoms.router, prefix="/api/v1")
app.include_router(diseases.router, prefix="/api/v1")
app.include_router(medications.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(clinical_cases.router, prefix="/api/v1")
app.include_router(expert_strategies.router, prefix="/api/v1")
app.include_router(diagnostic.router, prefix="/api/v1")

@app.get("/")
def read_root():
    """
    Endpoint racine pour vérifier que le service est en ligne.
    """
    return {"status": "Service is running"}
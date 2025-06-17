from fastapi.testclient import TestClient
from api import api # Importe l'instance de l'API FastAPI.
import logging

# Crée un client de test pour l'API.
client = TestClient(api)

# Teste le point de terminaison racine.
def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bienvenue sur l'API de prédiction de sentiment pour Air Paradis"}

# Teste la prédiction de sentiment positif.
def test_predict_positive_sentiment():
    response = client.post("/predict", json={"text": "I love this company ! the service was excellent !!!"})
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert data["sentiment"] == "positif"

# Teste la prédiction de sentiment négatif.
def test_predict_negative_sentiment():
    response = client.post("/predict", json={"text": "What a bad flight. It was late and the service was bad :("})
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert data["sentiment"] == "negatif"
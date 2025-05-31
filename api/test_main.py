from fastapi.testclient import TestClient
from api import api
import logging

client = TestClient(api)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API de prédiction de sentiment pour Air Paradis"}

def test_predict_positive_sentiment():
    response = client.post("/predict", json={"text": "I love this company ! the service was excellent !!!"})
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert data["sentiment"] == "positif" 

def test_predict_negative_sentiment():
    response = client.post("/predict", json={"text": "What a bad flight. It was late and the service was bad :("})
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data
    assert data["sentiment"] == "negatif"
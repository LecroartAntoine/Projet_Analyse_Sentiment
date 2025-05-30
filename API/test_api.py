import pytest
import json
import azure.functions as func
import os

try:
    from function_app import predict_sentiment, root_endpoint, log_feedback, logger, model, tokenizer # For potential checks or setup
except ImportError as e:
    print(f"ImportError: {e}. Ensure your function_app.py and shared_code are accessible.")
    print(f"Current working directory: {os.getcwd()}")
    pytest.exit(f"Failed to import function app modules: {e}", 1)


# Fixture to ensure model is loaded (though it loads on import of function_app)
# This is more of a check or a place for future test-specific setup
@pytest.fixture(scope="session", autouse=True)
def ensure_model_loaded():
    logger.info("Test session starting: Checking model and tokenizer.")
    if model is None or tokenizer is None:
        pytest.fail("Model or tokenizer failed to load. Check shared_code/app_setup.py and model paths.")
    logger.info("Model and tokenizer are loaded for tests.")
    # You could potentially set a test-specific APPLICATIONINSIGHTS_CONNECTION_STRING here if needed
    # os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = "..."


def create_mock_http_request(
    method: str,
    url: str,
    body: dict = None,
    params: dict = None,
    headers: dict = None,
    route_params: dict = None
) -> func.HttpRequest:
    """Helper function to create a mock HttpRequest."""
    req_body_bytes = json.dumps(body).encode('utf-8') if body else None
    req_headers = headers if headers else {}
    if body and 'content-type' not in (key.lower() for key in req_headers.keys()):
        req_headers['Content-Type'] = 'application/json'

    return func.HttpRequest(
        method=method,
        url=url,
        headers=req_headers,
        params=params,
        route_params=route_params,
        body=req_body_bytes
    )

def test_read_main():
    req = create_mock_http_request(method="GET", url="http://localhost/api/")

    response = root_endpoint.build().get_user_function()(req) 

    assert response.status_code == 200
    response_json = json.loads(response.get_body().decode())
    assert response_json == {"message": "API de prédiction de sentiment pour Air Paradis (Azure Function v2)"}

def test_predict_positive_sentiment():
    payload = {"text": "I love this company ! the service was excellent !!!"}
    req = create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

    response = predict_sentiment.build().get_user_function()(req)

    assert response.status_code == 200
    data = json.loads(response.get_body().decode())
    assert "sentiment" in data
    assert data["sentiment"] == "positif"
    assert "probability" in data
    assert isinstance(data["probability"], float)

def test_predict_negative_sentiment():
    payload = {"text": "What a bad flight. It was late and the service was bad :("}
    req = create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

    response = predict_sentiment.build().get_user_function()(req)

    assert response.status_code == 200
    data = json.loads(response.get_body().decode())
    assert "sentiment" in data
    assert data["sentiment"] == "negatif"
    assert "probability" in data
    assert isinstance(data["probability"], float)

def test_predict_invalid_json():
    req = func.HttpRequest(
        method="POST",
        url="http://localhost/api/predict",
        headers={"Content-Type": "application/json"}, 
        body=b"this is not json"
    )
    response = predict_sentiment.build().get_user_function()(req)
    assert response.status_code == 400 
    assert "Please pass a valid JSON object" in response.get_body().decode()


def test_predict_missing_text_field():
    payload = {"message": "This is not the right field"} # Missing 'text'
    req = create_mock_http_request(method="POST", url="http://localhost/api/predict", body=payload)

    response = predict_sentiment.build().get_user_function()(req)
    assert response.status_code == 400 
    data = json.loads(response.get_body().decode())
    assert "error" in data
    assert "Invalid request body" in data["error"]
    assert any("text" in detail["loc"] and "Field required" in detail["msg"] for detail in data["details"])


def test_log_feedback_misprediction():
    payload = {
        "tweet_text": "Great flight!",
        "predicted_sentiment": "negatif",
        "actual_sentiment_is_different": True
    }
    req = create_mock_http_request(method="POST", url="http://localhost/api/feedback", body=payload)

    response = log_feedback.build().get_user_function()(req)

    assert response.status_code == 200
    data = json.loads(response.get_body().decode())
    assert data == {"message": "Feedback received, misprediction logged."}


def test_log_feedback_no_misprediction():
    payload = {
        "tweet_text": "Bad flight!",
        "predicted_sentiment": "negatif",
        "actual_sentiment_is_different": False
    }
    req = create_mock_http_request(method="POST", url="http://localhost/api/feedback", body=payload)

    response = log_feedback.build().get_user_function()(req)

    assert response.status_code == 200
    data = json.loads(response.get_body().decode())
    assert data == {"message": "Feedback received."}

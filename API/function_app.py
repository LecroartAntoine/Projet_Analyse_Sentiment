import azure.functions as func
import json
import traceback
from pydantic import ValidationError
import os
import logging
import traceback
import pickle
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from pydantic import BaseModel
from opencensus.ext.azure.log_exporter import AzureLogHandler

# --- Logger Setup ---
logger = logging.getLogger("SentimentAnalysisApp") # Custom logger name
logger.setLevel(logging.INFO)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


MODEL_FILE_PATH = "./model.keras"
TOKENIZER_FILE_PATH = "./tokenizer.pkl"
MAX_SEQUENCE_LENGTH = 100


try:
    model = load_model(MODEL_FILE_PATH)
    with open(TOKENIZER_FILE_PATH, 'rb') as handle:
        tokenizer = pickle.load(handle)
    logger.info("Model and tokenizer loaded successfully!")
except Exception:
    logger.error(f"Error loading model or tokenizer: {traceback.format_exc()}")

# --- Pydantic Models ---
class TweetInput(BaseModel):
    text: str

class SentimentPrediction(BaseModel):
    sentiment: str
    probability: float

class FeedbackInput(BaseModel):
    tweet_text: str
    predicted_sentiment: str
    actual_sentiment_is_different: bool


@app.route(route="predict")
def predict(req: func.HttpRequest) -> func.HttpResponse:
    
    logger.info("Python HTTP trigger function processed a /predict request.")

    if model is None or tokenizer is None:
        logger.error("Model or Tokenizer not loaded. Cannot perform prediction.")
        return func.HttpResponse(
            json.dumps({"error": "Model or Tokenizer not available. Check server logs."}),
            status_code=503,
            mimetype="application/json"
        )

    try:
        req_body = req.get_json()
    except ValueError:
        logger.error("Invalid JSON format in request body.")
        return func.HttpResponse(
            "Please pass a valid JSON object in the request body",
            status_code=400
        )

    try:
        tweet_input = TweetInput(**req_body)
    except ValidationError as e:
        logger.error(f"Request body validation error: {e.errors()}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid request body", "details": e.errors()}),
            status_code=400,
            mimetype="application/json"
        )

    try:
        sequences = tokenizer.texts_to_sequences([tweet_input.text])
        padded_sequences = pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH)
        
        prediction_output = model.predict(padded_sequences)
        
        if prediction_output.ndim == 2 and prediction_output.shape[0] == 1 and prediction_output.shape[1] == 1:
            prediction_proba = prediction_output[0][0]
        elif prediction_output.ndim == 1 and prediction_output.shape[0] == 1:
            prediction_proba = prediction_output[0]
        else:
            logger.error(f"Unexpected model prediction output shape: {prediction_output.shape}")
            raise ValueError("Unexpected model prediction output shape")

        proba_pos = float(prediction_proba)
        threshold = 0.5
        sentiment_label = "negatif" if proba_pos < threshold else "positif"
        
        if proba_pos < threshold :
            estimated_prob = (1 - proba_pos * 2) * 100
        else :
            estimated_prob = ((proba_pos - 0.5) * 2) * 100

        estimated_prob = max(0.0, min(100.0, estimated_prob))

        response_data = SentimentPrediction(sentiment=sentiment_label, probability=float(estimated_prob))
        
        return func.HttpResponse(
            response_data.model_dump_json(), 
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error during prediction: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": "An error occurred during prediction.", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="welcome")
def welcome(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Python HTTP trigger function processed a / request.")
    return func.HttpResponse(
        json.dumps({"message": "API de prédiction de sentiment pour Air Paradis"}),
        mimetype="application/json"
    )
    
@app.route(route="feedback")
def feedback(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Python HTTP trigger function processed a /feedback request .")

    try:
        req_body = req.get_json()
    except ValueError:
        logger.error("Invalid JSON format in feedback request body.")
        return func.HttpResponse(
            "Please pass a valid JSON object in the request body",
            status_code=400
        )

    try:
        feedback_input = FeedbackInput(**req_body)
    except ValidationError as e:
        logger.error(f"Feedback request body validation error: {e.errors()}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid request body for feedback", "details": e.errors()}),
            status_code=400,
            mimetype="application/json"
        )

    if feedback_input.actual_sentiment_is_different:
        log_message = (
            f"Misprediction reported by user. "
            f"Tweet: '{feedback_input.tweet_text}', "
            f"Predicted: '{feedback_input.predicted_sentiment}'"
        )
        logger.warning(log_message) 
        return func.HttpResponse(
            json.dumps({"message": "Feedback received, misprediction logged."}),
            mimetype="application/json"
        )
    else:
        return func.HttpResponse(
            json.dumps({"message": "Feedback received."}),
            mimetype="application/json"
        )
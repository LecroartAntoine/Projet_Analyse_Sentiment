import azure.functions as func
import json
import traceback
from tensorflow.keras.preprocessing.sequence import pad_sequences # Specific import
from pydantic import ValidationError

      
# shared_code/app_setup.py
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # Set before importing TensorFlow

import logging
import traceback
import pickle
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from pydantic import BaseModel
from opencensus.ext.azure.log_exporter import AzureLogHandler

# --- Logger Setup ---
logger = logging.getLogger("SentimentAnalysisApp") # Custom logger name
logger.setLevel(logging.INFO)

# Prevent adding handler multiple times
if not any(isinstance(handler, AzureLogHandler) for handler in logger.handlers):
    CONNECTION_STRING = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if CONNECTION_STRING:
        try:
            azure_log_handler = AzureLogHandler(connection_string=CONNECTION_STRING)
            logger.addHandler(azure_log_handler)
            logger.info("AzureLogHandler configured successfully for SentimentAnalysisApp.")
        except Exception as e:
            # Fallback to console logging if App Insights handler fails
            print(f"ERROR: Failed to initialize AzureLogHandler: {e}") # Print for immediate visibility
            logger.addHandler(logging.StreamHandler()) # Add console handler
            logger.error(f"Failed to initialize AzureLogHandler: {e}")
    else:
        logger.addHandler(logging.StreamHandler()) # Fallback if no connection string
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set. Logging to console.")

MODEL_DIR = "./model"
MODEL_FILE_PATH = os.path.join(MODEL_DIR, "model.keras")
TOKENIZER_FILE_PATH = os.path.join(MODEL_DIR, "keras_tokenizer.pkl")
MAX_SEQUENCE_LENGTH = 100

model = None
tokenizer = None


model_exists = os.path.exists(MODEL_FILE_PATH)
tokenizer_exists = os.path.exists(TOKENIZER_FILE_PATH)

if model_exists and tokenizer_exists:
    try:
        model = load_model(MODEL_FILE_PATH)
        with open(TOKENIZER_FILE_PATH, 'rb') as handle:
            tokenizer = pickle.load(handle)
        logger.info("Model and tokenizer loaded successfully!")
    except Exception:
        logger.error(f"Error loading model or tokenizer: {traceback.format_exc()}")
        # model and tokenizer will remain None
else:
    if not model_exists:
        logger.error(f"Model file not found at expected path: {os.path.abspath(MODEL_FILE_PATH)}")
    if not tokenizer_exists:
        logger.error(f"Tokenizer file not found at expected path: {os.path.abspath(TOKENIZER_FILE_PATH)}")
    logger.error("Model or tokenizer file missing. Prediction will not be available.")


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

    

# Create a FunctionApp instance.
# You can set a default authorization level for all HTTP functions here.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="predict", methods=[func.HttpMethod.POST])
def predict_sentiment(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Python HTTP trigger function processed a /predict request.")

    if model is None or tokenizer is None:
        logger.error("Model or Tokenizer not loaded. Cannot perform prediction.")
        return func.HttpResponse(
             json.dumps({"error": "Model or Tokenizer not available. Check server logs."}),
             status_code=503, # Service Unavailable
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

@app.route(route="/", methods=[func.HttpMethod.GET]) # Or route="" for the root
def root_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("Python HTTP trigger function processed a / request.")
    return func.HttpResponse(
        json.dumps({"message": "API de prédiction de sentiment pour Air Paradis"}),
        mimetype="application/json"
    )

@app.route(route="feedback", methods=[func.HttpMethod.POST])
def log_feedback(req: func.HttpRequest) -> func.HttpResponse:
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
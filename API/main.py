import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
from fastapi import FastAPI
from pydantic import BaseModel
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle 
import traceback
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

CONNECTION_STRING = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=CONNECTION_STRING))
logger.setLevel(logging.INFO) 

api = FastAPI()

try :
  model = load_model("./model/model.keras")
  with open('./model/keras_tokenizer.pkl', 'rb') as handle:
      tokenizer = pickle.load(handle)
  MAX_SEQUENCE_LENGTH = 100 

  logger.info("Modèle chargé!")
except Exception :
  logger.error(traceback.format_exc())


class TweetInput(BaseModel):
    text: str

class SentimentPrediction(BaseModel):
    sentiment: str
    probability: float

@api.post("/predict", response_model=SentimentPrediction)
async def predict_sentiment(tweet: TweetInput):

    sequences = tokenizer.texts_to_sequences([tweet.text])
    padded_sequences = pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH)
    prediction_proba = model.predict(padded_sequences)[0][0]
    
    proba_pos = float(prediction_proba)

    threshold = 0.5
    sentiment_label = "negatif" if proba_pos < threshold else "positif"
    
    if proba_pos < threshold :
      estimated_prob = (1 - proba_pos*2) *100
      
    else :
      estimated_prob =  ((proba_pos - 0.5) *2) *100

    return SentimentPrediction(sentiment=sentiment_label, probability=float(estimated_prob))

@api.get("/")
async def root():
    return {"message": "API de prédiction de sentiment pour Air Paradis"}
  
class FeedbackInput(BaseModel):
    tweet_text: str
    predicted_sentiment: str
    actual_sentiment_is_different: bool

@api.post("/feedback")
async def log_feedback(feedback: FeedbackInput):
    if feedback.actual_sentiment_is_different:
        log_message = f"Misprediction reported by user. Tweet: '{feedback.tweet_text}', Predicted: '{feedback.predicted_sentiment}'"
        logger.warning(log_message) 

        return {"message": "Feedback received, misprediction logged."}
    return {"message": "Feedback received."}
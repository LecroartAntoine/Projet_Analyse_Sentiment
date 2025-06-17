from dotenv import load_dotenv
import os
from fastapi import FastAPI
from pydantic import BaseModel
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle
import re
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import contractions
import traceback
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# Charge les variables d'environnement.
load_dotenv()

# Désactive les optimisations OneDNN pour TensorFlow.
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Configure la chaîne de connexion pour Azure Application Insights.
CONNECTION_STRING = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")

# Configure le logger pour Azure Application Insights.
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=CONNECTION_STRING))
logger.setLevel(logging.INFO)

# Initialise l'application FastAPI.
api = FastAPI()

# Télécharge les ressources NLTK nécessaires si elles ne sont pas déjà présentes.
try:
    stopwords.words("english")
except LookupError:
    nltk.download("stopwords")
try:
    word_tokenize("test")
except LookupError:
    nltk.download("punkt")
try:
    WordNetLemmatizer().lemmatize("cats")
except LookupError:
    nltk.download("wordnet")
    nltk.download("omw-1.4")

# Initialise les composants globaux pour le traitement du texte.
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))

# Charge le modèle de prédiction et le tokenizer.
try:
    model = load_model("./model.keras")
    with open('./tokenizer.pkl', 'rb') as handle:
        tokenizer = pickle.load(handle)
    MAX_SEQUENCE_LENGTH = 20
    logger.info("Modèle chargé!")
except Exception:
    logger.error(traceback.format_exc())

# Définit le modèle de données pour l'entrée du tweet.
class TweetInput(BaseModel):
    text: str

# Définit le modèle de données pour la sortie de prédiction de sentiment.
class SentimentPrediction(BaseModel):
    sentiment: str
    probability: float

# Fonction de prétraitement du texte sans suppression des stop words.
def preprocess_no_stopwords(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()  # Convertit en minuscules.
    text = contractions.fix(text)  # Développe les contractions.
    text = re.sub(r"http\S+|www\S+", "", text)  # Supprime les URL.
    text = re.sub(r"@\w+", "", text)  # Supprime les mentions.
    text = re.sub(r"#\w+", "", text)  # Supprime les hashtags.
    text = re.sub(r"\d+", "", text)  # Supprime les nombres.
    text = re.sub(r"[^a-z\s]", "", text)  # Supprime les caractères spéciaux.

    tokens = word_tokenize(text)  # Tokenise le texte.
    cleaned_tokens = []
    for word in tokens:
        if len(word) > 1:
            lemma = lemmatizer.lemmatize(word)  # Lemmatise le mot.
            cleaned_tokens.append(lemma)
    return " ".join(cleaned_tokens)

# Point de terminaison pour la prédiction de sentiment.
@api.post("/predict", response_model=SentimentPrediction)
async def predict_sentiment(tweet: TweetInput):
    preprocessed_tweet = preprocess_no_stopwords(tweet.text)  # Prétraite le tweet.

    sequences = tokenizer.texts_to_sequences([preprocessed_tweet])  # Convertit en séquences de nombres.
    padded_sequences = pad_sequences(sequences, maxlen=MAX_SEQUENCE_LENGTH)  # Pad les séquences.
    prediction_proba = model.predict(padded_sequences)[0][0]  # Obtient la probabilité de prédiction.

    proba_pos = float(prediction_proba)

    threshold = 0.5
    sentiment_label = "negatif" if proba_pos < threshold else "positif"  # Détermine le sentiment.

    # Calcule la probabilité estimée en pourcentage.
    if proba_pos < threshold:
        estimated_prob = (1 - proba_pos * 2) * 100
    else:
        estimated_prob = ((proba_pos - 0.5) * 2) * 100

    return SentimentPrediction(sentiment=sentiment_label, probability=float(estimated_prob))

# Point de terminaison racine.
@api.get("/")
async def root():
    return {"message": "Bienvenue sur l'API de prédiction de sentiment pour Air Paradis"}

# Définit le modèle de données pour le feedback utilisateur.
class FeedbackInput(BaseModel):
    tweet_text: str
    predicted_sentiment: str
    actual_sentiment_is_different: bool

# Point de terminaison pour enregistrer le feedback utilisateur.
@api.post("/feedback")
async def log_feedback(feedback: FeedbackInput):
    if feedback.actual_sentiment_is_different:
        log_message = f"Misprediction reported by user. Tweet: '{feedback.tweet_text}', Predicted: '{feedback.predicted_sentiment}'"
        logger.warning(log_message)  # Log l'erreur.

        # Crée une trace pour le feedback de misprédiction.
        tracer = Tracer(exporter=AzureExporter(connection_string=CONNECTION_STRING), sampler=ProbabilitySampler(1.0))
        with tracer.span(name='MispredictionFeedback') as span:
            span.add_attribute("tweet_text", feedback.tweet_text)
            span.add_attribute("predicted_sentiment", feedback.predicted_sentiment)
        return {"message": "Merci ! L'erreur a été signalée pour analyse."}
    return {"message": "Merci pour votre retour !"}

# Sert les fichiers statiques depuis le répertoire './static'.
api.mount("/static", StaticFiles(directory="./static"), name="static")

# Point de terminaison pour afficher un article de blog statique.
@api.get("/blog", response_class=HTMLResponse)
async def read_blog_article():
    blog_file_path = os.path.join("./static", "article.html")
    if os.path.exists(blog_file_path):
        return FileResponse(blog_file_path)  # Renvoie le fichier HTML.
    return HTMLResponse(content="<h1>Article non trouvé</h1>", status_code=404)
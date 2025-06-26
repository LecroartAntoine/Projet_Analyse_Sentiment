import streamlit as st
import requests
import pandas as pd

# URL de l'API de prédiction.
API_URL = "http://cityhand.fr:8000//predict"
# URL de l'API pour le feedback.
FEEDBACK_URL = "http://cityhand.fr:8000//feedback"

@st.cache_data
def load_data(filepath="data.csv"):
    """Charge les tweets depuis un fichier CSV."""
    try:
        df = pd.read_csv(filepath)
        if 'tweet' not in df.columns:
            st.error("Le fichier data.csv doit contenir une colonne nommée 'text'.")
            return None
        return df
    except FileNotFoundError:
        st.error(f"Erreur : Le fichier '{filepath}' est introuvable. Veuillez le placer à côté de votre script.")
        return None

# Charge les données au démarrage de l'application.
tweet_data = load_data()

# ### MODIFIÉ ### : Définition de la fonction de callback.
# Cette fonction sera appelée lorsque le bouton "Suggérer" est cliqué.
def suggest_random_tweet():
    """Sélectionne un tweet aléatoire et le met dans st.session_state."""
    if tweet_data is not None and not tweet_data.empty:
        random_tweet = tweet_data['tweet'].sample(n=1).iloc[0]
        st.session_state.tweet_input = random_tweet
        # Réinitialise l'état de la prédiction précédente
        st.session_state.prediction_made = False
        st.session_state.feedback_message = None
    else:
        st.warning("Impossible de charger les données pour la suggestion.")

# Titre de l'application Streamlit.
st.title("Testeur de Sentiment Air Paradis")

# Initialise les variables d'état de session si elles n'existent pas.
if 'prediction_made' not in st.session_state:
    st.session_state.prediction_made = False
    st.session_state.sentiment = None
    st.session_state.probability = None
    st.session_state.tweet_text_for_feedback = ""
    st.session_state.feedback_message = None
if 'tweet_input' not in st.session_state:
    st.session_state.tweet_input = ""

# Zone de texte pour l'entrée du tweet.
# Elle est maintenant "contrôlée" par la valeur dans st.session_state.tweet_input
st.text_area("Entrez un tweet (en anglais) :", key="tweet_input")

# Utilisation de colonnes pour les boutons
col_predict, col_suggest = st.columns([3, 2])

with col_predict:
    # Ce bouton déclenche une action immédiate, donc on peut le garder dans un 'if'.
    if st.button("Prédire le sentiment", use_container_width=True):
        # La valeur du text_area est lue depuis st.session_state
        if st.session_state.tweet_input:
            try:
                response = requests.post(API_URL, json={"text": st.session_state.tweet_input})
                response.raise_for_status()
                prediction_data = response.json()

                st.session_state.sentiment = prediction_data.get("sentiment")
                st.session_state.probability = prediction_data.get("probability")
                st.session_state.tweet_text_for_feedback = st.session_state.tweet_input
                st.session_state.prediction_made = True
                st.session_state.feedback_message = None

            except requests.exceptions.RequestException as e:
                st.error(f"Erreur lors de l'appel à l'API de prédiction : {e}", icon="🚨")
                st.session_state.prediction_made = False
            except Exception as e:
                st.error(f"Une erreur inattendue est survenue : {e}", icon="🚨")
                st.session_state.prediction_made = False
        else:
            st.warning("Veuillez entrer un tweet.")
            st.session_state.prediction_made = False

with col_suggest:
    # ### MODIFIÉ ### : Utilisation du paramètre on_click.
    # La logique est maintenant dans la fonction suggest_random_tweet.
    # Il n'y a plus besoin de 'if' autour du bouton.
    st.button(
        "Suggérer un tweet",
        on_click=suggest_random_tweet, # Passe la fonction en callback
        use_container_width=True
    )

# Affiche les résultats de la prédiction si une prédiction a été faite.
if st.session_state.prediction_made and st.session_state.sentiment is not None:
    st.write("---")
    st.write(f"Tweet analysé : \"{st.session_state.tweet_text_for_feedback}\"")
    st.write(f"Sentiment Prédit : **{st.session_state.sentiment}**")
    if st.session_state.probability is not None:
        st.write(f"Probabilité : {st.session_state.probability:.4f}")

    st.subheader("Cette prédiction est-elle correcte ?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Oui, correcte !", key="feedback_yes"):
            # ... (le reste du code est inchangé) ...
            try:
                response = requests.post(FEEDBACK_URL, json={
                    "tweet_text": st.session_state.tweet_text_for_feedback,
                    "predicted_sentiment": st.session_state.sentiment,
                    "actual_sentiment_is_different": False
                })
                response.raise_for_status()
                feedback_response_data = response.json()
                st.session_state.feedback_message = ("success", f"{feedback_response_data.get('message', '')}")
            except requests.exceptions.RequestException as e:
                st.session_state.feedback_message = ("error", f"Erreur lors de l'envoi du retour : {e}")

    with col2:
        if st.button("Non, incorrecte.", key="feedback_no"):
            try:
                response = requests.post(FEEDBACK_URL, json={
                    "tweet_text": st.session_state.tweet_text_for_feedback,
                    "predicted_sentiment": st.session_state.sentiment,
                    "actual_sentiment_is_different": True
                })
                response.raise_for_status()
                feedback_response_data = response.json()
                st.session_state.feedback_message = ("success", f"{feedback_response_data.get('message', '')}")
            except requests.exceptions.RequestException as e:
                st.session_state.feedback_message = ("error", f"Erreur lors de l'envoi du retour : {e}")

# Affiche le message de feedback si défini.
if st.session_state.feedback_message:
    msg_type, msg_content = st.session_state.feedback_message
    if msg_type == "success":
        st.success(msg_content, icon="✅")
    elif msg_type == "error":
        st.error(msg_content, icon="🚨")
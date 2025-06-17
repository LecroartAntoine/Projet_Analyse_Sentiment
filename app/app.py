import streamlit as st
import requests

# URL de l'API de prédiction.
API_URL = "http://cityhand.fr:8000//predict"
# URL de l'API pour le feedback.
FEEDBACK_URL = "http://cityhand.fr:8000//feedback"

# Titre de l'application Streamlit.
st.title("Testeur de Sentiment Air Paradis")

# Initialise les variables d'état de session si elles n'existent pas.
if 'prediction_made' not in st.session_state:
    st.session_state.prediction_made = False
    st.session_state.sentiment = None
    st.session_state.probability = None
    st.session_state.tweet_text_for_feedback = ""
    st.session_state.feedback_message = None

# Zone de texte pour l'entrée du tweet.
tweet_text = st.text_area("Entrez un tweet (en anglais) :", key="tweet_input")

# Bouton pour déclencher la prédiction.
if st.button("Prédire le sentiment"):
    if tweet_text:
        try:
            # Appel à l'API de prédiction.
            response = requests.post(API_URL, json={"text": tweet_text})
            response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP.
            prediction_data = response.json()

            # Stocke les résultats de la prédiction dans l'état de session.
            st.session_state.sentiment = prediction_data.get("sentiment")
            st.session_state.probability = prediction_data.get("probability")
            st.session_state.tweet_text_for_feedback = tweet_text
            st.session_state.prediction_made = True
            st.session_state.feedback_message = None  # Efface tout message de feedback précédent.

        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de l'appel à l'API de prédiction : {e}", icon="🚨")
            st.session_state.prediction_made = False
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue lors de la prédiction : {e}", icon="🚨")
            st.session_state.prediction_made = False
    else:
        st.warning("Veuillez entrer un tweet.")
        st.session_state.prediction_made = False

# Affiche les résultats de la prédiction si une prédiction a été faite.
if st.session_state.prediction_made and st.session_state.sentiment is not None:
    st.write(f"Tweet analysé : \"{st.session_state.tweet_text_for_feedback}\"")
    st.write(f"Sentiment Prédit : **{st.session_state.sentiment}**")
    if st.session_state.probability is not None:
        st.write(f"Probabilité : {st.session_state.probability:.4f}")

    st.subheader("Cette prédiction est-elle correcte ?")
    col1, col2 = st.columns(2)

    with col1:
        # Bouton pour confirmer que la prédiction est correcte.
        if st.button("Oui, correcte !", key="feedback_yes"):
            try:
                # Envoie le feedback à l'API.
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
            except Exception as e:
                st.session_state.feedback_message = ("error", f"Erreur inattendue lors du retour : {e}")

    with col2:
        # Bouton pour signaler que la prédiction est incorrecte.
        if st.button("Non, incorrecte.", key="feedback_no"):
            try:
                # Envoie le feedback à l'API.
                response = requests.post(FEEDBACK_URL, json={
                    "tweet_text": st.session_state.tweet_text_for_feedback,
                    "predicted_sentiment": st.session_state.sentiment,
                    "actual_sentiment_is_different": True
                })
                response.raise_for_status()
                feedback_response_data = response.json()
                st.session_state.feedback_message = ("error", f"{feedback_response_data.get('message', '')}", "🚨")
            except requests.exceptions.RequestException as e:
                st.session_state.feedback_message = ("error", f"Erreur lors de l'envoi du retour : {e}")
            except Exception as e:
                st.session_state.feedback_message = ("error", f"Erreur inattendue lors du retour : {e}")

# Affiche le message de feedback si défini.
if st.session_state.feedback_message:
    msg_type, msg_content, *icon = st.session_state.feedback_message
    if msg_type == "success":
        st.success(msg_content)
    elif msg_type == "error":
        the_icon = icon[0] if icon else "🚨"
        st.error(msg_content, icon=the_icon)
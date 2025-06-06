import streamlit as st
import requests # Pour appeler votre API déployée
# import time # Not used, can be removed

API_URL = "http://cityhand.fr:8000//predict"
FEEDBACK_URL = "http://cityhand.fr:8000//feedback"

st.title("Testeur de Sentiment Air Paradis")

# Initialize session state variables if they don't exist
if 'prediction_made' not in st.session_state:
    st.session_state.prediction_made = False
    st.session_state.sentiment = None
    st.session_state.probability = None
    st.session_state.tweet_text_for_feedback = "" # To store the text for which prediction was made
    st.session_state.feedback_message = None # To store the feedback success/error message

tweet_text = st.text_area("Entrez un tweet (en anglais) :", key="tweet_input") # Added a key for clarity

if st.button("Prédire le sentiment"):
    if tweet_text:
        try:
            response = requests.post(API_URL, json={"text": tweet_text})
            response.raise_for_status()
            prediction_data = response.json()

            # Store prediction results in session state
            st.session_state.sentiment = prediction_data.get("sentiment")
            st.session_state.probability = prediction_data.get("probability")
            st.session_state.tweet_text_for_feedback = tweet_text # Store the text that was predicted
            st.session_state.prediction_made = True
            st.session_state.feedback_message = None # Clear any previous feedback message

        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de l'appel à l'API de prédiction : {e}", icon="🚨")
            st.session_state.prediction_made = False # Ensure no stale prediction is shown
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue lors de la prédiction : {e}", icon="🚨")
            st.session_state.prediction_made = False
    else:
        st.warning("Veuillez entrer un tweet.")
        st.session_state.prediction_made = False # No prediction if no text

# This block will now execute if a prediction has been made,
# regardless of which button was pressed in the last interaction.
if st.session_state.prediction_made and st.session_state.sentiment is not None:
    st.write(f"Tweet analysé : \"{st.session_state.tweet_text_for_feedback}\"") # Show what was analyzed
    st.write(f"Sentiment Prédit : **{st.session_state.sentiment}**")
    if st.session_state.probability is not None:
        st.write(f"Probabilité : {st.session_state.probability:.4f}")

    st.subheader("Cette prédiction est-elle correcte ?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Oui, correcte !", key="feedback_yes"):
            try:
                response = requests.post(FEEDBACK_URL, json={
                    "tweet_text": st.session_state.tweet_text_for_feedback, # Use stored text
                    "predicted_sentiment": st.session_state.sentiment,
                    "actual_sentiment_is_different": False
                })
                response.raise_for_status()
                feedback_response_data = response.json()
                # Store feedback message to display it *after* this button's logic
                st.session_state.feedback_message = ("success", f"{feedback_response_data.get('message', '')}")
            except requests.exceptions.RequestException as e:
                st.session_state.feedback_message = ("error", f"Erreur lors de l'envoi du retour : {e}")
            except Exception as e:
                st.session_state.feedback_message = ("error", f"Erreur inattendue lors du retour : {e}")


    with col2:
        if st.button("Non, incorrecte.", key="feedback_no"):
            try:
                response = requests.post(FEEDBACK_URL, json={
                    "tweet_text": st.session_state.tweet_text_for_feedback, # Use stored text
                    "predicted_sentiment": st.session_state.sentiment,
                    "actual_sentiment_is_different": True
                })
                response.raise_for_status()
                feedback_response_data = response.json()
                st.session_state.feedback_message = ("error", f"{feedback_response_data.get('message', '')}", "🚨") # Using tuple for type, message, icon
            except requests.exceptions.RequestException as e:
                st.session_state.feedback_message = ("error", f"Erreur lors de l'envoi du retour : {e}")
            except Exception as e:
                st.session_state.feedback_message = ("error", f"Erreur inattendue lors du retour : {e}")

# Display the feedback message if it's set
if st.session_state.feedback_message:
    msg_type, msg_content, *icon = st.session_state.feedback_message
    if msg_type == "success":
        st.success(msg_content)
    elif msg_type == "error":
        the_icon = icon[0] if icon else "🚨"
        st.error(msg_content, icon=the_icon)
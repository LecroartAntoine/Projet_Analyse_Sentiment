import streamlit as st
import requests # Pour appeler votre API déployée

API_URL = "https://airparadisapi.azurewebsites.net//predict" # URL de votre API déployée
FEEDBACK_URL = "https://airparadisapi.azurewebsites.net//feedback"

st.title("Testeur de Sentiment Air Paradis")

tweet_text = st.text_area("Entrez un tweet (en anglais) :")

if st.button("Prédire le sentiment"):
    if tweet_text:
        try:
            response = requests.post(API_URL, json={"text": tweet_text})
            response.raise_for_status() 
            prediction_data = response.json()
            sentiment = prediction_data.get("sentiment")
            probability = prediction_data.get("probability")

            st.write(f"Sentiment Prédit : **{sentiment}**")
            if probability is not None:
                st.write(f"Probabilité : {probability:.4f}")

            st.subheader("Cette prédiction est-elle correcte ?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Oui, correcte !"):
                    requests.post(FEEDBACK_URL, json={
                        "tweet_text": tweet_text,
                        "predicted_sentiment": sentiment,
                        "actual_sentiment_is_different": False
                    })
                    st.success("Merci pour votre retour !")
            with col2:
                if st.button("Non, incorrecte."):
                    requests.post(FEEDBACK_URL, json={
                        "tweet_text": tweet_text,
                        "predicted_sentiment": sentiment,
                        "actual_sentiment_is_different": True
                    })
                    st.error("Merci ! L'erreur a été signalée pour analyse.")
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de l'appel à l'API : {e}")
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue : {e}")
    else:
        st.warning("Veuillez entrer un tweet.")
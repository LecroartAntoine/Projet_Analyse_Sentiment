# OpenClassrooms Projet 7 : Réalisez une analyse de sentiments grâce au Deep Learning

[Dépot GitHub Versionné](https://github.com/LecroartAntoine/Projet_Analyse_Sentiment)

---
---

## Structure du projet

---

- [Modélisation](./Modélisation/)
    - [Exploration & Preprocessing](./Modélisation/Notebook_exploration_preprocessing.ipynb)
    - [Modèle sur mesure simple](./Modélisation/Notebook_model_simple.ipynb)
    - [Modèle sur mesure avancé](./Modélisation/Notebook_model_advanced.ipynb)
    - [Modèle avancé BERT](./Modélisation/Notebook_model_BERT.ipynb)

- [API d'exposition du modèle](./api/)

- [APP Streamlit de test de l'API](./app/)

- [Article de Blog](./Blog/)

---

## API

### 1. Point de Terminaison Racine

*   **Endpoint** : `GET http://cityhand.fr:8000/`
*   **Description** : Un simple point de terminaison de bienvenue pour vérifier que l'API est en cours d'exécution.
*   **Réponse** :
    ```json
    {
      "message": "Bienvenue sur l'API de prédiction de sentiment pour Air Paradis"
    }
    ```

### 2. Prédire le Sentiment

*   **Endpoint** : `POST http://cityhand.fr:8000/predict`
*   **Description** : Analyse le sentiment d'une chaîne de texte donnée.
*   **Corps de la Requête** :
    ```json
    {
      "text": "Le texte de votre tweet ici."
    }
    ```
*   **Exemple de Requête (`curl`)** :
    ```bash
    curl -X POST "http://cityhand.fr:8000/predict" \
    -H "Content-Type: application/json" \
    -d '{"text": "J''adore cette compagnie aérienne, le service était incroyable !"}'
    ```
*   **Réponse de Succès (200 OK)** :
    Retourne le sentiment prédit (`positif` ou `négatif`) et une probabilité de confiance estimée.
    ```json
    {
      "sentiment": "positif",
      "probability": 98.7
    }
    ```

### 3. Enregistrer un Retour Utilisateur

*   **Endpoint** : `POST http://cityhand.fr:8000/feedback`
*   **Description** : Permet aux utilisateurs de signaler une prédiction incorrecte. Si une erreur de prédiction est signalée, un avertissement (`WARNING`) est enregistré dans Azure Application Insights.
*   **Corps de la Requête** :
    ```json
    {
      "tweet_text": "Le vol a été retardé et j'ai manqué ma correspondance.",
      "predicted_sentiment": "positif",
      "actual_sentiment_is_different": true
    }
    ```
*   **Réponse de Succès (200 OK)** :
    Retourne un message de confirmation.
    ```json
    {
      "message": "Merci ! L'erreur a été signalée pour analyse."
    }
    ```

### 4. Contenu Statique

*   **Endpoint** : `GET http://cityhand.fr:8000/blog`
*   **Description** : Sert un article de blog statique au format HTML.
*   **Réponse** : Retourne le fichier `static/article.html`.

*   **Endpoint** : `GET /static/{file_path}`
*   **Description** : Sert n'importe quel fichier depuis le répertoire `./static`.
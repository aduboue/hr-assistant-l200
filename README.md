# HR Assistant Demo

This project contains the code for the **HR Assistant**, an elite executive-level virtual analyst designed to assist a Chief Human Resources Officer in a highly controlled demonstration.

The agent is capable of:
*   Synthesizing complex HR data (headcount, attrition, employee NPS).
*   Proactively detecting weak signals and anomalies (e.g., deteriorating retention).
*   Investigating root causes by cross-referencing HR stats with operational databases (Workday, Greenhouse ATS) via mock tools.
*   Providing actionable remediation strategies and drafting formal strategic memos.

## Project Structure

*   **`hr_agent_app/`**: Contains the agent definition and tools.
    *   `agent.py`: The main agent code, system prompt, and tool definitions.
    *   `mock_data.json`: Mock data injected into the tools for the demo.
*   **`PROMPTS.md`**: Contains the demo playbook with specific prompts to use during the presentation.

## Local Development & Testing

This project uses `uv` for package management and the Agent Development Kit (ADK) for local testing.

### Prerequisites

*   Ensure you have `uv` installed.
*   Initialize the virtual environment and install dependencies:
    ```bash
    uv sync
    ```

### Running the Web Interface

To start the local ADK web server and test the agent:

```bash
./01-run-local.sh
```

Or run the command directly:

```bash
./.venv/bin/adk web --reload_agents .
```

Access the interface at `http://127.0.0.1:8000`.

## Déploiement sur Agent Engine

Vous pouvez déployer les dernières modifications du code de l'agent vers Google Cloud Agent Engine à l'aide de la commande ADK suivante. Si jamais c'est un nouvel agent ne pas utiliser le parametre `--agent_engine_id` :

```bash
adk deploy agent_engine \
  --adk_app_object app \
  --display_name "HR Assistant" \
  --project ai-search-demo-447216 \
  --region us-central1 \
  --agent_engine_id AGENT_ENGINE_ID \
  hr_agent_app
```

## Publication dans Gemini Enterprise

Pour rendre cet agent disponible pour l'organisation via **Gemini Enterprise**, vous devez l'enregistrer dans la console Google Cloud.

Suivez les étapes ci-dessous :

### 1. Préparer l'URL du Reasoning Engine

Vous aurez besoin de l'URL d'API spécifique qui pointe vers l'instance Agent Engine déployée.

- **Chemin de ressource Agent Engine** :
  `https://us-central1-aiplatform.googleapis.com/v1/projects/214344786860/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID`

### 2. Configurer l'authentification OAuth 2.0

Gemini Enterprise utilise OAuth 2.0 pour autoriser l'agent à effectuer des actions au nom de l'utilisateur. Vous aurez besoin de votre **Client ID** et de votre **Client Secret**.

Authorized redirect URIs: `https://vertexaisearch.cloud.google.com/static/oauth/oauth.html` et `https://vertexaisearch.cloud.google.com/oauth-redirect`

Lors du processus d'enregistrement dans la console, renseignez ces URL d'autorisation standard de Google. **Note :** Le paramètre `access_type=offline` est critique pour s'assurer que l'agent peut gérer les requêtes en arrière-plan sans reconnexions constantes. N'oubliez pas de remplacer `YOUR_CLIENT_ID` et `YOUR_CUSTOM_SCOPES` dans l'URL.

- **Authorization URI** : `https://accounts.google.com/o/oauth2/v2/auth?client_id=CLIENT_ID_HERE&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Fstatic%2Foauth%2Foauth.html&scope=openid%20email%20profile&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent`
- **Token URI** : `https://oauth2.googleapis.com/token`

### 3. Étapes d'enregistrement

1. Rendez-vous dans la [Console Google Cloud](https://console.cloud.google.com/) (Projet : `ai-search-demo-447216`).
2. Naviguez vers la section **Gemini Enterprise -> Agents**.
3. Cliquez sur **Enregistrer un nouvel agent**.
4. Remplissez les détails :
   - **Nom de l'agent** : HR Assistant
   - **Description** : Executive-level virtual analyst assisting a Chief Human Resources Officer.
   - **URL du point de terminaison** : Insérez le _Chemin de ressource Agent Engine_ ci-dessus.
5. Dans la section **Authentification**, sélectionnez "OAuth 2.0" et remplissez le "Client ID", le "Client Secret", l'"Authorization URI" et le "Token URI" avec les valeurs ci-dessus.
6. Enregistrez et testez l'agent dans Gemini.

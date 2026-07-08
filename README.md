# 🥗 NutriGuide — AI-Powered Smart Nutrition Assistant

> **Powered by IBM watsonx.ai (Llama 3.3 70B / Granite) on IBM Cloud**

A production-ready, full-stack web application that delivers personalized nutrition guidance through IBM watsonx.ai models. Features an interactive AI chatbot, meal plan generator, calorie tracker, BMI calculator, recipe generator, and multi-family profile management — all in a modern, mobile-responsive interface.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Nutrition Chatbot** | Chat with IBM watsonx.ai (Llama 3.3 70B) for personalized meal plans, recipes & nutrition advice |
| 📊 **Nutrition Dashboard** | Calorie tracking, macro breakdown charts, weekly trend visualization |
| 🧮 **BMI Calculator** | Body Mass Index + TDEE calculation with Mifflin-St Jeor formula |
| 💧 **Water Tracker** | Daily hydration logging with smart targets |
| 🍛 **AI Meal Planner** | 7-day personalized meal plans with Indian & global cuisine support |
| 🍳 **Recipe Generator** | AI recipes from available ingredients with nutritional breakdown |
| 🛒 **Grocery List Builder** | Auto-generated organized shopping lists from meal plans |
| 👨‍👩‍👧 **Family Profiles** | Manage nutrition for multiple family members |
| 📸 **Food Photo Analysis** | Upload food images (placeholder for vision AI integration) |
| 🎤 **Voice Input** | Browser speech recognition for hands-free interaction |
| 🔐 **Secure Auth** | Registration, login, hashed passwords, remember-me sessions |

---

## 🏗️ Project Structure

```
nutrition_app/
├── app.py                    # Main Flask application & all routes
├── models.py                 # SQLAlchemy database models
├── watsonx_client.py         # IBM watsonx.ai integration (auto-detects best model)
├── agent_instructions.py     # ✏️ EDITABLE — AI behavior, tone & rules
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .env                      # 🔒 Your secrets (not committed)
├── instance/
│   └── nutrition_app.db      # SQLite database (auto-created)
├── static/
│   ├── css/style.css         # Application styles
│   ├── js/
│   │   ├── main.js           # Common utilities & toast system
│   │   ├── chat.js           # AI chat interface
│   │   ├── charts.js         # Chart.js dashboard charts
│   │   └── dashboard.js      # Dashboard-specific functions
│   └── uploads/              # Food image uploads
└── templates/
    ├── base.html             # Base layout with navbar & footer
    ├── index.html            # Landing page
    ├── login.html            # Authentication
    ├── register.html         # User registration
    ├── dashboard.html        # Main nutrition dashboard
    ├── chat.html             # AI chatbot interface
    ├── profile.html          # Health profile editor
    ├── bmi_calculator.html   # BMI & TDEE calculator
    └── family.html           # Family profiles manager
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- IBM Cloud account (free Lite tier)
- IBM watsonx.ai project

### 1. Clone & Setup

```bash
cd nutrition_app
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_WATSONX_URL=https://au-syd.ml.cloud.ibm.com
FLASK_SECRET_KEY=your_random_secret_key_here
FLASK_ENV=development
```

> **Region Note:** Use the URL that matches where your watsonx.ai project was created:
> - `https://us-south.ml.cloud.ibm.com` — US South (Dallas)
> - `https://eu-de.ml.cloud.ibm.com` — Europe (Frankfurt)
> - `https://au-syd.ml.cloud.ibm.com` — Asia Pacific (Sydney)
> - `https://jp-tok.ml.cloud.ibm.com` — Asia Pacific (Tokyo)

### 3. Run the Application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🔑 IBM Cloud Setup Guide

### Step 1: Create IBM Cloud Account
1. Go to [https://cloud.ibm.com](https://cloud.ibm.com)
2. Sign up for a **free Lite account**
3. No credit card required for Lite tier

### Step 2: Get Your API Key
1. In IBM Cloud dashboard → Click your profile icon (top right)
2. Select **"IBM Cloud API keys"**
3. Click **"Create an IBM Cloud API key"**
4. Name it `nutriguide-api-key`
5. **Copy the key immediately** (only shown once!)
6. Paste into `.env` as `IBM_API_KEY`

### Step 3: Create a watsonx.ai Project
1. Go to [https://dataplatform.cloud.ibm.com/wx/home](https://dataplatform.cloud.ibm.com/wx/home)
2. Click **"New project"** → **"Create an empty project"**
3. Name: `NutriGuide AI`
4. Select your preferred **region** (note it — use matching URL in `.env`)
5. After creation, go to **Manage → General**
6. Copy the **Project ID** (UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
7. Paste into `.env` as `IBM_PROJECT_ID`

### Step 4: Associate Watson Machine Learning Service
1. In your watsonx.ai project → **Manage → Services & integrations**
2. Click **"Associate service"**
3. Select or create a **Watson Machine Learning** instance (Lite tier: free)
4. Click **Associate**
> ⚠️ This step is required — without an active WML instance, all AI calls will fail.

### Step 5: Verify the AI Model Works
The app **auto-detects** the best available model in this priority order:
1. `meta-llama/llama-3-3-70b-instruct` ← recommended
2. `meta-llama/llama-3-1-8b`
3. `ibm/granite-3-8b-instruct`
4. Additional fallbacks (see `agent_instructions.py`)

To verify in Prompt Lab: Go to your project → **Prompt Lab** → test any model.

---

## ☁️ IBM Cloud Deployment (Code Engine)

### Deploy to IBM Code Engine (Recommended — Free Tier Available)

#### Prerequisites
```bash
# Install IBM Cloud CLI
# Windows: winget install IBM.IBMCloudCLI
# macOS:   brew install ibmcloud-cli
# Linux:   curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

ibmcloud login --apikey YOUR_API_KEY -r au-syd   # change region as needed
ibmcloud plugin install code-engine
```

#### 1. Create a Procfile
```bash
echo "web: gunicorn app:app --bind 0.0.0.0:\$PORT --workers 2" > Procfile
```

#### 2. Create a `requirements.txt` (already done) and ensure `gunicorn` is included.

#### 3. Deploy via IBM Code Engine

```bash
# Login to IBM Cloud (use your region: us-south, eu-de, au-syd, jp-tok)
ibmcloud login --apikey $IBM_API_KEY -r au-syd

# Target resource group
ibmcloud target -g Default

# Create Code Engine project
ibmcloud ce project create --name nutriguide-app
ibmcloud ce project select --name nutriguide-app

# Build the application
ibmcloud ce buildrun submit \
  --name nutriguide-build \
  --source . \
  --strategy buildpacks

# Create the application
ibmcloud ce app create \
  --name nutriguide \
  --image icr.io/YOUR_NAMESPACE/nutriguide:latest \
  --port 5000 \
  --min-scale 0 \
  --max-scale 2 \
  --env IBM_API_KEY=$IBM_API_KEY \
  --env IBM_PROJECT_ID=$IBM_PROJECT_ID \
  --env IBM_WATSONX_URL=https://au-syd.ml.cloud.ibm.com \
  --env FLASK_SECRET_KEY=$FLASK_SECRET_KEY

# Get the public URL
ibmcloud ce app get --name nutriguide --output url
```

### Alternative: Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p instance static/uploads
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
```

```bash
# Build and run
docker build -t nutriguide .
docker run -p 5000:5000 \
  -e IBM_API_KEY=your_key \
  -e IBM_PROJECT_ID=your_project_id \
  -e FLASK_SECRET_KEY=your_secret \
  nutriguide
```

---

## ✏️ Customizing the AI Agent

Edit [`agent_instructions.py`](agent_instructions.py) to customize:

```python
AGENT_INSTRUCTIONS = """
# Modify any of these sections:
=== PERSONALITY & TONE ===       # How the AI communicates
=== NUTRITION SPECIALIZATION === # Food preferences & expertise
=== MEAL PLAN GENERATION ===     # Meal plan structure & format
=== SAFETY & MEDICAL RULES ===   # Safety guardrails
=== CULTURAL & RELIGIOUS ===     # Dietary culture support
=== RESPONSE FORMATTING ===      # Output format rules
"""
```

**Key customizable parameters:**
- `WATSONX_MODEL_CANDIDATES` — Ordered list of models to try (first working one is used)
- `MODEL_PARAMS` — Adjust temperature, max tokens, top-k/p
- Indian food preferences, regional cuisines, festival foods
- Safety rules for medical conditions (diabetes, PCOS, hypertension, etc.)

---

## 🔒 Security Best Practices

- ✅ **Never commit `.env`** — add it to `.gitignore`
- ✅ Passwords are hashed using **Werkzeug's PBKDF2-SHA256**
- ✅ File uploads are sanitized with `secure_filename()`
- ✅ All API endpoints require `@login_required`
- ✅ SQL injection prevented by SQLAlchemy ORM
- ✅ CSRF protection via Flask-WTF (add forms)
- ✅ `MAX_CONTENT_LENGTH` limits upload size to 16MB

```bash
# .gitignore essentials
echo -e ".env\ninstance/\nstatic/uploads/\n__pycache__/\n*.pyc\nvenv/" >> .gitignore
```

---

## 🤖 IBM watsonx.ai Model Information

The app auto-detects the best available model for your project and region.

| Model | Quality | Context |
|---|---|---|
| `meta-llama/llama-3-3-70b-instruct` | ⭐⭐⭐⭐⭐ Best quality | 128K |
| `meta-llama/llama-3-1-8b` | ⭐⭐⭐ Fast & lightweight | 128K |
| `ibm/granite-3-8b-instruct` | ⭐⭐⭐⭐ Granite (if available) | 128K |
| `ibm/granite-3-2b-instruct` | ⭐⭐⭐ Granite compact | 128K |

**IBM Cloud Lite Tier Limits (Free):**
- Watson Machine Learning: ~20 API calls/month free
- Upgrade to Plus/Standard for production workloads
- Code Engine: 100 vCPU-seconds/month free

---

## 📊 Database Schema

| Table | Purpose |
|---|---|
| `users` | Account credentials & metadata |
| `health_profiles` | BMI, goals, dietary preferences |
| `chat_messages` | AI conversation history |
| `calorie_logs` | Daily food intake tracking |
| `water_logs` | Hydration tracking |
| `family_profiles` | Family member nutrition profiles |

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests (create test_app.py first)
pytest tests/ -v

# Check app starts correctly
python -c "from app import create_app; app = create_app(); print('✅ App OK')"
```

---

## 📝 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `IBM_API_KEY` | ✅ Yes | IBM Cloud API key |
| `IBM_PROJECT_ID` | ✅ Yes | watsonx.ai project ID |
| `IBM_WATSONX_URL` | Optional | Region URL — must match your project region (au-syd, us-south, eu-de, jp-tok) |
| `FLASK_SECRET_KEY` | ✅ Yes | Flask session encryption key |
| `FLASK_ENV` | Optional | `development` or `production` |
| `FLASK_DEBUG` | Optional | `True` for dev, `False` for prod |
| `DATABASE_URL` | Optional | SQLite default; use PostgreSQL in prod |
| `MAX_CONTENT_LENGTH` | Optional | Max upload size in bytes (default: 16MB) |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/voice-meal-logging`
3. Commit: `git commit -m "Add voice meal logging"`
4. Push: `git push origin feature/voice-meal-logging`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>🥗 NutriGuide</strong> — Built with ❤️ using IBM watsonx.ai &amp; Flask<br/>
  <sub>IBM Cloud · Llama 3.3 70B / IBM Granite · Python Flask · Bootstrap 5 · Chart.js</sub>
</div>

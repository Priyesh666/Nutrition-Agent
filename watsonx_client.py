"""
IBM watsonx.ai client integration for Smart Nutrition Assistant
"""
import os
import logging
from typing import Optional
from agent_instructions import SYSTEM_PROMPT, MODEL_PARAMS, WATSONX_MODEL_ID_CHAT, WATSONX_MODEL_CANDIDATES

# Graceful import — app runs in demo mode if ibm_watsonx_ai is not installed
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    ModelInference = None
    logging.getLogger(__name__).warning(
        "ibm-watsonx-ai not installed. Running in demo/fallback mode. "
        "Install with: pip install ibm-watsonx-ai"
    )

logger = logging.getLogger(__name__)

# Fix Windows console encoding for emoji in log messages
import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def get_watsonx_client():
    """
    Initialize and return the watsonx.ai model client.
    Auto-detects the first working model from WATSONX_MODEL_CANDIDATES.
    """
    if not WATSONX_AVAILABLE:
        logger.warning("ibm_watsonx_ai not available — running in fallback mode.")
        return None

    api_key = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        logger.warning("IBM_API_KEY or IBM_PROJECT_ID not configured — running in fallback mode.")
        return None

    try:
        credentials = Credentials(url=url, api_key=api_key)
        client = APIClient(credentials)
    except Exception as e:
        logger.error(f"Failed to create watsonx API client: {e}")
        return None

    base_params = {
        GenParams.DECODING_METHOD: MODEL_PARAMS["decoding_method"],
        GenParams.MAX_NEW_TOKENS: MODEL_PARAMS["max_new_tokens"],
        GenParams.MIN_NEW_TOKENS: MODEL_PARAMS["min_new_tokens"],
        GenParams.TEMPERATURE: MODEL_PARAMS["temperature"],
        GenParams.TOP_K: MODEL_PARAMS["top_k"],
        GenParams.TOP_P: MODEL_PARAMS["top_p"],
        GenParams.REPETITION_PENALTY: MODEL_PARAMS["repetition_penalty"],
    }

    # Try each candidate model until one works
    for model_id in WATSONX_MODEL_CANDIDATES:
        try:
            model = ModelInference(
                model_id=model_id,
                api_client=client,
                project_id=project_id,
                params=base_params,
            )
            # Quick probe to confirm it actually works
            test = model.generate_text("Hi")
            if test:
                logger.info(f"[OK] Connected to watsonx.ai -- model: {model_id}")
                return model
        except Exception as e:
            err = str(e)
            if "Inactive" in err or "invalid_instance_status" in err:
                logger.error(
                    "WML instance is INACTIVE. Please reactivate it at "
                    "https://cloud.ibm.com/resources"
                )
                return None  # No point trying other models — same WML instance
            elif "no_associated_service" in err:
                logger.error(
                    f"Project {project_id} has no WML service associated. "
                    "Go to your watsonx.ai project → Manage → Services & integrations → Associate service."
                )
                return None
            elif "not_found" in err or "404" in err:
                logger.error(f"Project ID {project_id} not found. Check IBM_PROJECT_ID in .env")
                return None
            else:
                logger.debug(f"Model {model_id} not available: {err[:80]}")
                continue  # Try next model

    logger.error("No working model found in WATSONX_MODEL_CANDIDATES for this project.")
    return None


def build_user_context(profile) -> str:
    """Build a context string from the user's health profile."""
    if not profile:
        return "No health profile available. Please ask the user to set up their profile."

    ctx_parts = []

    if profile.age:
        ctx_parts.append(f"Age: {profile.age} years")
    if profile.gender:
        ctx_parts.append(f"Gender: {profile.gender}")
    if profile.height_cm:
        ctx_parts.append(f"Height: {profile.height_cm} cm")
    if profile.weight_kg:
        ctx_parts.append(f"Weight: {profile.weight_kg} kg")
    if profile.bmi:
        ctx_parts.append(f"BMI: {profile.bmi} ({profile.bmi_category})")
    if profile.activity_level:
        ctx_parts.append(f"Activity Level: {profile.activity_level.replace('_', ' ').title()}")
    if profile.fitness_goal:
        ctx_parts.append(f"Fitness Goal: {profile.fitness_goal.replace('_', ' ').title()}")
    if profile.dietary_preference:
        ctx_parts.append(f"Dietary Preference: {profile.dietary_preference.replace('_', ' ').title()}")
    if profile.cuisine_preference:
        ctx_parts.append(f"Cuisine Preference: {profile.cuisine_preference}")
    if profile.daily_calorie_target:
        ctx_parts.append(f"Daily Calorie Target: {profile.daily_calorie_target} kcal")
    if profile.allergies_list:
        ctx_parts.append(f"Allergies: {', '.join(profile.allergies_list)}")
    if profile.conditions_list:
        ctx_parts.append(f"Medical Conditions: {', '.join(profile.conditions_list)}")

    return "\n".join(ctx_parts) if ctx_parts else "Profile incomplete."


def generate_nutrition_response(
    user_message: str,
    profile=None,
    conversation_history: list = None,
    model: Optional[ModelInference] = None,
) -> str:
    """
    Generate AI nutrition response using IBM watsonx Granite model.
    Falls back to a helpful static response if the API is unavailable.
    """
    if model is None:
        model = get_watsonx_client()

    if model is None:
        return _fallback_response(user_message)

    user_context = build_user_context(profile)

    # Build prompt with conversation history
    history_text = ""
    if conversation_history:
        for msg in conversation_history[-6:]:  # last 3 turns
            role_label = "User" if msg["role"] == "user" else "NutriGuide"
            history_text += f"{role_label}: {msg['content']}\n"

    prompt = f"""<|system|>
{SYSTEM_PROMPT}

=== USER HEALTH PROFILE ===
{user_context}
<|user|>
{history_text}User: {user_message}
<|assistant|>
NutriGuide:"""

    try:
        response = model.generate_text(prompt=prompt)
        if response:
            return response.strip()
        return _fallback_response(user_message)
    except Exception as e:
        logger.error(f"watsonx API error: {e}")
        return _fallback_response(user_message)


def _fallback_response(user_message: str) -> str:
    """Return a helpful fallback when the AI model is unavailable."""
    msg_lower = user_message.lower()
    if any(w in msg_lower for w in ["meal plan", "diet plan", "weekly plan"]):
        return (
            "**Sample 1-Day Meal Plan** _(AI model temporarily unavailable — configure IBM_API_KEY for full plans)_\n\n"
            "| Meal | Food | Calories |\n|---|---|---|\n"
            "| Breakfast | Oats with banana & almonds | ~320 kcal |\n"
            "| Snack | Apple + 10 walnuts | ~200 kcal |\n"
            "| Lunch | Dal rice, sabzi, curd | ~550 kcal |\n"
            "| Snack | Sprouts chaat | ~150 kcal |\n"
            "| Dinner | Roti, palak paneer, salad | ~480 kcal |\n\n"
            "_Total: ~1700 kcal. Please set up your IBM watsonx credentials for a personalized plan._"
        )
    if any(w in msg_lower for w in ["recipe", "cook", "how to make"]):
        return (
            "**Recipe: Dal Tadka** _(Demo — configure IBM_API_KEY for AI-generated recipes)_\n\n"
            "**Ingredients:** 1 cup toor dal, 1 onion, 2 tomatoes, cumin, turmeric, ghee\n\n"
            "**Steps:**\n1. Pressure cook dal with turmeric (3 whistles)\n"
            "2. Sauté onion till golden, add tomatoes & spices\n"
            "3. Mix with dal, add tadka of ghee + cumin\n\n"
            "_~280 kcal per serving | 15g protein | High in iron_"
        )
    if any(w in msg_lower for w in ["calori", "calorie", "how many"]):
        return (
            "**Common Indian Food Calorie Guide:**\n\n"
            "- Roti (1 medium): ~80 kcal\n- Rice (1 cup cooked): ~200 kcal\n"
            "- Dal (1 cup): ~150 kcal\n- Paneer (100g): ~265 kcal\n"
            "- Curd (1 cup): ~100 kcal\n- Banana (1 medium): ~90 kcal\n\n"
            "_Configure your IBM watsonx API key for detailed nutrition analysis._"
        )
    return (
        "👋 **NutriGuide is ready!** \n\n"
        "To enable full AI-powered responses, please configure your `IBM_API_KEY` and `IBM_PROJECT_ID` "
        "in the `.env` file.\n\n"
        "**I can help you with:**\n"
        "- 🥗 Personalized meal plans\n- 🍳 Healthy recipes\n"
        "- 📊 Calorie & nutrition tracking\n- 💧 Hydration guidance\n"
        "- 🛒 Smart grocery lists\n\n"
        "_Currently running in demo mode. Set up your watsonx credentials to unlock full AI capabilities._"
    )

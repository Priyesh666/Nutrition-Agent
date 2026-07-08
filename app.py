"""
Smart Nutrition Assistant — Flask Application
Powered by IBM watsonx.ai Granite Models
"""
import os
import json
import logging
import uuid
from datetime import date, timedelta, datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, flash, session, send_from_directory
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import func

from models import db, User, HealthProfile, ChatMessage, CalorieLog, WaterLog, FamilyProfile
from watsonx_client import get_watsonx_client, generate_nutrition_response, build_user_context
from template_helpers import register_template_helpers

# ──────────────────────────────────────────────────────────────────
#  Bootstrap
# ──────────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", str(uuid.uuid4()))
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'nutrition_app.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "static", "uploads")

    # ── Extensions ────────────────────────────────────────────────
    db.init_app(app)
    register_template_helpers(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ── Watsonx client (singleton) ────────────────────────────────
    app.watsonx_model = None

    def get_model():
        if app.watsonx_model is None:
            app.watsonx_model = get_watsonx_client()
        return app.watsonx_model

    # ── Helper: allowed file ──────────────────────────────────────
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    # ──────────────────────────────────────────────────────────────
    #  Blueprints / Route groups
    # ──────────────────────────────────────────────────────────────

    # ── Auth routes ───────────────────────────────────────────────
    from flask import Blueprint

    auth = Blueprint("auth", __name__)

    @auth.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")

            if not username or not email or not password:
                flash("All fields are required.", "danger")
                return render_template("register.html")
            if len(password) < 8:
                flash("Password must be at least 8 characters.", "danger")
                return render_template("register.html")
            if password != confirm:
                flash("Passwords do not match.", "danger")
                return render_template("register.html")
            if User.query.filter_by(username=username).first():
                flash("Username already taken.", "danger")
                return render_template("register.html")
            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
                return render_template("register.html")

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            # Create empty profile
            profile = HealthProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

            login_user(user)
            flash(f"Welcome, {username}! Let's set up your health profile.", "success")
            return redirect(url_for("main.profile"))
        return render_template("register.html")

    @auth.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        if request.method == "POST":
            identifier = request.form.get("identifier", "").strip()
            password = request.form.get("password", "")
            remember = bool(request.form.get("remember"))

            user = User.query.filter(
                (User.username == identifier) | (User.email == identifier.lower())
            ).first()

            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get("next")
                flash(f"Welcome back, {user.username}! 🎉", "success")
                return redirect(next_page or url_for("main.dashboard"))
            flash("Invalid credentials. Please try again.", "danger")
        return render_template("login.html")

    @auth.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You've been logged out successfully.", "info")
        return redirect(url_for("auth.login"))

    app.register_blueprint(auth)

    # ── Main routes ───────────────────────────────────────────────
    main = Blueprint("main", __name__)

    @main.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        return render_template("index.html")

    @main.route("/dashboard")
    @login_required
    def dashboard():
        profile = current_user.profile
        today = date.today()

        # Today's calorie summary
        today_logs = CalorieLog.query.filter_by(
            user_id=current_user.id, log_date=today
        ).all()
        total_calories = sum(l.calories or 0 for l in today_logs)
        total_protein = sum(l.protein or 0 for l in today_logs)
        total_carbs = sum(l.carbs or 0 for l in today_logs)
        total_fat = sum(l.fat or 0 for l in today_logs)

        # Today's water
        today_water = WaterLog.query.filter_by(
            user_id=current_user.id, log_date=today
        ).all()
        total_water_ml = sum(w.amount_ml for w in today_water)

        # Last 7 days calorie data for chart
        week_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily_cal = db.session.query(func.sum(CalorieLog.calories)).filter_by(
                user_id=current_user.id, log_date=d
            ).scalar() or 0
            week_data.append({"date": d.strftime("%a"), "calories": round(daily_cal)})

        # Meal breakdown by type for today
        meal_breakdown = {}
        for log in today_logs:
            mt = log.meal_type or "other"
            meal_breakdown[mt] = meal_breakdown.get(mt, 0) + (log.calories or 0)

        return render_template(
            "dashboard.html",
            profile=profile,
            today_logs=today_logs,
            total_calories=round(total_calories),
            total_protein=round(total_protein, 1),
            total_carbs=round(total_carbs, 1),
            total_fat=round(total_fat, 1),
            total_water_ml=round(total_water_ml),
            week_data=json.dumps(week_data),
            meal_breakdown=json.dumps(meal_breakdown),
        )

    @main.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        profile = current_user.profile
        if not profile:
            profile = HealthProfile(user_id=current_user.id)
            db.session.add(profile)
            db.session.commit()

        if request.method == "POST":
            form = request.form
            profile.age = int(form.get("age", 0) or 0) or None
            profile.gender = form.get("gender")
            profile.height_cm = float(form.get("height_cm", 0) or 0) or None
            profile.weight_kg = float(form.get("weight_kg", 0) or 0) or None
            profile.activity_level = form.get("activity_level")
            profile.fitness_goal = form.get("fitness_goal")
            profile.dietary_preference = form.get("dietary_preference")
            profile.cuisine_preference = form.get("cuisine_preference")
            profile.meal_frequency = int(form.get("meal_frequency", 3) or 3)
            profile.medications = form.get("medications", "")

            # Process comma-separated lists
            allergies_raw = form.get("allergies", "")
            conditions_raw = form.get("medical_conditions", "")
            allergies_list = [a.strip() for a in allergies_raw.split(",") if a.strip()]
            conditions_list = [c.strip() for c in conditions_raw.split(",") if c.strip()]
            profile.allergies = json.dumps(allergies_list)
            profile.medical_conditions = json.dumps(conditions_list)

            # Auto-calculate targets
            profile.calculate_targets()
            db.session.commit()
            flash("Profile updated successfully! 🎉", "success")
            return redirect(url_for("main.dashboard"))

        return render_template("profile.html", profile=profile)

    @main.route("/chat")
    @login_required
    def chat():
        profile = current_user.profile
        # Load last 20 messages
        messages = ChatMessage.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatMessage.timestamp.desc()).limit(20).all()
        messages = list(reversed(messages))
        return render_template("chat.html", profile=profile, messages=messages)

    @main.route("/family")
    @login_required
    def family():
        members = FamilyProfile.query.filter_by(owner_id=current_user.id).all()
        return render_template("family.html", members=members)

    @main.route("/bmi-calculator")
    @login_required
    def bmi_calculator():
        profile = current_user.profile
        return render_template("bmi_calculator.html", profile=profile)

    app.register_blueprint(main)

    # ── API routes ────────────────────────────────────────────────
    api = Blueprint("api", __name__, url_prefix="/api")

    @api.route("/chat", methods=["POST"])
    @login_required
    def api_chat():
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

        profile = current_user.profile

        # Get recent history for context
        history_records = ChatMessage.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatMessage.timestamp.desc()).limit(12).all()
        history = [{"role": r.role, "content": r.content} for r in reversed(history_records)]

        # Generate response
        ai_response = generate_nutrition_response(
            user_message=user_message,
            profile=profile,
            conversation_history=history,
            model=get_model(),
        )

        # Save both messages
        user_msg = ChatMessage(
            user_id=current_user.id,
            role="user",
            content=user_message,
            session_id=session.get("chat_session_id", "default"),
        )
        ai_msg = ChatMessage(
            user_id=current_user.id,
            role="assistant",
            content=ai_response,
            session_id=session.get("chat_session_id", "default"),
        )
        db.session.add_all([user_msg, ai_msg])
        db.session.commit()

        return jsonify({"response": ai_response, "timestamp": ai_msg.timestamp.strftime("%H:%M")})

    @api.route("/calorie-log", methods=["POST"])
    @login_required
    def log_calories():
        data = request.get_json(silent=True) or {}
        if not data.get("food_name"):
            return jsonify({"error": "Food name required"}), 400

        log = CalorieLog(
            user_id=current_user.id,
            log_date=date.fromisoformat(data.get("log_date", str(date.today()))),
            meal_type=data.get("meal_type", "snack"),
            food_name=data["food_name"],
            quantity=data.get("quantity", "1 serving"),
            calories=float(data.get("calories", 0) or 0),
            protein=float(data.get("protein", 0) or 0),
            carbs=float(data.get("carbs", 0) or 0),
            fat=float(data.get("fat", 0) or 0),
        )
        db.session.add(log)
        db.session.commit()

        # Return updated totals for today
        today_logs = CalorieLog.query.filter_by(
            user_id=current_user.id, log_date=date.today()
        ).all()
        total_cal = sum(l.calories or 0 for l in today_logs)
        return jsonify({
            "message": "Logged successfully",
            "log": log.to_dict(),
            "daily_total": round(total_cal),
        })

    @api.route("/calorie-log/<int:log_id>", methods=["DELETE"])
    @login_required
    def delete_calorie_log(log_id):
        log = CalorieLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
        db.session.delete(log)
        db.session.commit()
        return jsonify({"message": "Deleted"})

    @api.route("/calorie-log/today", methods=["GET"])
    @login_required
    def get_today_logs():
        today = date.today()
        logs = CalorieLog.query.filter_by(user_id=current_user.id, log_date=today).all()
        return jsonify([l.to_dict() for l in logs])

    @api.route("/water-log", methods=["POST"])
    @login_required
    def log_water():
        data = request.get_json(silent=True) or {}
        amount = float(data.get("amount_ml", 0) or 0)
        if amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        entry = WaterLog(user_id=current_user.id, amount_ml=amount)
        db.session.add(entry)
        db.session.commit()

        today_logs = WaterLog.query.filter_by(
            user_id=current_user.id, log_date=date.today()
        ).all()
        total_ml = sum(w.amount_ml for w in today_logs)
        target = (current_user.profile.daily_water_target or 2.5) * 1000

        return jsonify({
            "message": "Water logged",
            "total_ml": total_ml,
            "target_ml": target,
            "percentage": min(round((total_ml / target) * 100), 100) if target else 0,
        })

    @api.route("/water-log/today", methods=["GET"])
    @login_required
    def get_water_today():
        today = date.today()
        logs = WaterLog.query.filter_by(user_id=current_user.id, log_date=today).all()
        total_ml = sum(w.amount_ml for w in logs)
        target = (current_user.profile.daily_water_target or 2.5) * 1000
        return jsonify({
            "total_ml": total_ml,
            "target_ml": target,
            "percentage": min(round((total_ml / target) * 100), 100) if target else 0,
        })

    @api.route("/bmi-calculate", methods=["POST"])
    @login_required
    def bmi_calculate():
        data = request.get_json(silent=True) or {}
        try:
            weight = float(data["weight_kg"])
            height = float(data["height_cm"])
            age = int(data.get("age", 25))
            gender = data.get("gender", "female")
        except (KeyError, ValueError):
            return jsonify({"error": "Invalid input"}), 400

        h = height / 100
        bmi = round(weight / (h * h), 1)

        if bmi < 18.5:
            category, color = "Underweight", "#3498db"
        elif bmi < 25:
            category, color = "Normal weight", "#2ecc71"
        elif bmi < 30:
            category, color = "Overweight", "#f39c12"
        else:
            category, color = "Obese", "#e74c3c"

        # BMR
        if gender.lower() in ["male", "man", "m"]:
            bmr = round(10 * weight + 6.25 * height - 5 * age + 5)
        else:
            bmr = round(10 * weight + 6.25 * height - 5 * age - 161)

        ideal_weight_min = round(18.5 * h * h, 1)
        ideal_weight_max = round(24.9 * h * h, 1)

        return jsonify({
            "bmi": bmi,
            "category": category,
            "color": color,
            "bmr": bmr,
            "ideal_weight_min": ideal_weight_min,
            "ideal_weight_max": ideal_weight_max,
        })

    @api.route("/generate-meal-plan", methods=["POST"])
    @login_required
    def generate_meal_plan():
        data = request.get_json(silent=True) or {}
        days = data.get("days", 7)
        preferences = data.get("preferences", "")
        profile = current_user.profile

        prompt = f"Generate a detailed {days}-day meal plan"
        if preferences:
            prompt += f" with these preferences: {preferences}"
        prompt += ". Include calories, macros, and preparation tips for each meal."

        response = generate_nutrition_response(
            user_message=prompt,
            profile=profile,
            model=get_model(),
        )
        return jsonify({"meal_plan": response})

    @api.route("/generate-recipe", methods=["POST"])
    @login_required
    def generate_recipe():
        data = request.get_json(silent=True) or {}
        ingredients = data.get("ingredients", "")
        if not ingredients:
            return jsonify({"error": "Please provide ingredients"}), 400

        profile = current_user.profile
        prompt = (
            f"Create a healthy, nutritious recipe using these available ingredients: {ingredients}. "
            f"Provide step-by-step instructions, calorie count, macro breakdown, and nutrition tips."
        )
        response = generate_nutrition_response(
            user_message=prompt,
            profile=profile,
            model=get_model(),
        )
        return jsonify({"recipe": response})

    @api.route("/generate-grocery-list", methods=["POST"])
    @login_required
    def generate_grocery_list():
        data = request.get_json(silent=True) or {}
        meal_plan = data.get("meal_plan", "")
        days = data.get("days", 7)
        profile = current_user.profile

        prompt = (
            f"Generate an organized weekly grocery list for {days} days based on my health profile. "
            f"Categorize by: Vegetables, Fruits, Grains & Pulses, Dairy, Proteins, Spices & Condiments. "
            f"Include quantities and budget tips."
        )
        if meal_plan:
            prompt += f" Based on this meal plan: {meal_plan[:500]}"

        response = generate_nutrition_response(
            user_message=prompt,
            profile=profile,
            model=get_model(),
        )
        return jsonify({"grocery_list": response})

    @api.route("/analyze-food-image", methods=["POST"])
    @login_required
    def analyze_food_image():
        """Placeholder for future food image recognition integration"""
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PNG, JPG, GIF, or WebP"}), 400

        filename = secure_filename(f"{current_user.id}_{uuid.uuid4().hex[:8]}_{file.filename}")
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(upload_path)

        # Placeholder analysis — replace with actual vision model integration
        return jsonify({
            "message": "Image uploaded successfully!",
            "filename": filename,
            "analysis": (
                "**Food Image Analysis** _(Vision AI coming soon!)_\n\n"
                "Image saved for processing. Full AI-powered food recognition will be available "
                "in the next update using IBM Watson Visual Recognition or a multimodal Granite model.\n\n"
                "**What's coming:**\n"
                "- Automatic food identification\n"
                "- Calorie estimation from images\n"
                "- Portion size detection\n"
                "- Instant nutritional breakdown"
            ),
            "image_url": url_for("static", filename=f"uploads/{filename}"),
        })

    @api.route("/family", methods=["GET"])
    @login_required
    def get_family():
        members = FamilyProfile.query.filter_by(owner_id=current_user.id).all()
        return jsonify([m.to_dict() for m in members])

    @api.route("/family", methods=["POST"])
    @login_required
    def add_family_member():
        data = request.get_json(silent=True) or {}
        if not data.get("name"):
            return jsonify({"error": "Name is required"}), 400

        member = FamilyProfile(
            owner_id=current_user.id,
            name=data["name"],
            relationship=data.get("relationship"),
            age=data.get("age"),
            gender=data.get("gender"),
            weight_kg=data.get("weight_kg"),
            height_cm=data.get("height_cm"),
            dietary_preference=data.get("dietary_preference"),
            fitness_goal=data.get("fitness_goal"),
            allergies=json.dumps(data.get("allergies_list", [])),
            medical_conditions=json.dumps(data.get("conditions_list", [])),
            activity_level=data.get("activity_level"),
        )
        db.session.add(member)
        db.session.commit()
        return jsonify({"message": "Family member added", "member": member.to_dict()}), 201

    @api.route("/family/<int:member_id>", methods=["DELETE"])
    @login_required
    def delete_family_member(member_id):
        member = FamilyProfile.query.filter_by(
            id=member_id, owner_id=current_user.id
        ).first_or_404()
        db.session.delete(member)
        db.session.commit()
        return jsonify({"message": "Deleted"})

    @api.route("/family/<int:member_id>/meal-plan", methods=["POST"])
    @login_required
    def family_meal_plan(member_id):
        member = FamilyProfile.query.filter_by(
            id=member_id, owner_id=current_user.id
        ).first_or_404()
        data = request.get_json(silent=True) or {}
        days = data.get("days", 3)

        prompt = (
            f"Generate a {days}-day healthy meal plan for {member.name} "
            f"(Age: {member.age}, Gender: {member.gender or 'not specified'}, "
            f"Dietary preference: {member.dietary_preference or 'not specified'}, "
            f"Goal: {member.fitness_goal or 'general health'}, "
            f"Allergies: {member.allergies or 'none'}). "
            f"Include Indian-style meals with calorie counts."
        )
        response = generate_nutrition_response(user_message=prompt, model=get_model())
        return jsonify({"meal_plan": response, "member_name": member.name})

    @api.route("/chat/clear", methods=["POST"])
    @login_required
    def clear_chat():
        ChatMessage.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({"message": "Chat history cleared"})

    @api.route("/nutrition-tip", methods=["GET"])
    @login_required
    def nutrition_tip():
        profile = current_user.profile
        prompt = "Give me one quick, actionable daily nutrition tip tailored to my profile. Keep it under 60 words and make it practical."
        response = generate_nutrition_response(user_message=prompt, profile=profile, model=get_model())
        return jsonify({"tip": response})

    app.register_blueprint(api)

    # ── Database initialization ───────────────────────────────────
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)
        db.create_all()
        logger.info("Database initialized successfully.")
        
        # Eagerly initialize the watsonx client on startup
        logger.info("Initializing IBM watsonx.ai client...")
        get_model()
        logger.info("IBM watsonx.ai client initialization complete.")

    return app


# ──────────────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug)

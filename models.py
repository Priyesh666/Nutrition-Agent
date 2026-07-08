"""
Database models for Smart Nutrition Assistant
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    profile = db.relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_history = db.relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    calorie_logs = db.relationship("CalorieLog", back_populates="user", cascade="all, delete-orphan")
    water_logs = db.relationship("WaterLog", back_populates="user", cascade="all, delete-orphan")
    family_profiles = db.relationship("FamilyProfile", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class HealthProfile(db.Model):
    """User health profile"""
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    # Basic biometrics
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    activity_level = db.Column(db.String(50))  # sedentary, lightly_active, moderately_active, very_active, extra_active

    # Goals & preferences
    fitness_goal = db.Column(db.String(50))  # weight_loss, weight_gain, maintain, muscle_gain, general_health
    dietary_preference = db.Column(db.String(50))  # vegetarian, vegan, eggetarian, non_vegetarian, jain, sattvic

    # Health information
    allergies = db.Column(db.Text)         # JSON list
    medical_conditions = db.Column(db.Text)  # JSON list
    medications = db.Column(db.Text)

    # Regional preferences
    cuisine_preference = db.Column(db.String(100))
    meal_frequency = db.Column(db.Integer, default=3)

    # Daily targets (auto-calculated)
    daily_calorie_target = db.Column(db.Integer)
    daily_protein_target = db.Column(db.Float)
    daily_carb_target = db.Column(db.Float)
    daily_fat_target = db.Column(db.Float)
    daily_water_target = db.Column(db.Float, default=2.5)  # litres

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="profile")

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if bmi is None:
            return "Unknown"
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal weight"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"

    @property
    def allergies_list(self):
        try:
            return json.loads(self.allergies) if self.allergies else []
        except Exception:
            return []

    @property
    def conditions_list(self):
        try:
            return json.loads(self.medical_conditions) if self.medical_conditions else []
        except Exception:
            return []

    def calculate_targets(self):
        """Calculate BMR, TDEE, and macro targets using Mifflin-St Jeor equation"""
        if not all([self.age, self.gender, self.height_cm, self.weight_kg]):
            return

        # BMR
        if self.gender and self.gender.lower() in ["male", "man", "m"]:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5
        else:
            bmr = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age - 161

        # Activity multiplier
        activity_multipliers = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "very_active": 1.725,
            "extra_active": 1.9,
        }
        multiplier = activity_multipliers.get(self.activity_level, 1.375)
        tdee = bmr * multiplier

        # Adjust for goal
        goal_adjustments = {
            "weight_loss": -500,
            "weight_gain": 400,
            "muscle_gain": 300,
            "maintain": 0,
            "general_health": 0,
        }
        adjustment = goal_adjustments.get(self.fitness_goal, 0)
        calorie_target = max(1200, int(tdee + adjustment))

        self.daily_calorie_target = calorie_target
        # Macros: 50% carbs, 25% protein, 25% fat
        self.daily_protein_target = round((calorie_target * 0.25) / 4, 1)
        self.daily_carb_target = round((calorie_target * 0.50) / 4, 1)
        self.daily_fat_target = round((calorie_target * 0.25) / 9, 1)
        # Water: 35ml per kg body weight
        self.daily_water_target = round(self.weight_kg * 0.035, 1)

    def __repr__(self):
        return f"<HealthProfile user_id={self.user_id}>"


class ChatMessage(db.Model):
    """Chat history storage"""
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # "user" or "assistant"
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(64))

    user = db.relationship("User", back_populates="chat_history")

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M"),
        }


class CalorieLog(db.Model):
    """Daily calorie / food intake tracking"""
    __tablename__ = "calorie_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    log_date = db.Column(db.Date, default=date.today, index=True)
    meal_type = db.Column(db.String(30))  # breakfast, lunch, dinner, snack
    food_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.String(50))
    calories = db.Column(db.Float)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="calorie_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "meal_type": self.meal_type,
            "food_name": self.food_name,
            "quantity": self.quantity,
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "log_date": self.log_date.strftime("%Y-%m-%d"),
        }


class WaterLog(db.Model):
    """Daily water intake tracking"""
    __tablename__ = "water_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    log_date = db.Column(db.Date, default=date.today, index=True)
    amount_ml = db.Column(db.Float, nullable=False)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="water_logs")


class FamilyProfile(db.Model):
    """Family member profiles"""
    __tablename__ = "family_profiles"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50))  # spouse, child, parent, sibling, other
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    weight_kg = db.Column(db.Float)
    height_cm = db.Column(db.Float)
    dietary_preference = db.Column(db.String(50))
    fitness_goal = db.Column(db.String(50))
    allergies = db.Column(db.Text)
    medical_conditions = db.Column(db.Text)
    activity_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", back_populates="family_profiles")

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "relationship": self.relationship,
            "age": self.age,
            "gender": self.gender,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "bmi": self.bmi,
            "dietary_preference": self.dietary_preference,
            "fitness_goal": self.fitness_goal,
            "allergies": self.allergies,
            "medical_conditions": self.medical_conditions,
            "activity_level": self.activity_level,
        }

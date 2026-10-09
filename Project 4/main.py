import os
import json
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func 

# Load credentials from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'bb58e8cb6616678afde4e77b63b7c839299eeceeab55c240a0f90a1aab7fc289')

# Construct the secure connection string
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database = os.getenv('DB_NAME')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{user}:{password}@{host}/{database}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

# Initialize the database
db = SQLAlchemy(app)

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(45), unique=True, nullable=False) 
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False) 
    create_time = db.Column(db.DateTime, server_default=func.now()) 

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

def check_login(email_input, password_input):
    user = User.query.filter_by(email=email_input).first()
    if user and user.check_password(password_input):
        return True
    return False

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == '' or password == '':
            return "Please fill out both email and password."
        
        if check_login(email, password):
            session['user_email'] = email
            return f"<html><script>alert('Login successful.'); window.location.href='{url_for('home')}';</script></html>"
        else:
            return f"<html><script>alert('Invalid email or password.'); window.location.href='{url_for('login')}';</script></html>"
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return f"<html><script>alert('User already registered.'); window.location.href='{url_for('register')}';</script></html>"
            
        new_user = User(email=email, username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return f"<html><script>alert('Registration successful! Please login.'); window.location.href='{url_for('login')}';</script></html>"
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None) 
    return redirect(url_for('dashboard'))

@app.route("/home", methods=['GET', 'POST'])
def home():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        key = request.form.get('recipe_name')
        people_str = request.form.get('people')

        if not key or not people_str:
            return "Please fill out both the recipe name and number of people."

        # GENERATIVE AI INTEGRATION
        # We instruct Gemini to act as a recipe calculator and return only JSON
        prompt = f"""
        You are an expert Indian chef. 
        Provide a list of grocery ingredients to make '{key}' for {people_str} people.
        If the dish is a generic Indian everyday term like 'sabji', 'dal bhat', or 'khichdi', understand the cultural context and provide standard authentic ingredients.
        Output ONLY a raw JSON array of strings. Do not use markdown blocks (like ```json), do not include any other conversational text.
        Format example: ["1.0 cup basmati rice", "0.5 cup moong dal", "2.0 tbsp ghee", "1.0 tsp turmeric"]
        """

        try:
            # Use gemini-2.5-flash as it is the current supported Flash model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Force the AI to return strict JSON data
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Convert the guaranteed JSON string directly into a Python list
            ingredients = json.loads(response.text)
            
            if not ingredients:
                return render_template('home.html', ingredients=["Could not calculate ingredients."])
                
            return render_template('home.html', ingredients=ingredients)

        except Exception as e:
            # Fallback if the AI fails
            print(f"\n--- GENERATIVE AI ERROR ---\n{e}\n---------------------------\n")
            return render_template('home.html', ingredients=["Error generating recipe. Please try again."])

    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)

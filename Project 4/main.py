import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func # Add this import at the top for auto-timestamps

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

# REMOVED the duplicate app = Flask(__name__) that was here!

class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    # 1. Add the missing username column
    username = db.Column(db.String(45), unique=True, nullable=False) 
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False) 
    # 2. Add the create_time column to fully match your MySQL schema
    create_time = db.Column(db.DateTime, server_default=func.now()) 

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

def check_login(email_input, password_input):
    # Renamed the variable to 'user' so it doesn't overwrite your 'email_input' string
    user = User.query.filter_by(email=email_input).first()

    if user and user.check_password(password_input):
        return True
    return False

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# ADDED methods=['GET', 'POST'] so the form can actually submit
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == '' or password == '':
            return "Please fill out both email and password."
        
        if check_login(email, password):
            # FIXED: Use JS to alert AND redirect in the same HTML string
            session['user_email'] = email
            return f"<html><script>alert('Login successful.'); window.location.href='{url_for('home')}';</script></html>"
        else:
            return f"<html><script>alert('Invalid email or password.'); window.location.href='{url_for('login')}';</script></html>"
            
    # Added GET return so the page loads when you just visit /login
    return render_template('login.html')

# ADDED methods and logic to actually save users to the database
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return f"<html><script>alert('User already registered.'); window.location.href='{url_for('register')}';</script></html>"
            
        # Create new user and save to DB securely
        new_user = User(email=email, username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return f"<html><script>alert('Registration successful! Please login.'); window.location.href='{url_for('login')}';</script></html>"
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    # ADD THIS LINE: Remove the user from the session
    session.pop('user_email', None) 
    
    return redirect(url_for('dashboard'))


@app.route("/home", methods=['GET', 'POST'])
def home():
    # 1. Protect the route
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        key = request.form.get('recipe_name')
        people_str = request.form.get('people')

        if not key or not people_str:
            return "Please fill out both the recipe name and number of people."

        # 2. Call the external API (Ask for BOTH recipe info and filled ingredients)
        api_key = os.getenv('SPOONACULAR_API_KEY')
        url = f"https://api.spoonacular.com/recipes/complexSearch?query={key}&cuisine=Indian&addRecipeInformation=true&fillIngredients=true&apiKey={api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
        except Exception as e:
            return f"Error contacting the recipe API: {e}"

        # 3. Handle empty results
        if not data.get('results'):
            return render_template('home.html', ingredients=None)

        # 4. Extract data and scale ingredients (Bulletproof method)
        recipe = data['results'][0]
        
        # Try to find ingredients in 'extendedIngredients' first
        fetched_ingredients = recipe.get('extendedIngredients', [])
        
        # If it's empty, combine Spoonacular's 'used' and 'missed' ingredient lists instead
        if not fetched_ingredients:
            used = recipe.get('usedIngredients', [])
            missed = recipe.get('missedIngredients', [])
            fetched_ingredients = used + missed
            
        # If it is STILL empty, print the raw API response to the terminal so we can debug it
        if not fetched_ingredients:
            print("\n--- RAW API RESPONSE FOR", key.upper(), "---")
            print(recipe)
            print("--------------------------------------\n")
            return render_template('home.html', ingredients=["No ingredient data available for this recipe."])

        # 5. Math and formatting
        base_servings = recipe.get('servings', 1) 
        target_people = int(people_str)
        
        lines = []
        for item in fetched_ingredients:
            # Safely grab the amount, default to 1 if the API forgot to include it
            amount = item.get('amount', 1) * (target_people / base_servings)
            
            if amount.is_integer():
                amount = int(amount)
            else:
                amount = round(amount, 2)
                
            ingredient_name = f"{item.get('unit', '')} {item.get('name', 'Unknown item')}".strip()
            lines.append(f"{amount} {ingredient_name}")

        return render_template('home.html', ingredients=lines)

    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)

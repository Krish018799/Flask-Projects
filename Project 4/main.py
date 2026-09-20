from flask import Flask, render_template, url_for, redirect, request

app = Flask(__name__)

recipies = {
    "Tea": ["cup water", "cup milk", "tsp tea powder", "tsp sugar", "inch ginger"],
    "Coffee": ["cup water", "cup milk", "tsp coffee powder", "tsp sugar"],
    "Paneer Butter Masala": ["g paneer", "tbsp butter", "medium tomato", "large onion", "pcs cashew", "tbsp cream", "tbsp garam masala", "tbsp kasuri methi"]
}

# base quantity for 2 peoples order is same as above
quantities = {
    "Tea": [1, 1, 2, 2, 1],
    "Coffee": [1, 1, 2, 2],
    "Paneer Butter Masala": [200, 2, 3, 1, 10, 2, 1, 1]
}

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/logout')
def logout():
    return redirect(url_for('dashboard'))


@app.route("/recipie", methods=['GET', 'POST'])
def recipie():
    if request.method == 'POST':
        # 1. Match the name attributes from your home.html exactly
        key = request.form.get('recipe_name')
        people_str = request.form.get('people')

        if not key or not people_str:
            return "Please fill out both the recipe name and number of people."

        key = key.title()
        ingredients = recipies.get(key)

        if not ingredients:
            # If recipe isn't found, reload the page with no ingredients
            return render_template('home.html', ingredients=None)

        people = int(people_str)
        quantity = []

        for i in quantities[key]:
            amount = i * (people / 2)
            if amount.is_integer():
                amount = int(amount)
            quantity.append(amount)

        # 2. Build the final strings (e.g., "400 g paneer")
        lines = []
        for i in range(len(ingredients)):
            lines.append(f"{quantity[i]} {ingredients[i]}")

        # 3. Pass the 'lines' list to your Jinja template as 'ingredients'
        return render_template('home.html', ingredients=lines)

    # If the user visits the page via GET request
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)

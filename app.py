from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configure the database (SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here'

# Initialize the database
db = SQLAlchemy(app)

# Property Model
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)

# User Model for signup and login
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Function to populate the database with sample properties
def insert_sample_data():
    if Property.query.count() == 0:  # Only insert if database is empty
        sample_properties = [
            Property(name="Modern Villa", price=500000, location="Cork", type="Villa"),
            Property(name="Cozy Apartment", price=300000, location="Galway", type="Apartment"),
            Property(name="Luxury Mansion", price=1000000, location="Dublin 07", type="Mansion"),
            Property(name="Flat", price=200000, location="Dublin 1", type="Flat"),
            Property(name="House", price=400000, location="Dublin 15", type="House"),
        ]
        db.session.add_all(sample_properties)
        db.session.commit()

@app.route('/')
def home():
    return render_template('index.html')  # Displays home page with buttons for signup and login

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Call classmate's API for password strength check
        response = requests.post('http://localhost:5000/check-password', json={"password": password})
        if response.status_code != 200 or response.json().get('valid') == False:
            return jsonify({"error": "Password is not strong enough. Please try again."}), 400

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return render_template('signup.html')  # Displays signup page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return render_template('welcome.html', username=username)
        else:
            return jsonify({"error": "Invalid credentials. Please try again."}), 400

    return render_template('login.html')  # Displays login page

@app.route('/recommend', methods=['POST', 'GET'])
def recommend_property():
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"error": "Request must be in JSON format"}), 400

        data = request.get_json()
        budget = data.get('budget')
        location = data.get('location')
        property_type = data.get('type')

        if not all([budget, location, property_type]):
            return jsonify({"error": "Missing required fields: budget, location, or type"}), 400

        # Filter properties from the database
        recommended_properties = Property.query.filter(
            Property.price <= budget,
            Property.location.ilike(f"%{location}%"),
            Property.type.ilike(f"%{property_type}%")
        ).all()

        # Format the response
        response = [
            {"id": prop.id, "name": prop.name, "price": prop.price, "location": prop.location, "type": prop.type}
            for prop in recommended_properties
        ]

        # Call classmate's Loan Suggestion API
        loan_response = requests.post('http://localhost:5002/get-loans', json={
            "price": budget
        })

        if loan_response.status_code == 200:
            loans = loan_response.json()
        else:
            loans = []

        return jsonify({"properties": response, "loans": loans})

    elif request.method == 'GET':
        # Fetch all properties from the database
        all_properties = Property.query.all()
        response = [
            {"id": prop.id, "name": prop.name, "price": prop.price, "location": prop.location, "type": prop.type}
            for prop in all_properties
        ]
        return jsonify(response)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist
        insert_sample_data()  # Insert sample data only if the database is empty
    app.run(debug=True)

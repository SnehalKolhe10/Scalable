from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os

# Create Flask app (AWS requires 'application' as the variable name)
application = Flask(__name__)
application.debug = True

# Use SQLite (For production, replace with RDS database)
database_path = os.path.join(os.getcwd(), 'properties.db')
application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.secret_key = 'your_secret_key_here'

# Initialize the database
db = SQLAlchemy(application)

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
    if Property.query.count() == 0:
        sample_properties = [
            Property(name="Modern Villa", price=500000, location="Cork", type="Villa"),
            Property(name="Cozy Apartment", price=300000, location="Galway", type="Apartment"),
            Property(name="Luxury Mansion", price=1000000, location="Dublin 07", type="Mansion"),
            Property(name="Flat", price=200000, location="Dublin 1", type="Flat"),
            Property(name="House", price=400000, location="Dublin 15", type="House"),
        ]
        db.session.add_all(sample_properties)
        db.session.commit()

@application.route('/')
def home():
    return render_template('index.html')

@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Call the actual password strength API
        try:
            response = requests.post(
                'http://pscapi-env.eba-c6kbzpsc.us-east-1.elasticbeanstalk.com/api/user/check',
                json={"password": password}
            )

            if response.status_code != 200:
                return render_template('signup.html', error="Error with password strength check API.")

            response_data = response.json()
            strength = response_data.get("strength", 0)
            
            if strength != 5:
                return render_template('signup.html', error="Password strength must be 5.")

            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)

            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))

        except requests.exceptions.RequestException as e:
            return render_template('signup.html', error=f"Error with API request: {str(e)}")

    return render_template('signup.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = username
            return redirect(url_for('welcome'))
        else:
            return jsonify({"error": "Invalid credentials."}), 400

    return render_template('login.html')


import requests
from bs4 import BeautifulSoup

def fetch_loans_from_html():
    url = "http://loanrecommendation-env.eba-fssmj2mu.us-east-1.elasticbeanstalk.com/all-loans"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    all_loans = []

    for scheme_div in soup.select(".mb-5"):
        scheme_name = scheme_div.find("h4").text.strip()
        rows = scheme_div.select("tbody tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                loan = {
                    "scheme": scheme_name,
                    "bank": cols[0].text.strip(),
                    "interest_rate": cols[1].text.strip(),
                    "max_loan_amount": cols[2].text.strip(),
                    "tenure": cols[3].text.strip(),
                    "monthly_emi": cols[4].text.strip(),
                    "processing_fee": cols[5].text.strip(),
                    "prepayment_penalty": cols[6].text.strip()
                }
                all_loans.append(loan)

    return all_loans

@application.route('/welcome', methods=['GET', 'POST'])
def welcome():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    properties = []

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'filter':
            budget = request.form.get('budget')
            location = request.form.get('location')
            property_type = request.form.get('type')

            try:
                budget = int(budget) if budget else None
            except ValueError:
                budget = None

            query = Property.query
            if budget:
                query = query.filter(Property.price <= budget)
            if location:
                query = query.filter(Property.location.ilike(f"%{location}%"))
            if property_type:
                query = query.filter(Property.type.ilike(f"%{property_type}%"))

            properties = query.all()

        elif action == 'show_all':
            properties = Property.query.limit(5).all()

    loans = fetch_loans_from_html()

    return render_template('welcome.html', username=username, properties=properties, loans=loans)

# @application.route('/welcome', methods=['GET', 'POST'])
# def welcome():
#     if 'user' not in session:
#         return redirect(url_for('login'))

#     username = session['user']
#     properties = []

#     if request.method == 'POST':
#         action = request.form.get('action')

#         if action == 'filter':
#             budget = request.form.get('budget')
#             location = request.form.get('location')
#             property_type = request.form.get('type')

#             # Convert budget to integer safely
#             try:
#                 budget = int(budget) if budget else None
#             except ValueError:
#                 budget = None

#             # Query filter
#             query = Property.query
#             if budget:
#                 query = query.filter(Property.price <= budget)
#             if location:
#                 query = query.filter(Property.location.ilike(f"%{location}%"))
#             if property_type:
#                 query = query.filter(Property.type.ilike(f"%{property_type}%"))

#             properties = query.all()

#         elif action == 'show_all':
#             properties = Property.query.limit(5).all()

#     return render_template('welcome.html', username=username, properties=properties)


from flask import render_template
import requests
from bs4 import BeautifulSoup

@application.route("/view_all_loans")
def view_all_loans():
    url = "http://loanrecommendation-env.eba-fssmj2mu.us-east-1.elasticbeanstalk.com/all-loans"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract each scheme's name and table rows
        schemes = []

        for scheme_div in soup.select(".mb-5"):
            scheme_name = scheme_div.find("h4").text.strip()
            rows = []
            for tr in scheme_div.select("tbody tr"):
                cells = [td.text.strip() for td in tr.find_all("td")]
                rows.append(cells)

            schemes.append({
                "name": scheme_name,
                "loans": rows
            })

        return render_template("parsed_loans.html", schemes=schemes)

    except Exception as e:
        return f"<h3>Error parsing loan data: {e}</h3>", 500
    
@application.route('/select_loan', methods=['POST'])
def select_loan():
    try:
        property_id = request.form.get('property_id')
        loan_info = request.form.get('loan_info')

        if not property_id or not loan_info:
            return "<h3>Error: Missing property ID or loan selection.</h3>", 400

        print("Raw loan_info:", loan_info)  # Debug print

        parts = loan_info.split('|')
        if len(parts) != 4:
            return f"<h3>Unexpected loan info format: {loan_info}</h3>", 400

        bank, max_loan, interest_rate, tenure = parts

        # Optional: Save to DB here

        return render_template("purchase_success.html")

    except Exception as e:
        print("Error in /select_loan route:", e)
        return f"<h3>Server Error: {e}</h3>", 500
    
@application.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@application.route('/recommend', methods=['GET'])
def recommend_properties():
    # Insert sample data if no properties exist
    if Property.query.count() == 0:
        sample_properties = [
            Property(name="Modern Villa", price=500000, location="Cork", type="Villa"),
            Property(name="Cozy Apartment", price=300000, location="Galway", type="Apartment"),
            Property(name="Luxury Mansion", price=1000000, location="Dublin 07", type="Mansion"),
            Property(name="Flat", price=200000, location="Dublin 1", type="Flat"),
            Property(name="House", price=400000, location="Dublin 15", type="House"),
        ]
        db.session.add_all(sample_properties)
        db.session.commit()

    # Retrieve all properties
    properties = Property.query.all()

    # Prepare the list of properties to return as a JSON response
    properties_list = []
    for property in properties:
        properties_list.append({
            'name': property.name,
            'price': property.price,
            'location': property.location,
            'type': property.type
        })

    # Return the properties in a JSON response
    return jsonify(properties_list)


if __name__ == '__main__':
    with application.app_context():
        db.create_all()
    application.run(host='0.0.0.0', port=8080)

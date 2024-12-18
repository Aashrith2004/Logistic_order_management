import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize the Flask application
app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'  # Use SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable track modifications
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the Order model
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)  # Order ID
    customer_id = db.Column(db.Integer, nullable=False)  # Customer ID
    shipping_address = db.Column(db.String(255), nullable=False)  # Shipping Address
    consignment_weight = db.Column(db.Float, nullable=False)  # Weight of the consignment
    shipping_cost = db.Column(db.Float, nullable=False)  # Shipping cost
    status = db.Column(db.String(50), default='Pending')  # Order status
    pincode = db.Column(db.String(6), nullable=False)  # Pincode extracted from shipping address
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())  # Created timestamp
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())  # Updated timestamp

    def __repr__(self):
        return f'<Order {self.id}>'

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Function to calculate shipping cost
def calculate_shipping_cost(weight):
    base_cost = 5.0  # Base cost for shipping
    cost_per_kg = 2.0  # Cost per kilogram
    return base_cost + (cost_per_kg * weight)

# Function to verify pincode using an external API
def verify_pincode(pincode, country_code='in'):
    if not isinstance(pincode, str) or len(pincode) != 6 or not pincode.isdigit():
        return False  # Invalid pincode format

    # URL for Zippopotam.us API (or any other pincode verification service)
    url = f'https://api.zippopotam.us/{country_code}/{pincode}'
    try:
        response = requests.get(url)
        # Check if the response status code is OK (200)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.RequestException:
        return False

# Route to verify a pincode (GET)
@app.route('/api/shipping/verify_pincode/<int:pincode>', methods=['GET'])
def verify_pincode_route(pincode):
    if verify_pincode(str(pincode)):  # Ensure pincode is passed as string
        return jsonify({'message': 'Pincode is valid'}), 200
    return jsonify({'message': 'Invalid pincode'}), 400

# Route to calculate shipping cost (POST)
@app.route('/api/shipping/calculate', methods=['POST'])
def calculate_shipping():
    data = request.json  # Get the JSON data from the request
    weight = data.get('weight')
    if weight is None or weight <= 0:
        return jsonify({'message': 'Invalid weight provided'}), 400

    shipping_cost = calculate_shipping_cost(weight)
    return jsonify({'shipping_cost': shipping_cost}), 200

# Create an order (POST)
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    address = data['shipping_address']
    pincode = str(address.split()[-1])  # Extract pincode (assuming it's at the end of the address)

    if not verify_pincode(pincode):
        return jsonify({'message': 'Invalid pincode'}), 400

    new_order = Order(
        customer_id=data['customer_id'],
        shipping_address=address,
        consignment_weight=data['consignment_weight'],
        shipping_cost=calculate_shipping_cost(data['consignment_weight']),
        pincode=pincode
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Order created successfully', 'order_id': new_order.id}), 201
# Delete an order (DELETE)
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = Order.query.get(order_id)  # Query the order by ID
    if order:
        db.session.delete(order)  # Delete the order
        db.session.commit()  # Commit the transaction to save the change
        return jsonify({'message': f'Order {order_id} deleted successfully'}), 200
    return jsonify({'message': 'Order not found'}), 404

# Retrieve all orders (GET)
@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()  # Query all orders
    return jsonify([{
        'id': order.id,
        'customer_id': order.customer_id,
        'shipping_address': order.shipping_address,
        'consignment_weight': order.consignment_weight,
        'shipping_cost': order.shipping_cost,
        'status': order.status,
        'pincode': order.pincode,
        'created_at': order.created_at,
        'updated_at': order.updated_at
    } for order in orders]), 200

# Retrieve a specific order (GET)
@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get(order_id)  # Query the order by ID
    if order:
        return jsonify({
            'id': order.id,
            'customer_id': order.customer_id,
            'shipping_address': order.shipping_address,
            'consignment_weight': order.consignment_weight,
            'shipping_cost': order.shipping_cost,
            'status': order.status,
            'pincode': order.pincode,
            'created_at': order.created_at,
            'updated_at': order.updated_at
        }), 200
    return jsonify({'message': 'Order not found'}), 404

# Define a route for the root URL, serving HTML
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

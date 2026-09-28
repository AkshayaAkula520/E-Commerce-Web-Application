# E-Commerce Web Application

A full-stack E-Commerce Web Application built using Python Flask and MySQL.

## Features

- User Registration and Login
- Role-Based Access Control
- Admin Dashboard
- Product Catalog
- Add Products
- Edit Products
- Delete Products
- Shopping Cart
- Checkout
- Order History
- Admin Order Management
- REST APIs for Products and Orders
- MySQL Database Integration
- Responsive Web Interface

## Technologies Used

- Python
- Flask
- MySQL
- HTML
- CSS
- JavaScript
- Flask-MySQLdb
- Flask-CORS
- Werkzeug

## User Roles

### User
- Register and login
- View products
- Add products to cart
- Checkout
- View order history

### Admin
- Manage products
- Add, edit and delete products
- View customer orders
- Update order status
- Access product and order APIs

## Database

The application uses MySQL with the following tables:

- users
- products
- cart
- orders
- order_items

## How to Run

1. Create the MySQL database.
2. Create the required tables.
3. Create a Python virtual environment.
4. Install dependencies:

```bash
pip install -r requirements.txt
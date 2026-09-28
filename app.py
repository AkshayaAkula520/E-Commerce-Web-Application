from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.secret_key = 'ecommerce_secret_key'

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = 'ecommerce_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('products'))
    return redirect(url_for('login'))


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        cursor = mysql.connection.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_password, 'user')
            )
            mysql.connection.commit()
            cursor.close()

            return redirect(url_for('login'))

        except Exception:
            cursor.close()
            return "Email already exists!"

    return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']

            return redirect(url_for('products'))

        return "Invalid email or password!"

    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Temporary products page
@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()

    return render_template('products.html', products=products)
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor()

    # Check if product is already in cart
    cursor.execute(
        "SELECT * FROM cart WHERE user_id = %s AND product_id = %s",
        (user_id, product_id)
    )

    existing_item = cursor.fetchone()

    if existing_item:
        cursor.execute(
            "UPDATE cart SET quantity = quantity + 1 WHERE id = %s",
            (existing_item['id'],)
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
            (user_id, product_id, 1)
        )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('cart'))
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT cart.id, products.name, products.price,
               cart.quantity,
               (products.price * cart.quantity) AS subtotal
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))

    cart_items = cursor.fetchall()
    cursor.close()

    total = sum(item['subtotal'] for item in cart_items)

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total=total
    )
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    # Get cart items
    cursor.execute("""
        SELECT cart.product_id, cart.quantity, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))

    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        return "Your cart is empty!"

    total = sum(item['price'] * item['quantity'] for item in cart_items)

    if request.method == 'POST':

        # Create order
        cursor.execute("""
            INSERT INTO orders (user_id, total_amount, status)
            VALUES (%s, %s, %s)
        """, (user_id, total, 'Pending'))

        order_id = cursor.lastrowid

        # Add products to order_items
        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (
                order_id,
                item['product_id'],
                item['quantity'],
                item['price']
            ))

        # Clear cart
        cursor.execute(
            "DELETE FROM cart WHERE user_id = %s",
            (user_id,)
        )

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('orders'))

    cursor.close()

    return render_template(
        'checkout.html',
        cart_items=cart_items,
        total=total
    )
@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id, total_amount, status, order_date
        FROM orders
        WHERE user_id = %s
        ORDER BY order_date DESC
    """, (user_id,))

    orders_list = cursor.fetchall()
    cursor.close()

    return render_template('orders.html', orders=orders_list)
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return "Access Denied! Admins only."

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.execute("""
        SELECT orders.id, users.name, orders.total_amount,
               orders.status, orders.order_date
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.order_date DESC
    """)

    orders = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin.html',
        products=products,
        orders=orders
    )
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return "Access Denied! Admins only."

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image']
        stock = request.form['stock']

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO products
            (name, description, price, image, stock)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, description, price, image, stock))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('admin'))

    return render_template('add_product.html')
@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return "Access Denied! Admins only."

    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image']
        stock = request.form['stock']

        cursor.execute("""
            UPDATE products
            SET name=%s, description=%s, price=%s,
                image=%s, stock=%s
            WHERE id=%s
        """, (name, description, price, image, stock, product_id))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('admin'))

    cursor.execute(
        "SELECT * FROM products WHERE id=%s",
        (product_id,)
    )

    product = cursor.fetchone()
    cursor.close()

    return render_template(
        'edit_product.html',
        product=product
    )
@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return "Access Denied! Admins only."

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id=%s",
        (product_id,)
    )

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))
@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        return "Access Denied! Admins only."

    status = request.form['status']

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = %s
        WHERE id = %s
    """, (status, order_id))

    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))
# =========================
# PRODUCT APIs
# =========================

@app.route('/api/products', methods=['GET'])
def api_products():
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.close()

    return jsonify(products)


@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_product(product_id):
    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM products WHERE id = %s",
        (product_id,)
    )

    product = cursor.fetchone()
    cursor.close()

    if not product:
        return jsonify({"message": "Product not found"}), 404

    return jsonify(product)


@app.route('/api/products', methods=['POST'])
def api_add_product():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"message": "Admin access required"}), 403

    data = request.get_json()

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO products
        (name, description, price, image, stock)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        data['name'],
        data.get('description', ''),
        data['price'],
        data.get('image', ''),
        data.get('stock', 0)
    ))

    mysql.connection.commit()

    product_id = cursor.lastrowid
    cursor.close()

    return jsonify({
        "message": "Product added successfully",
        "product_id": product_id
    }), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"message": "Admin access required"}), 403

    data = request.get_json()

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE products
        SET name=%s,
            description=%s,
            price=%s,
            image=%s,
            stock=%s
        WHERE id=%s
    """, (
        data['name'],
        data.get('description', ''),
        data['price'],
        data.get('image', ''),
        data.get('stock', 0),
        product_id
    ))

    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "message": "Product updated successfully"
    })


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"message": "Admin access required"}), 403

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM products WHERE id=%s",
        (product_id,)
    )

    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "message": "Product deleted successfully"
    })


# =========================
# ORDER APIs
# =========================

@app.route('/api/orders', methods=['GET'])
def api_orders():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"message": "Admin access required"}), 403

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT orders.id,
               users.name,
               orders.total_amount,
               orders.status,
               orders.order_date
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.order_date DESC
    """)

    orders = cursor.fetchall()

    cursor.close()

    return jsonify(orders)


@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def api_update_order(order_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"message": "Admin access required"}), 403

    data = request.get_json()

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET status=%s
        WHERE id=%s
    """, (
        data['status'],
        order_id
    ))

    mysql.connection.commit()

    cursor.close()

    return jsonify({
        "message": "Order status updated successfully"
    })
if __name__ == '__main__':
    app.run(debug=True)
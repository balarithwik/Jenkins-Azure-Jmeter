from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "retaildb")
DB_USER = os.getenv("DB_USER", "retailuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "RetailPass@123")


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def wait_for_db():
    for _ in range(30):
        try:
            conn = get_connection()
            conn.close()
            print("Database connected successfully")
            return
        except Exception as e:
            print(f"Waiting for DB... {e}")
            time.sleep(5)
    raise Exception("Could not connect to database after retries")


def generate_order_number(order_id):
    today = datetime.now().strftime("%Y%m%d")
    return f"ORD-{today}-{order_id:06d}"


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"status": "UP"}), 200
    except Exception as e:
        return jsonify({"status": "DOWN", "error": str(e)}), 500


@app.route("/products", methods=["GET"])
def get_products():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, category, price, stock_qty FROM products ORDER BY id")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(products), 200


@app.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()

    customer_name = data.get("customer_name")
    customer_email = data.get("customer_email")
    items = data.get("items", [])

    if not customer_name or not customer_email or not items:
        return jsonify({"error": "customer_name, customer_email and items are required"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        total_amount = 0.0

        for item in items:
            product_id = item.get("product_id")
            quantity = int(item.get("quantity", 1))

            cursor.execute(
                "SELECT id, name, price, stock_qty FROM products WHERE id = %s",
                (product_id,)
            )
            product = cursor.fetchone()

            if not product:
                conn.rollback()
                return jsonify({"error": f"Product {product_id} not found"}), 404

            if product["stock_qty"] < quantity:
                conn.rollback()
                return jsonify({"error": f"Insufficient stock for product {product_id}"}), 400

            total_amount += float(product["price"]) * quantity

        cursor.execute("""
            INSERT INTO orders (order_number, customer_name, customer_email, total_amount, status)
            VALUES (%s, %s, %s, %s, %s)
        """, ("TEMP", customer_name, customer_email, total_amount, "CREATED"))

        order_id = cursor.lastrowid
        order_number = generate_order_number(order_id)

        cursor.execute("""
            UPDATE orders
            SET order_number = %s
            WHERE id = %s
        """, (order_number, order_id))

        for item in items:
            product_id = item.get("product_id")
            quantity = int(item.get("quantity", 1))

            cursor.execute("SELECT price FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            unit_price = float(product["price"])

            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, product_id, quantity, unit_price))

            cursor.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
            """, (quantity, product_id))

        conn.commit()

        return jsonify({
            "message": "Order created successfully",
            "order_id": order_id,
            "order_number": order_number,
            "total_amount": total_amount,
            "status": "CREATED"
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, order_number, customer_name, customer_email, total_amount, status, created_at
        FROM orders
        WHERE id = %s
    """, (order_id,))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        conn.close()
        return jsonify({"error": "Order not found"}), 404

    cursor.execute("""
        SELECT oi.id, oi.product_id, p.name AS product_name, oi.quantity, oi.unit_price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    order["items"] = items
    return jsonify(order), 200


if __name__ == "__main__":
    wait_for_db()
    app.run(host="0.0.0.0", port=5000)
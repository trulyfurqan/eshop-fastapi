from flask import Flask, request, jsonify, g
from psycopg2 import pool, sql
import threading
import time
import itertools

app = Flask(__name__)

db_pool = pool.SimpleConnectionPool(1, 10, user='user', password='password', host='localhost', port='5432', database='inventory_db')

RATE_LIMIT = 100
LEAK_RATE = 1
bucket_lock = threading.Lock()
buckets = {}

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)

def rate_limiter(ip):
    global buckets
    current_time = time.time()
    with bucket_lock:
        if ip not in buckets:
            buckets[ip] = {'tokens': RATE_LIMIT, 'last': current_time}
        else:
            elapsed = current_time - buckets[ip]['last']
            buckets[ip]['tokens'] = min(RATE_LIMIT, buckets[ip]['tokens'] + elapsed * LEAK_RATE)
            buckets[ip]['last'] = current_time
        if buckets[ip]['tokens'] < 1:
            return False
        buckets[ip]['tokens'] -= 1
        return True

@app.before_request
def limit_remote_addr():
    ip = request.remote_addr
    if not rate_limiter(ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

@app.route('/products', methods=['GET'])
def get_products():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.name, p.quantity, c.name as category_name, s.name as supplier_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        JOIN suppliers s ON p.supplier_id = s.id
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    
    products = cur.fetchall()
    release_db_connection(conn)

    product_list = [{'id': row[0], 'name': row[1], 'quantity': row[2], 'category_name': row[3], 'supplier_name': row[4]} for row in products]
    return jsonify(product_list)

@app.route('/products/<int:product_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_product(product_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("""
            SELECT p.id, p.name, p.quantity, c.name as category_name, s.name as supplier_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.id = %s
        """, (product_id,))
        product = cur.fetchone()
        release_db_connection(conn)

        if product is None:
            return jsonify({'error': 'Product not found'}), 404

        product_data = {'id': product[0], 'name': product[1], 'quantity': product[2], 'category_name': product[3], 'supplier_name': product[4]}
        return jsonify(product_data)

    elif request.method == 'PUT':
        update_data = request.get_json()
        name = update_data.get('name')
        quantity = update_data.get('quantity')

        cur.execute("""
            UPDATE products SET name = %s, quantity = %s WHERE id = %s
        """, (name, quantity, product_id))
        conn.commit()
        release_db_connection(conn)
        return jsonify({'status': 'Product updated'})

    elif request.method == 'DELETE':
        cur.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        release_db_connection(conn)
        return jsonify({'status': 'Product deleted'})

@app.route('/suppliers', methods=['GET'])
def get_suppliers():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.id, s.name, COUNT(p.id) as product_count
        FROM suppliers s
        LEFT JOIN products p ON s.id = p.supplier_id
        GROUP BY s.id, s.name
    """)
    suppliers = cur.fetchall()
    release_db_connection(conn)

    supplier_list = [{'id': row[0], 'name': row[1], 'product_count': row[2]} for row in suppliers]
    return jsonify(supplier_list)

@app.route('/products/bulk', methods=['POST'])
def add_products_bulk():
    products = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()

    for product in products:
        cur.execute('INSERT INTO products (name, quantity, category_id, supplier_id) VALUES (%s, %s, %s, %s)', 
                    (product['name'], product['quantity'], product['category_id'], product['supplier_id']))

    conn.commit()
    release_db_connection(conn)
    return jsonify({'status': 'Bulk products added'}), 201

@app.route('/product-quantities', methods=['GET'])
def product_quantities():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, quantity FROM products")
    products = cur.fetchall()
    release_db_connection(conn)

    product_quantities = {}
    for product in products:
        product_quantities[product[0]] = product[1]

    sorted_products = sorted(product_quantities.items(), key=lambda x: x[1])
    result = []
    for i, prod1 in enumerate(sorted_products):
        for prod2 in sorted_products[i+1:]:
            if prod1[1] > prod2[1]:
                result.append(prod1)

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)

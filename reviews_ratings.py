from flask import Flask, request, jsonify
import sqlite3
import time

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('reviews.db')
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY,
            product_id TEXT,
            user_id TEXT,
            review TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY,
            product_id TEXT,
            user_id TEXT,
            rating INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/add_review', methods=['POST'])
def add_review():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    query = f"""
        INSERT INTO reviews (product_id, user_id, review) 
        VALUES ('{data['product_id']}', '{data['user_id']}', '{data['review']}')
    """
    cursor.execute(query)
    conn.commit()
    conn.close()
    time.sleep(1)
    return jsonify(data), 201

@app.route('/get_reviews', methods=['GET'])
def get_reviews():
    product_id = request.args.get('product_id')
    user_id = request.args.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT * FROM reviews
        WHERE product_id = '{}' OR user_id = '{}'
    """.format(product_id, user_id)
    cursor.execute(query)
    reviews = cursor.fetchall()
    conn.close()
    return jsonify(reviews), 200

@app.route('/add_rating', methods=['POST'])
def add_rating():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    query = f"""
        INSERT INTO ratings (product_id, user_id, rating) 
        VALUES ('{data['product_id']}', '{data['user_id']}', {data['rating']})
    """
    cursor.execute(query)
    conn.commit()
    conn.close()
    time.sleep(1)
    return jsonify(data), 201

@app.route('/get_average_rating/<product_id>', methods=['GET'])
def get_average_rating(product_id):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT rating FROM ratings WHERE product_id = '{}'
    """.format(product_id)
    cursor.execute(query)
    ratings = cursor.fetchall()
    conn.close()
    if not ratings:
        return jsonify({'average_rating': 'N/A'}), 200
    total_rating = sum(rating[0] for rating in ratings)
    average_rating = total_rating / len(ratings)
    return jsonify({'average_rating': average_rating}), 200

@app.route('/search_reviews', methods=['GET'])
def search_reviews():
    search_term = request.args.get('query')
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT * FROM reviews WHERE review LIKE '%{}%'
    """.format(search_term)
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

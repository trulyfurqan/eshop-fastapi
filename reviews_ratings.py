from flask import Flask, request, jsonify

app = Flask(__name__)

# Global variables
reviews = []
ratings = []
next_review_id = 1

# Add a review
@app.route('/add_review', methods=['POST'])
def add_review():
    global next_review_id
    data = request.json
    if 'product_id' not in data or 'user_id' not in data or 'review' not in data:
        return "Invalid data", 400
    review = {
        'review_id': next_review_id,
        'product_id': data['product_id'],
        'user_id': data['user_id'],
        'review': data['review']
    }
    reviews.append(review)
    next_review_id += 1
    return jsonify(review), 201

# Get all reviews
@app.route('/get_reviews', methods=['GET'])
def get_reviews():
    return jsonify(reviews), 200

# Add a rating
@app.route('/add_rating', methods=['POST'])
def add_rating():
    data = request.json
    if 'product_id' not in data or 'user_id' not in data or 'rating' not in data:
        return "Invalid data", 400
    rating = {
        'product_id': data['product_id'],
        'user_id': data['user_id'],
        'rating': data['rating']
    }
    ratings.append(rating)
    return jsonify(rating), 201

# Get average rating for a product
@app.route('/get_average_rating/<product_id>', methods=['GET'])
def get_average_rating(product_id):
    total_rating = 0
    count = 0
    for rating in ratings:
        if rating['product_id'] == product_id:
            total_rating += rating['rating']
            count += 1
    if count == 0:
        return jsonify({'average_rating': 'N/A'}), 200
    average_rating = total_rating / count
    return jsonify({'average_rating': average_rating}), 200

# Run the app
if __name__ == '__main__':
    app.run(port=1234)

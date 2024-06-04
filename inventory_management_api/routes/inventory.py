from flask import Blueprint, request, jsonify
from cache import get_cache
from db import get_shards, get_shard, execute_query
from rate_limiter import limiter
from recommendation import recommendation_engine

inventory_bp = Blueprint("inventory", __name__)
shards = get_shards()
cache = get_cache()


@inventory_bp.route("/", methods=["GET"])
@limiter.limit("10 per minute")
def get_inventory():
    try:
        product_id = request.args.get("product_id")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))

        offset = (page - 1) * per_page
        cache_key = f"inventory_{product_id}_{page}_{per_page}"
        cached_inventory = cache.get(cache_key)

        if cached_inventory:
            return jsonify({"inventory": cached_inventory.decode("utf-8")})

        shard = get_shard(int(product_id), shards)
        query = """
            SELECT 
                i.product_id, i.quantity, p.name AS product_name, c.name AS category_name
            FROM 
                inventory i
            JOIN 
                products p ON i.product_id = p.id
            JOIN 
                categories c ON p.category_id = c.id
            WHERE 
                i.product_id = %s
            LIMIT %s OFFSET %s
        """
        cursor = execute_query(shard, query, (product_id, per_page, offset))
        inventory = cursor.fetchall()

        if inventory:
            cache.setex(cache_key, 300, str(inventory))  # Cache for 5 minutes
            return jsonify({"inventory": inventory})

        return jsonify({"error": "Product not found"}), 404
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@inventory_bp.route("/add", methods=["POST"])
@limiter.limit("5 per minute")
def add_inventory():
    try:
        data = request.json
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not product_id or not quantity:
            return jsonify({"error": "Invalid data"}), 400

        shard = get_shard(int(product_id), shards)
        query = "INSERT INTO inventory (product_id, quantity) VALUES (%s, %s)"
        cursor = execute_query(shard, query, (product_id, quantity))
        shard.commit()

        return jsonify({"message": "Inventory added successfully"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@inventory_bp.route("/update", methods=["POST"])
@limiter.limit("5 per minute")
def update_inventory():
    try:
        data = request.json
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if not product_id or not quantity:
            return jsonify({"error": "Invalid data"}), 400

        shard = get_shard(int(product_id), shards)
        query = "UPDATE inventory SET quantity = %s WHERE product_id = %s"
        cursor = execute_query(shard, query, (quantity, product_id))
        shard.commit()

        # Invalidate cache after update
        cache.delete(f"inventory_{product_id}")

        return jsonify({"message": "Inventory updated successfully"}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@inventory_bp.route("/delete", methods=["POST"])
@limiter.limit("5 per minute")
def delete_inventory():
    try:
        data = request.json
        product_id = data.get("product_id")

        if not product_id:
            return jsonify({"error": "Invalid data"}), 400

        shard = get_shard(int(product_id), shards)
        query = "DELETE FROM inventory WHERE product_id = %s"
        cursor = execute_query(shard, query, (product_id,))
        shard.commit()

        # Invalidate cache after delete
        cache.delete(f"inventory_{product_id}")

        # Confirm deletion
        if cursor.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404

        return jsonify({"message": "Inventory deleted successfully"}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@inventory_bp.route("/recommendations", methods=["GET"])
@limiter.limit("10 per minute")
def get_recommendations():
    try:
        user_id = request.args.get("user_id")
        num_recommendations = int(request.args.get("num_recommendations", 5))

        recommendations = recommendation_engine.get_recommendations(
            user_id, num_recommendations
        )
        return jsonify({"recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

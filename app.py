# app.py
from flask import Flask, request, jsonify
from datetime import datetime
from models import get_transaction, create_transaction
from worker import start_worker

app = Flask(__name__)

# Start background worker
start_worker(app)

@app.route("/")
def health():
    return jsonify({
        "status": "HEALTHY",
        "current_time": datetime.utcnow().isoformat() + "Z"
    })

@app.post("/v1/webhooks/transactions")
def webhook():
    data = request.get_json(force=True)

    # Validate
    required = ["transaction_id", "source_account", "destination_account", "amount", "currency"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    tx = get_transaction(data["transaction_id"])
    if tx:
        # Already exists (idempotency)
        return jsonify({"message": "Webhook received (duplicate ignored)"}), 202

    # Create new transaction
    create_transaction({
        "transaction_id": data["transaction_id"],
        "source_account": data["source_account"],
        "destination_account": data["destination_account"],
        "amount": data["amount"],
        "currency": data["currency"],
        "status": "PROCESSING",
        "created_at": datetime.utcnow(),
        "processed_at": None,
        "locked_at": None,
    })

    return jsonify({"message": "Webhook received"}), 202

@app.get("/v1/transactions/<transaction_id>")
def get_transaction_route(transaction_id):
    tx = get_transaction(transaction_id)
    if not tx:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "transaction_id": tx["transaction_id"],
        "source_account": tx["source_account"],
        "destination_account": tx["destination_account"],
        "amount": tx["amount"],
        "currency": tx["currency"],
        "status": tx["status"],
        "created_at": tx["created_at"].isoformat() + "Z" if tx.get("created_at") else None,
        "processed_at": tx["processed_at"].isoformat() + "Z" if tx.get("processed_at") else None
    })

if __name__ == "__main__":
    app.run(port=3000, debug=True)

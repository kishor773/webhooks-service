# models.py
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError


# Configure MongoDB connection from environment with sensible defaults
# Default to local MongoDB so the app runs without Atlas/DNS
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://kishordeshpande310_db_user:4P1zlLhRKVeIHB8z@webhooks.iyql0jq.mongodb.net/?retryWrites=true&w=majority&appName=webhooks")
MONGO_DB = os.getenv("MONGO_DB", "webhooks")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
transactions = db["transactions"]

# Ensure an index on transaction_id for idempotency and fast lookups
transactions.create_index("transaction_id", unique=True)


def get_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
    return transactions.find_one({"transaction_id": transaction_id})


def create_transaction(doc: Dict[str, Any]) -> None:
    try:
        transactions.insert_one(doc)
    except DuplicateKeyError:
        # Ignore duplicates to preserve idempotent behavior
        pass


def find_and_claim_one(lock_timeout_seconds: int) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow()
    stale_before = now - timedelta(seconds=lock_timeout_seconds)

    query = {
        "$or": [
            {"status": "PROCESSING"},
            {"status": "IN_PROGRESS", "locked_at": {"$lt": stale_before}},
        ]
    }

    update = {"$set": {"status": "IN_PROGRESS", "locked_at": now}}

    # Atomically find one eligible doc and claim it
    claimed = transactions.find_one_and_update(
        query,
        update,
        return_document=ReturnDocument.AFTER,
    )
    return claimed


def mark_processed(transaction_id: str) -> None:
    transactions.update_one(
        {"transaction_id": transaction_id},
        {"$set": {"status": "PROCESSED", "processed_at": datetime.utcnow(), "locked_at": None}},
    )

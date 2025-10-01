from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio

from models import transactions


app = FastAPI()


async def process_transaction(transaction_id: str) -> None:
    """Simulate external processing with 30 sec delay and update MongoDB."""
    await asyncio.sleep(30)
    transactions.update_one(
        {"transaction_id": transaction_id},
        {
            "$set": {
                "status": "PROCESSED",
                "processed_at": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


@app.get("/")
async def health_check():
    return {
        "status": "HEALTHY",
        "current_time": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/v1/webhooks/transactions")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()

    required = [
        "transaction_id",
        "source_account",
        "destination_account",
        "amount",
        "currency",
    ]
    if not all(k in body for k in required):
        return JSONResponse(status_code=400, content={"error": "Missing fields"})

    transaction_id = body["transaction_id"]
    existing_txn = transactions.find_one({"transaction_id": transaction_id})

    if not existing_txn:
        doc = {
            "transaction_id": body["transaction_id"],
            "source_account": body["source_account"],
            "destination_account": body["destination_account"],
            "amount": body["amount"],
            "currency": body["currency"],
            "status": "PROCESSING",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "processed_at": None,
        }
        transactions.insert_one(doc)
        background_tasks.add_task(process_transaction, transaction_id)

    return JSONResponse(status_code=202, content={"message": "Accepted"})


@app.get("/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    projection = {"_id": 0}
    txn = transactions.find_one({"transaction_id": transaction_id}, projection)
    if not txn:
        return JSONResponse(status_code=404, content={"error": "Transaction not found"})
    allowed_keys = [
        "transaction_id",
        "source_account",
        "destination_account",
        "amount",
        "currency",
        "status",
        "created_at",
        "processed_at",
    ]
    return {k: txn.get(k) for k in allowed_keys}

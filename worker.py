# worker.py
import threading, time
from models import find_and_claim_one, mark_processed

POLL_INTERVAL = 2   # seconds

def process_transaction(tx):
    """Simulate external API processing with 30s delay"""
    print(f"[worker] Processing {tx['transaction_id']}...")
    time.sleep(30)  # simulate API call
    mark_processed(tx["transaction_id"])
    print(f"[worker] Finished {tx['transaction_id']}")

def worker_loop(app):
    # No framework app context needed for Mongo operations
    while True:
        tx = find_and_claim_one()
        if tx:
            threading.Thread(target=process_transaction, args=(tx,)).start()
        time.sleep(POLL_INTERVAL)

def start_worker(app):
    t = threading.Thread(target=worker_loop, args=(app,), daemon=True)
    t.start()

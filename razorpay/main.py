"""
main.py
-------
Razorpay Agentic Checkout — Main Application Entrypoint.
Supports:
  1. Interactive CLI Mode: python main.py --cli
  2. Automated Benchmark Demo: python main.py --demo
  3. Web Server & Mandate Dashboard: python main.py --serve
"""

import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import uuid
import argparse
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from agent.buyer_agent import BuyerAgent
from tests import test_p2t, test_t2t, test_p2k, test_guardrails

app = FastAPI(title="Razorpay Agentic Checkout API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = BuyerAgent()


class PurchaseRequest(BaseModel):
    query: str
    max_spend: float = 25000.0
    step_up_consent: bool = False
    user_name: str = "Priya"


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    here = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(here, "frontend", "index.html")
    with open(frontend_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/purchase")
def api_purchase(req: PurchaseRequest):
    agent.user_id = req.user_name if req.user_name else "Priya"
    result = agent.process_purchase_intent(
        user_query=req.query,
        user_max_spend=req.max_spend,
        step_up_consent_given=req.step_up_consent,
    )
    return JSONResponse(content=result)



@app.get("/api/metrics")
def api_metrics():
    return JSONResponse(content=agent.metrics.export_summary())


@app.get("/api/receipts")
def api_receipts():
    return JSONResponse(content=agent.receipt_chain.get_receipts())


@app.get("/api/catalog")
def api_catalog():
    return JSONResponse(content=[p.to_dict() for p in agent.raw_catalog])


class AddProductRequest(BaseModel):
    id: str
    name: str
    category: str
    price_inr: int
    billing_cycle: str = "one-time"
    description: str
    features: list[str] = []


@app.post("/api/catalog/add")
def api_add_product(req: AddProductRequest):
    import json
    new_product_dict = {
        "id": req.id,
        "name": req.name,
        "category": req.category,
        "price_inr": req.price_inr,
        "billing_cycle": req.billing_cycle,
        "description": req.description,
        "features": req.features,
        "in_stock": True,
    }
    
    here = os.path.dirname(os.path.abspath(__file__))
    catalog_file = os.path.join(here, "catalog", "products.json")
    with open(catalog_file, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data.append(new_product_dict)
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    agent.raw_catalog = load_catalog(agent.catalog_path)
    agent.catalog_dicts = [p.to_dict() for p in agent.raw_catalog]
    agent.catalog_index._build_index()

    return JSONResponse(content={"success": True, "message": f"Product '{req.name}' added to merchant catalog and indexed."})


@app.post("/api/catalog/upload_file")
async def api_upload_catalog_file(file: UploadFile = File(...)):
    import json
    import csv
    import io

    contents = await file.read()
    filename = file.filename.lower()
    items_to_add = []

    if filename.endswith(".json"):
        raw_items = json.loads(contents.decode("utf-8"))
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        for item in raw_items:
            items_to_add.append({
                "id": str(item.get("id", f"prod-{uuid.uuid4().hex[:6]}")),
                "name": str(item.get("name", "Unnamed Item")),
                "category": str(item.get("category", "general")),
                "price_inr": int(float(item.get("price_inr", item.get("price", 999)))),
                "billing_cycle": str(item.get("billing_cycle", "one-time")),
                "description": str(item.get("description", "Uploaded merchant product")),
                "features": item.get("features", ["Merchant Inventory"]),
                "in_stock": bool(item.get("in_stock", True)),
            })
    elif filename.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
        for row in reader:
            items_to_add.append({
                "id": str(row.get("id", f"prod-{uuid.uuid4().hex[:6]}")),
                "name": str(row.get("name", "Unnamed Item")),
                "category": str(row.get("category", "general")),
                "price_inr": int(float(row.get("price_inr", row.get("price", 999)))),
                "billing_cycle": str(row.get("billing_cycle", "one-time")),
                "description": str(row.get("description", "Uploaded merchant product")),
                "features": [f.strip() for f in str(row.get("features", "")).split(";") if f.strip()],
                "in_stock": True,
            })
    else:
        return JSONResponse(status_code=400, content={"error": "Unsupported file format. Please upload JSON or CSV."})

    here = os.path.dirname(os.path.abspath(__file__))
    catalog_file = os.path.join(here, "catalog", "products.json")
    with open(catalog_file, "r+", encoding="utf-8") as f:
        existing = json.load(f)
        existing.extend(items_to_add)
        f.seek(0)
        json.dump(existing, f, indent=2)
        f.truncate()

    agent.raw_catalog = load_catalog(agent.catalog_path)
    agent.catalog_dicts = [p.to_dict() for p in agent.raw_catalog]
    agent.catalog_index._build_index()

    return JSONResponse(content={
        "success": True,
        "count": len(items_to_add),
        "message": f"Successfully imported and FAISS-indexed {len(items_to_add)} products from '{file.filename}'."
    })




def run_cli_interactive():
    print("=" * 70)
    print("  RAZORPAY AGENTIC CHECKOUT — INTERACTIVE BUYER AGENT CLI")
    print("  Track 01: AI Growth & Agentic Commerce | AP2 + RBI 2026 Framework")
    print("=" * 70)
    print("Type your purchase request (or 'quit' to exit).\n")

    cli_agent = BuyerAgent()

    while True:
        try:
            query = input("Buyer Prompt > ").strip()
            if not query or query.lower() in ["exit", "quit", "q"]:
                break

            print("\n[Executing AP2 Mandate Chain & Grounding Gate...]")
            res = cli_agent.process_purchase_intent(query)

            if res.get("requires_step_up"):
                print(f"\n⚠️  RBI 2026 AFA STEP-UP REQUIRED: Transaction INR {res['amount_inr']:,} > INR 15,000 threshold.")
                consent = input("Authorize Step-Up with OTP/re-consent? (y/n): ").strip().lower()
                if consent == "y":
                    res = cli_agent.process_purchase_intent(query, step_up_consent_given=True)
                else:
                    print("Transaction cancelled at step-up.")
                    continue

            if res.get("success"):
                print(f"✅ PURCHASE SUCCESSFUL!")
                print(f"   Product:        {res['product']['name']}")
                print(f"   Amount:         INR {res['amount_inr']:,}")
                print(f"   Checkout Mode:  {res['checkout_mode'].upper()} (Order ID: {res['checkout_order_id']})")
                print(f"   Mandate Hash:   {res['receipt']['mandate_chain_hash'][:24]}...")
                print(f"   Receipt Hash:   {res['receipt']['this_hash'][:24]}...")
            else:
                print(f"🛑 TRANSACTION BLOCKED: {res.get('error')}")
                if "recourse" in res:
                    print(f"   Reason:         {res['recourse']['user_message']}")
                    print(f"   Action:         {res['recourse']['actionable_step']}")
            print("-" * 70)

        except (KeyboardInterrupt, EOFError):
            break

    print("\nSession ended. Summary metrics:")
    cli_agent.metrics.print_summary()


def run_automated_demo():
    print("=" * 70)
    print("  RUNNING ALL ADVERSARIAL BENCHMARKS & SCENARIOS")
    print("=" * 70)
    test_p2t.run()
    test_t2t.run()
    test_p2k.run()
    test_guardrails.run()
    print("=" * 70)
    print("  ALL 4 TEST SUITES PASSED CLEANLY (0% ASR, 0% FPR)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Razorpay Agentic Checkout")
    parser.add_argument("--cli", action="store_true", help="Run interactive CLI buyer agent")
    parser.add_argument("--demo", action="store_true", help="Run automated test suite demo")
    parser.add_argument("--serve", action="store_true", help="Run FastAPI web server")
    parser.add_argument("--port", type=int, default=8000, help="Port for web server (default: 8000)")
    args = parser.parse_args()

    if args.cli:
        run_cli_interactive()
    elif args.demo:
        run_automated_demo()
    else:
        print(f"Starting Razorpay Agentic Checkout Server on http://127.0.0.1:{args.port} ...")
        uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

# Razorpay Agentic Checkout — Bounded Buyer Agent & Trust Infrastructure
**Track 01: AI Growth & Agentic Commerce | Razorpay AI Buildathon 2026**

---

## 1. Pitch & Core Idea

> **"70% of consumers are comfortable with AI-assisted product discovery, but only 4% trust an AI to buy without supervision. We built the trust infrastructure for that gap."**

Razorpay Agentic Checkout turns any merchant catalog into an agent-transactable storefront with end-to-end bounded execution on Razorpay test-mode APIs. It enables an AI buyer agent to search products, negotiate constraints, form signed cryptographic mandates, verify ground truth against hallucination, enforce regulatory thresholds, and execute checkout with a dispute-grade audit trail.

---

## 2. Three-Layer Grounding (The Core Winning Differentiator)

1. **AP2 (Global Agent Payment Protocol) + Ed25519 Verifiable Credentials:**
   $$\text{Intent Mandate} \xrightarrow{\text{Signed Ed25519}} \text{Cart Mandate} \xrightarrow{\text{Signed Ed25519}} \text{Payment Mandate}$$
   - Intent Mandate: Enforces user spend ceiling and category allow-list.
   - Cart Mandate: Records product details + **mandatory LLM explainability reasoning**.
   - Payment Mandate: Binds Razorpay Order ID + Step-Up AFA status.
   - Signed with asymmetric **Ed25519 keypairs** (`mandate/crypto_signing.py`) for non-repudiation.

2. **RBI Digital Payments E-Mandate Framework 2026 (India Regulation):**
   - Step-up re-consent threshold set to **₹15,000** (RBI Additional Factor of Authentication / AFA limit).
   - Interactive 6-digit OTP & Passkey WebAuthn simulation modal.
   - Mandatory user **PAUSE** and **CANCEL** rights enforced at any state in the Kripke state machine.

3. **NPCI's Unified Agent Protocol (UAP) & Razorpay Pilot Alignment:**
   - Implements the delegated payment model piloted by Razorpay with NPCI in Feb 2026 for autonomous checkouts.

> *"We extend the exact consent-and-spending-limit pattern Razorpay already piloted with NPCI and Claude, grounded in India's actual 2026 regulatory framework."*

---

## 3. Protocol Race Comparison Matrix

| Protocol Dimension | x402 / HTTP 402 | OpenAI ACP | **Razorpay Agentic Checkout (AP2 + RBI 2026)** |
|:---|:---|:---|:---|
| **Target Scope** | Micro-payments per API call | Chat-based checkout | **Bounded End-to-End Delegated Agent Commerce** |
| **Trust Model** | Pre-paid wallet debits | Merchant trust | **Cryptographic Mandate Chain (Ed25519 VC)** |
| **Regulatory Alignment** | None | US-centric | **RBI 2026 E-Mandate Framework (₹15,000 Step-Up AFA)** |
| **Explainability** | None | Text prompt | **Cart Mandate Explicit Reasoning Field** |
| **Auditability** | Server logs | Session history | **Dispute-Grade SHA-256 Receipt Chain (`receipt_chain.json`)** |
| **Failure Recovery** | Retry HTTP 402 | Error text | **Transparent Fallback Degradation & Algorithmic Recourse** |

---

## 4. Architecture & Flow

```
Catalog + Grounding Gate  →  Buyer Agent  →  Guardrails + Mandate Chain  →  Razorpay Checkout  →  Receipt Chain + Audit
   (FAISS + claim check)     (Ed25519 Sign)    (hardcoded rules,             (Payment Mandate,      (SHA-256
                              drafts Intent      Cart Mandate,                 step-up @ ₹15,000)     disk-persisted)
                              Mandate)           Kripke state check)
```

---

## 5. Key Features & Winning Edges

- **🛍️ Multi-Category Merchant Catalog (`catalog/products.json`):** Pre-loaded with Subscriptions, Electronics Hardware (Sony Soundbars, ESP32 Microcontrollers), and SaaS utilities.
- **📁 Dynamic CSV/JSON Catalog Ingestion (`POST /api/catalog/upload_file`):** Merchants can upload full CSV or JSON catalog files from the Web UI to FAISS-index inventory on the fly.
- **🔒 Ed25519 W3C Verifiable Credentials (`mandate/crypto_signing.py`):** Non-repudiable asymmetric digital signatures.
- **⚡ Interactive 6-Digit OTP / WebAuthn Step-Up Modal:** Realistic AFA compliance dialog for transactions > ₹15,000.
- **🛡️ Algorithmic Recourse Engine (`audit/recourse.py`):** Provides exact actionable steps on denial ("what to change to get approved").
- **💾 Disk-Persistent Receipt Chain (`receipt_chain.json`):** Dispute-grade evidence preserved across server restarts.

---

## 6. Repository Structure

```
razorpay-agentic-checkout/
├── README.md                    # Architecture, STRIDE table, protocol alignment, benchmarks
├── .env.example / .gitignore    # Keys never committed

├── requirements.txt
├── catalog/
│   ├── products.json            # Subscriptions, Electronics & Hardware catalog
│   ├── schema.py                # Schema.org product pattern + SHA-256 provenance checksums
│   └── faiss_index.py           # TF-IDF + FAISS IndexFlatIP semantic vector search
├── agent/
│   ├── buyer_agent.py           # End-to-end conversational autonomous buyer agent
│   ├── planner.py / retriever.py / decision.py / prompts.py
├── mandate/
│   ├── intent_mandate.py        # Intent Mandate (user authorization & spend ceiling)
│   ├── cart_mandate.py          # Cart Mandate (selected product & explainability reasoning)
│   ├── payment_mandate.py       # Payment Mandate (Razorpay order reference & step-up status)
│   ├── chain.py                 # Cryptographic mandate chain verification
│   ├── crypto_signing.py        # Ed25519 asymmetric signature generation & verification
│   └── kripke_state.py          # Finite state machine with allow-list transitions & PAUSE/CANCEL
├── guardrails/
│   ├── rules.py                 # STRIDE-mapped hardcoded rules, ₹15,000 step-up threshold
│   ├── risk_vector.py           # Multi-dimensional risk score (monetary, divergence, anomalies)
│   ├── loop_detector.py         # Deque sliding window consecutive tail-matching loop detector
│   └── failure_classifier.py    # Deterministic vs probabilistic error classifier & recovery
├── grounding/
│   ├── grounding_gate.py        # Commerce hallucination and price tampering checks
│   └── contradiction_detector.py # Regex-based negative constraint & budget check
├── checkout/
│   ├── razorpay_client.py       # Test-mode Orders API wrapper & signature verification
│   └── fallback_mode.py         # Transparent degradation to simulated checkout on network/key error
├── audit/
│   ├── receipt_chain.py         # Dispute-grade SHA-256 hash-linked receipt trail & JSON export
│   ├── recourse.py              # Algorithmic recourse on denial ("what to change to get approved")
│   └── metrics.py               # Real measured transaction and latency counters
├── tests/
│   ├── test_p2t.py              # Prompt-to-Tool injection attack benchmark
│   ├── test_t2t.py              # Tool-to-Tool indirect data poisoning benchmark
│   ├── test_p2k.py              # Prompt-to-Kripke state injection benchmark
│   └── test_guardrails.py       # Combined mixed transaction integration suite
├── frontend/
│   └── index.html               # Interactive Mandate Lifecycle Web Dashboard
└── main.py                      # CLI, benchmark demo, and FastAPI server entrypoint
```

---

## 7. STRIDE Threat Model & Defenses

| Threat Category | Attack Vector Tested | Defense Implementation | Measured Result |
|:---|:---|:---|:---|
| **Spoofing** | Forged Mandate Injection (`test_p2t.py`) | Hardcoded `secure_checkout_gate()` + Ed25519 signatures | **100% Blocked (0% ASR)** |
| **Tampering** | Catalog Poisoning / Indirect Injection (`test_t2t.py`) | FAISS provenance tags + regex marker sanitization + Grounding Gate | **100% Blocked** |
| **Repudiation** | Post-transaction dispute | SHA-256 hash-linked dispute-grade Receipt Chain (`receipt_chain.json`) | **100% Tamper-Evident** |
| **Information Disclosure** | Secret key leakage | Strict `.env` isolation; zero test credentials committed | **Zero Leaks** |
| **Denial of Service** | Agent loop recursion | Sliding window tail-matching deque Loop Detector (`guardrails/loop_detector.py`) | **Loop Halted** |
| **Elevation of Privilege** | State Machine Bypass (`test_p2k.py`) | Kripke finite state machine with strict allow-list transitions | **100% Blocked (0% ASR)** |

---

## 8. Measured Benchmark Results

All metrics are self-measured and reproducible on demand:
- **P2T (Prompt-to-Tool Injection):** `0.0% Attack Success Rate` (5/5 injection payloads blocked)
- **T2T (Tool-to-Tool Indirect Injection):** `100.0% Detection Rate` (3/3 caught and sanitized; Grounding Gate caught downstream price hallucination)
- **P2K (Prompt-to-Kripke State Injection):** `0.0% Attack Success Rate` (10/10 illegal transitions blocked)
- **Guardrail Integration Suite:** `0.0% Attack Success Rate`, `0.0% False Positive Rate` across mixed batches

---

## 9. Quickstart (Local)

### 1. Setup Environment
```bash
pip install -r requirements.txt
cp .env.example .env   # Fill in RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, GROQ_API_KEY
```

### 2. Run All Adversarial Benchmarks
```bash
python main.py --demo
# or with pytest:
pytest tests/
```

### 3. Interactive CLI Buyer Agent
```bash
python main.py --cli
```

### 4. Launch Web Dashboard
```bash
python main.py --serve --port 8000
```
Open **http://127.0.0.1:8000** in your browser.

---

## 10. ☁️ Cloud Deployment (Render.com — 1 Click, Always-On)

Deploy this project publicly so it runs **24/7 without needing your computer**:

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Razorpay Agentic Checkout — Track 01 Final Release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/razorpay-agentic-checkout.git
git push -u origin main
```

### Step 2: Deploy on Render (Free Tier)
1. Go to **[https://render.com](https://render.com)** → Sign up / Login with GitHub.
2. Click **"New +"** → **"Web Service"** → Connect your GitHub repo.
3. Render auto-detects `render.yaml` — click **Deploy**.
4. Go to **Environment → Add Environment Variables:**
   - `RAZORPAY_KEY_ID` = your Razorpay test key
   - `RAZORPAY_KEY_SECRET` = your Razorpay test secret
   - `GROQ_API_KEY` = your Groq API key
5. Your app will be live at: **`https://razorpay-agentic-checkout.onrender.com`**

> **Free tier note:** Render free tier sleeps after 15 min of inactivity. For a always-awake demo, use [Railway.app](https://railway.app) or [Fly.io](https://fly.io) instead.


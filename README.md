# ✈️ Rebound — Autonomous Travel Disruption Recovery Agent

[![CI - Evals](https://img.shields.io/badge/Evals-30%2F30%20Passing%20(100%25)-brightgreen)](#evaluation--reliability)
[![Apps Connected](https://img.shields.io/badge/Apps-Duffel%20%7C%20Google%20Calendar%20%7C%20Gmail%20%7C%20Twilio-blue)](#integrated-applications)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](#)

> **"Rebound has already fixed your trip by the time the airline emails you about the cancellation."**

Built for the **Multi-App AI Agent Hackathon** (hosted by Lemma & Comma Capital, judged by Arga Labs).

---

## 🎯 What It Does

When your flight is cancelled or delayed, **Rebound**:
1. **Reads your Google Calendar** to locate the destination commitment (the true hard deadline).
2. **Searches Duffel NDC inventory** and filters options using deterministic policy guardrails in Python.
3. **Applies Mandate Rules**:
   - $\le \$300$ delta: **Auto-books instantly**.
   - $\$300 < \Delta \le \$800$: **Holds the seat (Hold-Order Pattern)** and texts you via Twilio SMS for 1-click confirmation ("1", "2", or "NO").
   - $> \$800$ or 0 options: **Escalates cleanly** without booking.
4. **Irreversible Action Invariant**: Books the new flight $\to$ verifies ticket issuance via Duffel GET $\to$ **only then cancels the disrupted ticket**.
5. **Updates Google Calendar**, emails your **itinerary via Gmail**, drafts statutory **EU261 compensation claims**, and sends an ETA update to your **pickup contact**.

---

## 🏗️ Architecture

```
[Disruption Webhook]  ──►  FastAPI /webhook/disruption
                                  │  (Idempotency deduplication on event_id)
                                  ▼
                           ┌──────────────┐
                           │ Rebound Core │  ◄── Traveler Profile & Mandate
                           └──────────────┘
         ┌──────────┬──────────┼──────────┬──────────┐
         ▼          ▼          ▼          ▼          ▼
      Duffel     Calendar    Gmail      Twilio    Trace Log
    (Hold/Book/ (Commitment (Itinerary (Approval (JSONL audit
     Cancel)     & Patch)    & EU261)   & ETA)    timeline)
```

---

## 🧪 Evaluation & Reliability (30/30 Passing)

We built an **evaluation harness with an agent inside it**, not an agent with tests bolted on.

Full benchmark matrix documented in [**`EVAL_RESULTS.md`**](EVAL_RESULTS.md):
- **Idempotency (S10):** Duplicate delivery storms never create double bookings.
- **Hold-Order Pattern (S02, S13):** Prevents 15-minute offer expiration during SMS approval waits.
- **Ordered Irreversible Actions (S20, S21):** Verification mismatches abort old flight cancellation.
- **API Fault Tolerance (S11, S27, S29):** Network 500s trigger exponential backoff (1s, 2s, 4s). Calendar and Gmail outages degrade gracefully.

Run the evaluation suite:
```bash
python3 evals/test_scenarios.py
```

---

## 🚀 Quickstart

### 1. Install & Configure
```bash
# Clone the repository
git clone https://github.com/yashjaiswal2818/rebound.git
cd rebound

# Copy environment variables
cp .env.example .env
```

### 2. Run the Evaluation Suite
```bash
python3 evals/test_scenarios.py
```

### 3. Launch the Webhook Gateway & Visualizer
```bash
uvicorn app.main:app --reload --port 8000
```
Open `http://localhost:8000/docs` for the Swagger API or open `viewer/index.html` in your browser.


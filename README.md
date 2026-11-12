# PayPilot AI

### AI-Powered Procurement Intelligence and Payment Platform

PayPilot AI is an intelligent procurement platform that helps businesses evaluate supplier quotations, compare price and quality, identify procurement risks, and make informed purchasing decisions.

It combines Google Gemini-powered analysis, deterministic supplier scoring, human approval controls, and PayPal Sandbox payment integration in one dashboard.

## The Problem

Businesses often evaluate supplier quotations manually. Comparing prices, delivery timelines, specifications, and procurement risks can be time-consuming and inconsistent.

PayPilot AI simplifies this process by combining structured supplier evaluation with AI-generated explanations and controlled payment workflows.

## Key Features

- Procurement request creation and budget management.
- Supplier quotation management.
- Weighted supplier evaluation and ranking.
- Google Gemini-powered procurement reports.
- Supplier comparison and price-quality trade-offs.
- Budget utilization and risk assessment.
- Human approval before payment.
- PayPal Sandbox order creation and capture.
- Payment transaction history and status tracking.

## Technology Stack

### Frontend
- React
- Vite
- JavaScript
- CSS
- Lucide React
- React Markdown

### Backend
- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- REST APIs

### Artificial Intelligence
- Google Gemini API
- Gemini model: gemini-3.6-flash

### Payments
- PayPal REST API
- PayPal Sandbox

## How It Works

1. Create a procurement request with a description and approved budget.
2. Add supplier quotations containing price, specifications, quantity, and delivery information.
3. PayPilot AI evaluates the quotations using a weighted scoring model.
4. Gemini generates an explainable procurement decision report.
5. A human procurement manager reviews the recommendation and approves a supplier.
6. The application creates a PayPal Sandbox order.
7. The payment is completed through the Sandbox checkout flow.
8. PayPilot AI verifies the PayPal response and records the transaction status.

## Supplier Evaluation

The current scoring configuration uses:

| Evaluation factor | Weight |
|---|---:|
| Price | 45% |
| Specifications | 35% |
| Delivery time | 20% |

The AI report explains supplier rankings, trade-offs, budget impact, and procurement risks.

AI recommendations are advisory. They do not independently authorize purchases or payments.

## AI Decision Report

The Gemini-generated report contains eight sections:

1. Executive Summary
2. Supplier Ranking
3. Supplier Comparison
4. Price and Quality Trade-offs
5. Procurement Risk Assessment
6. Budget Impact
7. Final Recommendation
8. Human Approval and Payment Controls

The application also captures Gemini completion information and token usage for analysis verification.

## Payment and Human Approval Controls

PayPilot AI separates AI recommendations from financial authorization.

- A human must explicitly approve a supplier quotation.
- Payment creation requires an approved procurement transaction.
- The backend verifies the stored PayPal order ID.
- The capture response is checked for completed status.
- The captured amount and currency are validated.
- Completed transactions are recorded in the application.

**Important:** The current integration uses PayPal Sandbox. It demonstrates Sandbox checkout and capture, not real-money supplier payouts. Production deployment would require additional authentication, authorization, security controls, and payment integration work.

## Project Structure

    PayPilot-AI/
    ├── backend/
    │   ├── app/
    │   │   ├── models/
    │   │   ├── routes/
    │   │   └── services/
    │   ├── config.py
    │   ├── requirements.txt
    │   └── run.py
    ├── frontend/
    │   ├── public/
    │   ├── src/
    │   ├── package.json
    │   └── vite.config.js
    ├── docs/
    ├── .env.example
    ├── .gitignore
    └── README.md

## Setup Instructions

### Prerequisites

- Python 3
- Node.js and npm
- Google Gemini API key
- PayPal Sandbox developer credentials

### 1. Clone the repository

    git clone YOUR_GITHUB_REPOSITORY_URL
    cd PayPilot-AI

### 2. Configure environment variables

    cp .env.example .env

Edit `.env` locally and provide your credentials:

    SECRET_KEY=your-secret-key
    PAYPAL_MODE=sandbox
    PAYPAL_CLIENT_ID=your-paypal-sandbox-client-id
    PAYPAL_CLIENT_SECRET=your-paypal-sandbox-secret
    GEMINI_API_KEY=your-gemini-api-key
    GEMINI_MODEL=gemini-3.6-flash

Never commit `.env` or share API credentials publicly.

### 3. Install backend dependencies

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r backend/requirements.txt

### 4. Start the backend

    cd backend
    python run.py

Backend address:

    http://127.0.0.1:5000

Health endpoint:

    http://127.0.0.1:5000/api/health

### 5. Install frontend dependencies

Open another terminal:

    cd PayPilot-AI/frontend
    npm ci

### 6. Start the frontend

    npm run dev

Frontend address:

    http://localhost:5173

## Environment Variables

| Variable | Purpose |
|---|---|
| SECRET_KEY | Flask application secret |
| PAYPAL_MODE | PayPal environment; use sandbox for testing |
| PAYPAL_CLIENT_ID | PayPal Sandbox client ID |
| PAYPAL_CLIENT_SECRET | PayPal Sandbox client secret |
| GEMINI_API_KEY | Google Gemini API key |
| GEMINI_MODEL | Gemini model identifier |

Refer to `.env.example` for the configuration template.

## Testing

Backend:

    cd backend
    python -m pytest -q

Frontend:

    cd frontend
    npm ci
    npm run build

Run the application locally and test the complete procurement and Sandbox checkout workflow.

## Security and Limitations

- Never commit API keys, passwords, or `.env` files.
- Use Sandbox credentials for development and demonstrations.
- AI-generated supplier information must be independently verified.
- Supplier specifications, warranties, and credentials are only as reliable as the supplied quotation data.
- Human approval is required before payment.
- The current application is a hackathon prototype, not a production financial system.
- Production deployment requires authentication, role-based authorization, secure session management, CSRF protection, monitoring, and additional payment safeguards.

## Project Vision

PayPilot AI aims to make business procurement more transparent, explainable, and efficient by combining AI-assisted decision intelligence with human-controlled payment execution.

---

**Built for the PayPal AI Hackathon — Build What's Next with PayPal and AI.**

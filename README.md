# 🌿 EcoSort AI — AI-Powered Waste Segregation & Recycling Assistant

> **Bharat Builds Tour · Environmental Hacks 2026**
> Developed: October 8–11, 2026 (Hackathon window)

EcoSort AI helps students, households, and communities correctly identify and dispose of waste through AI-powered image classification, reducing landfill usage and supporting a circular economy.

---

## ⚠️ Important Disclaimers

- **AI predictions can be incorrect.** All classifications are approximate.
- **Local rules vary.** Always verify disposal guidance with your local municipal waste authority.
- **Never handle hazardous materials without appropriate precautions.**

---

## 📋 Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [AWS Architecture](#aws-architecture)
4. [Setup Instructions](#setup-instructions)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [Testing](#testing)
8. [Demo Script](#demo-script)
9. [Known Limitations](#known-limitations)
10. [AI Tools & Disclosures](#ai-tools--disclosures)
11. [Third-Party Libraries](#third-party-libraries)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 AI Waste Scanner | Upload JPG/PNG/WebP images for instant classification |
| ♻️ Disposal Guidance | Step-by-step disposal instructions per waste category |
| 📊 Dashboard | Scan statistics, charts, and category breakdown |
| 📜 Scan History | Searchable, filterable history with delete functionality |
| 💡 Insights | Common mistakes, reduction tips, environmental context |
| 📚 Education | Segregation guide, recycling do's & don'ts, e-waste safety, composting |

### Waste Categories Supported
- 🍃 Organic / Compostable
- 📄 Paper & Cardboard
- 🧴 Plastic
- 🍾 Glass
- 🥫 Metal
- 💻 Electronic Waste (E-Waste)
- 🗑️ General / Residual Waste
- ⚠️ Hazardous / Special Handling
- ❓ Unclassified (low confidence)

---

## 🛠️ Tech Stack

### Frontend
- **React 18** + **Vite** + **TypeScript**
- **Tailwind CSS** — custom eco-green theme
- **Lucide React** — icons
- **Recharts** — dashboard charts
- **React Router v6** — navigation
- **React Dropzone** — image upload

### Backend
- **Python 3.11+** + **FastAPI**
- **Uvicorn** — ASGI server
- **Pillow** — image validation
- **SlowAPI** — rate limiting
- **boto3** — AWS SDK
- **httpx** — async HTTP (Hugging Face API)

### AI Classification
- **Primary:** Hugging Face Inference API (`google/vit-base-patch16-224` or configurable)
- **Alternative:** Amazon Bedrock (Claude claude-3-haiku with vision) — requires Bedrock access
- **Fallback:** Demo mode (clearly labelled, rotates through example categories)

### AWS Services
- **Amazon DynamoDB** — scan history and statistics
- **Amazon S3** — optional image storage (with lifecycle rules)
- **Amazon Bedrock** — optional AI backend (Claude claude-3-haiku vision)

---

## 🏗️ AWS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EcoSort AI Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Browser (React/Vite)                                            │
│       │                                                           │
│       │ HTTP / multipart upload                                  │
│       ▼                                                           │
│  FastAPI Backend (Python)                                        │
│       │                                                           │
│       ├─── Image Validation (Pillow)                            │
│       │                                                           │
│       ├─── AI Classifier ─────────────────────────────────────► │
│       │    ├── Hugging Face Inference API (external)            │
│       │    ├── Amazon Bedrock (Claude claude-3-haiku vision)*   │
│       │    └── Demo Mode (fallback)                             │
│       │                                                           │
│       ├─── Amazon DynamoDB ──────────────────────────────────── │
│       │    └── ecosort-scans table (scan history)               │
│       │                                                           │
│       └─── Amazon S3 (optional) ──────────────────────────────► │
│            └── ecosort-images bucket (uploaded images)           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

* Bedrock requires region with model access enabled
```

### DynamoDB Table: `ecosort-scans`
- **Partition key:** `id` (String, UUID)
- **Billing:** On-demand (PAY_PER_REQUEST) — Free Tier eligible
- **Attributes:** id, category, label, confidence, recyclable, timestamp, isDemo

### AWS Cost Estimate (Free Tier)
| Service | Free Tier | Estimated Usage |
|---------|-----------|-----------------|
| DynamoDB | 25 GB storage, 25 RCU/WCU | < 1 MB, minimal |
| S3 | 5 GB storage, 20k GET, 2k PUT | < 100 MB demo |
| Bedrock | Varies by model | Minimal (demo) |

---

## 🚀 Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.11+
- AWS account (optional, for DynamoDB/Bedrock)
- Hugging Face account (optional, free tier available)

### 1. Clone / create the project

```bash
cd C:\Users\Purvi\.gemini\antigravity\scratch\ecosort-ai
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env if needed
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate    # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### 4. AWS Setup (Optional)

**DynamoDB table:**
```bash
cd backend
python ..\infrastructure\dynamodb_setup.py
```

**Required IAM permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:Scan",
    "dynamodb:DeleteItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/ecosort-scans"
}
```

---

## 🔐 Environment Variables

### Frontend (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000
VITE_DEMO_MODE=false
```

### Backend (`backend/.env`)
```env
# AI Provider: 'huggingface', 'bedrock', or 'demo'
AI_PROVIDER=huggingface
HUGGINGFACE_TOKEN=your_hf_token_here
HUGGINGFACE_MODEL=google/vit-base-patch16-224

# AWS (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
DYNAMODB_TABLE=ecosort-scans

# Demo mode (no AI required)
DEMO_MODE=false

CORS_ORIGINS=http://localhost:5173
```

> ⚠️ **Never commit `.env` files or credentials to source control.**

---

## ▶️ Running the Application

### Start backend:
```bash
cd backend
.\venv\Scripts\activate
python run.py
# Server at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Start frontend:
```bash
cd frontend
npm run dev
# App at http://localhost:5173
```

### Quick Start (both together on Windows):
```powershell
# Terminal 1
cd backend; .\venv\Scripts\activate; python run.py
# Terminal 2
cd frontend; npm run dev
```

### Demo Mode (no backend needed):
```env
# frontend/.env
VITE_DEMO_MODE=true
```

---

## 🧪 Testing

### Manual Testing Checklist

```
✅ Application starts without build errors
✅ Home page loads with all sections
✅ Navigation links work (all 6 pages)
✅ Image upload via drag-and-drop works
✅ Image upload via click-to-browse works
✅ Image preview is displayed correctly
✅ Invalid file types are rejected with error message
✅ Files over 10 MB are rejected with error message
✅ Analyze button triggers classification
✅ Loading state is shown during analysis
✅ Classification result displays category and confidence
✅ Disposal instructions are displayed
✅ Safety precautions shown for hazardous/glass/metal
✅ Low-confidence results handled (unclassified category)
✅ "Analyze Another Item" resets the scanner
✅ Category correction dropdown works
✅ Scan is saved to history after classification
✅ History page shows scans with timestamps
✅ History search by label works
✅ History filter by category works
✅ Individual record deletion works
✅ Clear all history works (with confirmation)
✅ Dashboard shows total scans and stats
✅ Dashboard charts render correctly
✅ Dashboard updates after new scans
✅ Insights page shows data or empty state
✅ Education page tabs all work
✅ App is usable on mobile (320px width)
✅ Demo mode banner shown when demo results returned
✅ Error state shown clearly on classification failure
✅ Backend health endpoint returns 200
```

### Backend API Tests (curl):
```bash
# Health check
curl http://localhost:8000/api/health

# Classify an image
curl -X POST http://localhost:8000/api/classify \
  -F "file=@test_image.jpg"

# Get history
curl http://localhost:8000/api/history

# Get stats
curl http://localhost:8000/api/stats
```

### Frontend Build Test:
```bash
cd frontend
npm run build
# Should complete without TypeScript or build errors
```

---

## 🎬 3-Minute Demo Script

### 0:00–0:25 — Environmental Problem
> "2.1 billion tonnes of waste are generated globally every year, yet 91% of plastics are never recycled. The root cause is poor waste segregation at source. EcoSort AI makes correct disposal effortless."

### 0:25–0:55 — AI Scanner Demo
> Upload a plastic bottle image → show loading → reveal classification with 82% confidence as "Plastic (PET)" → explain the result and confidence bar.

### 0:55–1:25 — Disposal Guidance
> Show the 4-step disposal instructions → highlight the "Check Local" notice → for a battery, show the safety precautions panel.

### 1:25–1:55 — History & Dashboard
> Navigate to History — show the scan that was just recorded → filter by "Plastic" → go to Dashboard → show the category pie chart and weekly bar chart updating in real time.

### 1:55–2:25 — AWS Architecture
> "Our backend persists every scan to Amazon DynamoDB in real time — here's the table in the AWS Console [show screenshot]. The classifier can also use Amazon Bedrock's Claude claude-3-haiku vision model when Bedrock access is enabled. The DynamoDB setup script creates the table with on-demand billing — zero cost at hackathon scale."

### 2:25–2:50 — Benefits, Limits & Next Steps
> "Correctly sorted waste reduces landfill and emissions. Limitations: AI predictions are approximate; local rules vary; Hugging Face's general image classifier doesn't specialise in waste, so a fine-tuned waste-specific model would significantly improve accuracy. Next: mobile app, barcode scanning, multilingual support."

### 2:50–3:00 — Closing
> "EcoSort AI — sort smarter, recycle better. Thank you."

---

## ⚠️ Known Limitations

1. **AI accuracy**: The default Hugging Face model (`google/vit-base-patch16-224`) is a general image classifier, not a waste-specific model. Accuracy is approximate. A fine-tuned waste classification model would perform significantly better.

2. **Label mapping**: Raw model labels are mapped to waste categories using keyword heuristics, which can produce incorrect mappings for ambiguous items.

3. **Local storage fallback**: When the backend is unavailable, scan history is stored in the browser's localStorage. This data is device-specific and can be cleared by the browser.

4. **No user authentication**: There is no user account system. All scans from a session are shared in the in-memory backend store.

5. **Bedrock access**: Amazon Bedrock's Claude claude-3-haiku model requires explicit access request approval in the AWS Console. Not available in all regions.

6. **Rate limiting**: The backend applies a 20 requests/minute rate limit per IP, which may impact rapid testing.

7. **Image not stored on server**: Images are classified in-memory and not persistently stored (no S3 upload in the current implementation) unless explicitly configured.

---

## 🤖 AI Tools & Disclosures

| Tool | Role |
|------|------|
| **Google Antigravity (Gemini)** | AI coding assistant used to generate, scaffold, and review all source code during the hackathon window (Oct 8–11, 2026). All code was reviewed and adapted by the development team. |
| **Hugging Face Inference API** | Real image classification API. Model: `google/vit-base-patch16-224` (free tier). |
| **Amazon Bedrock** | Optional alternative AI backend using Claude claude-3-haiku vision. |

All AI-generated code was reviewed for correctness, security, and accuracy before inclusion.

---

## 📦 Third-Party Libraries

### Frontend
| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| react | 18.2.0 | MIT | UI framework |
| react-router-dom | 6.22.0 | MIT | Client routing |
| tailwindcss | 3.4.1 | MIT | Styling |
| lucide-react | 0.344.0 | ISC | Icons |
| recharts | 2.12.0 | MIT | Charts |
| react-dropzone | 14.2.3 | MIT | File upload |
| axios | 1.6.7 | MIT | HTTP client |
| date-fns | 3.3.1 | MIT | Date formatting |
| uuid | 9.0.0 | MIT | Unique IDs |

### Backend
| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| fastapi | 0.110.0 | MIT | Web framework |
| uvicorn | 0.27.1 | BSD | ASGI server |
| pillow | 10.2.0 | HPND | Image processing |
| boto3 | 1.34.34 | Apache 2.0 | AWS SDK |
| slowapi | 0.1.9 | MIT | Rate limiting |
| pydantic | 2.6.1 | MIT | Data validation |
| httpx | 0.26.0 | BSD | Async HTTP |
| python-dotenv | 1.0.1 | BSD | Env vars |

---

## 📁 Project Structure

```
ecosort-ai/
├── frontend/                 # React/Vite/TypeScript frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   │   ├── layout/       # Sidebar, Header
│   │   │   └── scanner/      # DropZone, ResultCard
│   │   ├── hooks/            # useScanner, useHistory
│   │   ├── pages/            # Page components
│   │   ├── services/         # API calls, local storage
│   │   ├── constants/        # Category metadata
│   │   └── types/            # TypeScript types
│   ├── .env.example
│   └── package.json
│
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── main.py           # FastAPI routes
│   │   ├── classifier.py     # AI classification logic
│   │   ├── storage.py        # DynamoDB / in-memory store
│   │   ├── models.py         # Pydantic models
│   │   └── config.py         # Settings from env vars
│   ├── .env.example
│   ├── requirements.txt
│   └── run.py
│
├── infrastructure/
│   └── dynamodb_setup.py     # DynamoDB table creation script
│
└── README.md
```

---

## 🏆 Hackathon Compliance

| Requirement | Status |
|-------------|--------|
| New project developed Oct 8–11, 2026 | ✅ |
| React + Vite + TypeScript frontend | ✅ |
| FastAPI Python backend | ✅ |
| Genuine AI image classification | ✅ (HF API / Bedrock) |
| Amazon DynamoDB integration | ✅ |
| Demo mode when AI unavailable | ✅ (clearly labelled) |
| Error handling and loading states | ✅ |
| Input validation (type + size) | ✅ |
| Rate limiting | ✅ |
| No credentials in frontend | ✅ |
| `.env.example` without secrets | ✅ |
| AI tools disclosed | ✅ |
| Known limitations documented | ✅ |
| 3-minute demo script | ✅ |

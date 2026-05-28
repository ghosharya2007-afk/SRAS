[README.md](https://github.com/user-attachments/files/28332170/README.md)
# ⚡ SRAS — Smart Resource Allocation System

> AI-powered emergency resource allocation and dispatch engine for disaster response and social impact.

![Built with](https://img.shields.io/badge/Built%20with-React%20%2B%20FastAPI-blue)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-orange)
![Deploy](https://img.shields.io/badge/Deploy-Cloud%20Run%20%2B%20Firebase-green)

---

## 🎯 What is SRAS?

SRAS is a **real-time emergency resource coordination system** that connects people in need with resource providers (NGOs, hospitals, volunteers). It uses **Google Gemini AI** to auto-classify emergencies, a **bounded mathematical priority formula** to ensure fair queuing, and a **greedy matching algorithm** to dispatch the nearest capable provider.

### Key Differentiators
| Feature | Traditional Systems | SRAS |
|---------|-------------------|------|
| Priority Model | Static triage categories | Dynamic, bounded mathematical scoring |
| Resource Matching | Manual coordinator decisions | Algorithmic, real-time greedy matching |
| Demand Prediction | Reactive only | Proactive AI forecasting (Gemini) |
| Transparency | Black box | Explainable priority scores shown to users |
| Input Methods | Forms only | Voice + Text + AI auto-classification |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  [Request Page]    [Provider Portal]    [Admin Dashboard]        │
│       ↕                    ↕                     ↕              │
└───────────────────┬─────────────────────────────────────────────┘
                    │  HTTPS / REST API
┌───────────────────▼─────────────────────────────────────────────┐
│                    FastAPI Backend (Cloud Run)                   │
│  /api/requests  /api/dispatch  /api/ai  /api/stats              │
├─────────────────────────────────────────────────────────────────┤
│  Priority Engine     │  Matching Engine    │  Gemini Service     │
│  (Bounded scoring)   │  (Greedy dispatch)  │  (3 AI use cases)   │
└─────────────────────┴────────────────────┴─────────────────────┘
```

---

## 🧮 Mathematical Core

### Priority Score Formula
```
P(r) = B(type) + T(t) + S(s) + V(v)
```

| Component | Formula | Range |
|-----------|---------|-------|
| **Base** B(type) | food=10, shelter=15, medical=50, critical=100 | [10, 100] |
| **Time Aging** T(t) | min(40, 40 × ln(1+t_hrs) / ln(13)) | [0, 40] |
| **Severity** S(s) | severity × 3 | [3, 30] |
| **Verified** V(v) | 5 if verified, else 0 | [0, 5] |

**Key property:** Time bonus uses a logarithmic curve — grows fast in the first 2 hours, plateaus after 12 hours. This prevents old low-severity requests from outscoring new critical emergencies.

### Matching Score Formula
```
M(r, p) = 0.55 × Proximity + 0.30 × Reliability + 0.15 × Capability
```

Where:
- `Proximity = 1 / (1 + d_km)` — Haversine distance
- `Reliability = score / 10` — Provider track record
- `Capability = 1.0 if type matches, else 0.0`

---

## 🤖 Google Gemini AI Integration (3 Use Cases)

1. **Request Classification** — Auto-detects emergency type, severity (1-10), and urgency keywords from free text
2. **Situation Report (SITREP)** — Generates professional operational reports from live data
3. **Zone Demand Forecast** — Predicts demand for next 4 hours with risk level and recommendations

---

## 📁 Project Structure

```
emergency/
├── backend/
│   ├── main.py                     # FastAPI application
│   ├── services/
│   │   ├── priority_engine.py      # Bounded priority scoring formula
│   │   ├── matching_engine.py      # Greedy dispatch algorithm
│   │   └── gemini_service.py       # 3 Gemini AI use cases
│   ├── routes/
│   │   ├── requests.py             # CRUD for emergency requests
│   │   ├── dispatch.py             # Matching + provider management
│   │   ├── ai.py                   # Gemini endpoints
│   │   └── stats.py                # Dashboard metrics
│   ├── models/
│   │   └── schemas.py              # Pydantic validation models
│   ├── Dockerfile                  # Cloud Run container
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx       # Role selection landing
│   │   │   ├── Dashboard.jsx       # Admin command center
│   │   │   ├── RequestPage.jsx     # Emergency request form
│   │   │   └── ProviderPage.jsx    # Provider registration + assignments
│   │   ├── components/
│   │   │   ├── MapView.jsx         # Interactive SVG map
│   │   │   ├── PriorityQueue.jsx   # Live ranked request list
│   │   │   ├── RequestForm.jsx     # Form with voice + AI preview
│   │   │   ├── PriorityScoreCard.jsx # Score breakdown visualization
│   │   │   ├── AIInsightCard.jsx   # Zone demand forecast
│   │   │   ├── SitrepModal.jsx     # AI situation report
│   │   │   └── AssignmentCard.jsx  # Provider assignment card
│   │   ├── hooks/
│   │   │   ├── useRequests.js      # Data polling hooks
│   │   │   ├── useGeolocation.js   # Auto GPS detection
│   │   │   └── useVoiceInput.js    # Web Speech API hook
│   │   ├── lib/
│   │   │   ├── api.js              # Axios API client
│   │   │   └── priorityUtils.js    # Visual helpers
│   │   ├── App.jsx
│   │   └── index.css               # Full design system
│   ├── firebase.json               # Hosting config
│   └── package.json
│
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Node.js 18+
- Python 3.11+
- Google Gemini API key ([get one free](https://aistudio.google.com/apikey))

### 1. Clone & Setup
```bash
cd emergency
```

### 2. Start Backend
```bash
cd backend
pip install -r requirements.txt
# Set your Gemini API key:
set GEMINI_API_KEY=your_key_here      # Windows
# export GEMINI_API_KEY=your_key_here  # Mac/Linux
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```
Backend runs at: `http://localhost:8080`

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at: `http://localhost:5173`

### 4. Seed Demo Data
Click **"🌱 Seed Data"** on the dashboard, or:
```bash
curl -X POST http://localhost:8080/api/seed
```

---

## ☁️ Cloud Deployment

### Backend → Google Cloud Run
```bash
cd backend

# Build and deploy
gcloud run deploy sras-api \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key_here"
```

### Frontend → Firebase Hosting
```bash
cd frontend

# Update .env with Cloud Run URL
echo "VITE_API_URL=https://sras-api-xxxxx.run.app" > .env

# Build and deploy
npm run build
firebase deploy --only hosting
```

### Environment Variables Checklist
| Variable | Where | Required |
|----------|-------|----------|
| `GEMINI_API_KEY` | Backend (Cloud Run env) | ✅ For AI features |
| `PORT` | Backend (auto-set by Cloud Run) | Auto |
| `VITE_API_URL` | Frontend (.env) | ✅ For API calls |

---

## 🎮 Demo Flow (Hackathon Presentation)

```
Step 1: Open /request → Speak "My child has a high fever"
Step 2: Watch Gemini auto-classify → type=medical, severity=8
Step 3: Submit → See priority score breakdown (#1 in queue, score 74.0)
Step 4: Switch to /dashboard → Red pin appears on map instantly
Step 5: Click "Run Dispatch" → Nearest provider gets assigned
Step 6: Click zone on map → AI Forecast: "HIGH risk, pre-position 2 units"
Step 7: Click "AI SITREP" → Gemini writes professional ops report
Step 8: Show live Cloud Run URL
```

---

## 🏆 Hackathon Judging Checklist

- [x] Live URL works (Cloud Run + Firebase Hosting)
- [x] Google Gemini AI visibly used (3 use cases)
- [x] Cloud deployment proven
- [x] Real-time updates without page refresh
- [x] Priority score explained to users (explainability card)
- [x] Voice input for accessibility
- [x] Mathematical rigor (bounded priority formula)
- [x] Matching algorithm (greedy with Haversine distance)
- [x] Mobile responsive design
- [x] Dark mode glassmorphism UI

---

## 👥 Team

| Role | Focus Area |
|------|-----------|
| **Member 1** — The Builder | Frontend (React, Map, UI/UX) |
| **Member 2** — The Brain | Backend (FastAPI, Priority Engine, Matching) |
| **Member 3** — The Bridge | AI/Gemini (Classification, SITREP, Forecasting) |
| **Member 4** — The Base | Cloud/DB (Firebase, Cloud Run, Deployment) |

---

## 📄 License

MIT — Built for hackathon, free to use and extend.

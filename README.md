# Scontrini

**Gestisci i tuoi acquisti, migliora le tue scelte.**

App web per digitalizzare scontrini del supermercato tramite OCR e analizzare pattern di spesa con AI.

## 🏗️ Architettura

- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: Python FastAPI + Google Vision OCR + OpenAI Agents
- **Database**: Supabase (PostgreSQL + Storage + Auth)

## 📁 Struttura Progetto

```
scontrini/
├── scontrini-backend/     # API Python FastAPI
├── scontrini-frontend/    # Web app Next.js
├── docs/                  # Documentazione
└── scripts/               # Setup e utility scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Setup Backend

```bash
cd scontrini-backend
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
# Configura .env con le tue API keys
uvicorn app.main:app --reload
```

### Setup Frontend

```bash
cd scontrini-frontend
npm install
copy .env.local.example .env.local
# Configura .env.local
npm run dev
```

## 🌐 Accesso

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## 📚 Documentazione

- [Architecture](docs/architecture.md)
- [Database Schema](docs/database-schema.md)
- [API Documentation](docs/api-docs.md)

## 🧪 Testing

```bash
# Backend
cd scontrini-backend
pytest

# Frontend
cd scontrini-frontend
npm test
```

## 📝 Development Status

- [x] Task 1: Setup iniziale
- [ ] Task 2: Supabase setup
- [ ] Task 3: API esterne
- [ ] Task 4: OCR e parsing
- [ ] Task 5: Agente normalizzazione
- [ ] Task 6-10: Frontend e deploy

## 📄 License

MIT

# Scontrini Backend

API Python FastAPI per elaborazione scontrini con OCR e normalizzazione prodotti tramite AI.

## 🏗️ Stack Tecnologico

- **Framework**: FastAPI
- **OCR**: Google Cloud Vision API
- **AI**: OpenAI GPT-4o-mini
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage

## 📁 Struttura

```
scontrini-backend/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── config.py            # Configurazione
│   ├── api/                 # Endpoints REST
│   ├── services/            # Logica business
│   ├── agents/              # Agenti OpenAI
│   └── utils/               # Utilities
├── tests/                   # Test
└── requirements.txt         # Dipendenze
```

## 🚀 Setup

### 1. Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS/Linux
```

### 2. Installa Dipendenze

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configura Environment

```bash
copy .env.example .env
# Modifica .env con le tue API keys
```

### 4. Avvia Server

```bash
uvicorn app.main:app --reload --port 8000
```

## 🌐 API Documentation

Una volta avviato il server:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

```bash
pytest
pytest --cov=app
```

## 📋 Endpoints Principali

- `GET /` - Root
- `GET /health` - Health check
- `POST /api/v1/receipts/process` - Elabora scontrino (Task 4)
- `GET /api/v1/receipts` - Lista scontrini (Task 4)
- `POST /api/v1/products/normalize` - Normalizza prodotto (Task 5)

## 🔑 Environment Variables

Vedi `.env.example` per lista completa.

## 📝 Development Status

- [x] Setup base
- [ ] OCR service
- [ ] Parser service
- [ ] Agente normalizzazione
- [ ] Endpoints completi

"""
Scontrini Backend API
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Inizializza FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="API per gestione scontrini e analisi acquisti",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "message": "Scontrini API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Eseguito all'avvio del server"""
    print(f"🚀 {settings.PROJECT_NAME} API started")
    print(f"📝 Environment: {settings.ENVIRONMENT}")
    print(f"📚 Docs: http://localhost:{settings.API_PORT}/docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Eseguito alla chiusura del server"""
    print(f"👋 {settings.PROJECT_NAME} API shutdown")

# Include routers API
from app.api.routes import receipts, products

app.include_router(
    receipts.router, 
    prefix="/api/v1/receipts", 
    tags=["receipts"]
)

app.include_router(
    products.router,
    prefix="/api/v1/products",
    tags=["products"]
)
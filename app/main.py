"""FastAPI application for Football Intel."""
from fastapi import FastAPI
from app.models import AnalysisRequest, AnalysisResponse
from app.services.analysis import analyze_fixture

app = FastAPI(
    title="Football Intel API",
    description="A transparent football match-analysis foundation. Estimates use supplied statistics only.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"name": "Football Intel API", "version": app.version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    """Analyze a fixture from user-supplied team statistics."""
    return analyze_fixture(request)

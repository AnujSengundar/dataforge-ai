from fastapi import FastAPI

from backend.app.api.comparisons import router as comparisons_router
from backend.app.api.contracts import router as contracts_router
from backend.app.api.datasets import legacy_router, router as datasets_router
from backend.app.api.validations import router as validations_router


app = FastAPI(
    title="DataForge AI Studio API",
    description="Versioned dataset profiling, contracts, validation, quarantine, and drift APIs.",
    version="0.2.0",
)

app.include_router(datasets_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")
app.include_router(validations_router, prefix="/api")
app.include_router(comparisons_router, prefix="/api")
app.include_router(legacy_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

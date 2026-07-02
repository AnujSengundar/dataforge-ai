from fastapi import FastAPI

from backend.app.api.datasets import router as datasets_router


app = FastAPI(
    title="DataForge AI Studio API",
    description="Metadata engine foundation for CSV uploads and dataset tracking.",
    version="0.1.0",
)

app.include_router(datasets_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

from fastapi import FastAPI

from app.api.router import api_router


app = FastAPI(
    title="Stock & Fund Predictor API",
    version="0.1.0",
    description="Prediction and market-analysis API.",
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

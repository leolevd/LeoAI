
import fastapi
from pathlib import Path
from fastapi import FastAPI, Request
import uvicorn

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from API.forward import forward_openai_request

# Empero's free endpoint is offline for maintenance; exclude it from fallback.
providers = ["nvidia", "gonka", "kilo", "vercel"]

app = FastAPI()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


@app.post("/api/v1/chat/completions")
@limiter.limit("10/minute")
def chat_completions(request: Request, payload: dict):
    for provider in providers:
        response = forward_openai_request(payload, provider)
        if response is not None:
            return response

    return {"error": "No valid response received. Try again later."}


@app.get("/")
def read_root():
    return fastapi.responses.FileResponse("index.html")

@app.get("/tos")
def read_tos():
    return fastapi.responses.FileResponse("terms_of_service.html")

@app.get("/privacy", response_class=fastapi.responses.FileResponse)
def read_privacy():
    return fastapi.responses.FileResponse(
        Path(__file__).with_name("privacy.html"),
        media_type="text/html",
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=26006)

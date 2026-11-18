
import fastapi
import os
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
import uvicorn

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from API.forward import forward_openai_request
from API.keys import lookup_key

KEY_RPM = int(os.environ.get("LEOAI_KEY_RPM", "60"))
if KEY_RPM <= 10:
    raise ValueError("LEOAI_KEY_RPM must be greater than the free tier's 10 RPM")


def authenticate_optional_key(request: Request):
    request.state.api_key_id = None
    authorization = request.headers.get("authorization")
    if authorization is None:
        return
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or len(token) > 256:
        raise HTTPException(401, "Invalid API key", headers={"WWW-Authenticate": "Bearer"})
    record = lookup_key(token)
    if record is None:
        raise HTTPException(401, "Invalid API key", headers={"WWW-Authenticate": "Bearer"})
    request.state.api_key_id = record[0]


def rate_limit_identity(request: Request):
    key_id = request.state.api_key_id
    return f"key:{key_id}" if key_id else f"ip:{get_remote_address(request)}"


def request_limit(key):
    return f"{KEY_RPM}/minute" if key.startswith("key:") else "10/minute"

# Empero's free endpoint is offline for maintenance; exclude it from fallback.
providers = ["nvidia", "gonka", "kilo", "vercel"]

app = FastAPI()

limiter = Limiter(
    key_func=rate_limit_identity,
    storage_uri=os.environ.get("LEOAI_RATE_LIMIT_STORAGE_URI", "memory://"),
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


@app.post("/api/v1/chat/completions", dependencies=[Depends(authenticate_optional_key)])
@limiter.limit(request_limit)
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

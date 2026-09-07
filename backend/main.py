import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth
from routers import raffineries, sessions, commerce, gestion_stock, stock_federation, commerce_federation, transport, crafting

app = FastAPI(title="Irréguliers-Logistics API")

_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(raffineries.router)
app.include_router(sessions.router)
app.include_router(commerce.router)
app.include_router(gestion_stock.router)
app.include_router(stock_federation.router)
app.include_router(commerce_federation.router)
app.include_router(transport.router)
app.include_router(crafting.router)


@app.get("/health")
def health():
    return {"status": "ok"}

# server_main.py
import time
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Image Receiver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "message": "alive"}

@app.get("/health")
def health():
    return PlainTextResponse("ok", status_code=200)

@app.post("/upload")
async def upload_image(
    file: UploadFile,
    seq: str = Form(...),
    client_t0_ns: str = Form(...)
):
    t1 = time.time_ns()
    data = await file.read()
    t2 = time.time_ns()
    return JSONResponse({
        "ok": True,
        "seq": seq,
        "bytes_received": len(data),
        "server_t1_ns": t1,
        "server_t2_ns": t2,
        "client_t0_ns": client_t0_ns,
    })

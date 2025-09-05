import time
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse

app = FastAPI()

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

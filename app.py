"""
app.py
======
FastAPI backend for the AI Resume Builder.
Serves the frontend, exposes scraping / generation APIs with SSE live logs.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import threading
import uuid
import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Optional

# ── paths ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── app ───────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Resume Builder")


# ── task management ───────────────────────────────────────────────────────
class TaskState:
    def __init__(self):
        self.logs: list[str] = []
        self.status: str = "running"           # running | completed | failed
        self.result = None

tasks: dict[str, TaskState] = {}


# ── request models ────────────────────────────────────────────────────────
class ScrapeRequest(BaseModel):
    search_keyword:   str
    countries:        List[str]
    jobs_per_country: int
    date_posted:      str
    email:            str
    password:         str

class GenerateRequest(BaseModel):
    csv_filename:     str
    profile_filename: Optional[str] = None
    resume_filename:  Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════
# SCRAPE
# ═════════════════════════════════════════════════════════════════════════
@app.post("/api/scrape")
async def start_scrape(req: ScrapeRequest):
    task_id = str(uuid.uuid4())
    state   = TaskState()
    tasks[task_id] = state

    def log_cb(msg):
        state.logs.append(msg)

    def _run():
        try:
            from scraper_service import run_scraper
            result = run_scraper(
                search_keyword   = req.search_keyword,
                countries        = req.countries,
                jobs_per_country = req.jobs_per_country,
                date_posted      = req.date_posted,
                log_callback     = log_cb,
                output_dir       = BASE_DIR,
                email            = req.email,
                password         = req.password,
            )
            state.result = result
            state.status = "completed"
        except Exception as e:
            log_cb(f"❌ Fatal error: {e}")
            state.status = "failed"

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


# ═════════════════════════════════════════════════════════════════════════
# GENERATE
# ═════════════════════════════════════════════════════════════════════════
@app.post("/api/generate")
async def start_generate(req: GenerateRequest):
    csv_path = os.path.join(UPLOAD_DIR, req.csv_filename)
    if not os.path.exists(csv_path):
        csv_path = os.path.join(BASE_DIR, req.csv_filename)
    if not os.path.exists(csv_path):
        raise HTTPException(404, "CSV file not found")

    task_id = str(uuid.uuid4())
    state   = TaskState()
    tasks[task_id] = state

    def log_cb(msg):
        state.logs.append(msg)

    profile_path = None
    if req.profile_filename:
        profile_path = os.path.join(UPLOAD_DIR, req.profile_filename)
        if not os.path.exists(profile_path):
            raise HTTPException(404, "Profile TXT file not found")

    resume_path = None
    if req.resume_filename:
        resume_path = os.path.join(UPLOAD_DIR, req.resume_filename)
        if not os.path.exists(resume_path):
            raise HTTPException(404, "Resume PDF file not found")

    def _run():
        try:
            from agent_service import run_agent
            result = run_agent(
                csv_path         = csv_path,
                log_callback     = log_cb,
                output_dir       = OUTPUT_DIR,
                profile_txt_path = profile_path,
                resume_pdf_path  = resume_path,
            )
            state.result = result
            state.status = "completed"
        except Exception as e:
            log_cb(f"❌ Fatal error: {e}")
            state.status = "failed"

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


# ═════════════════════════════════════════════════════════════════════════
# SSE LOG STREAM
# ═════════════════════════════════════════════════════════════════════════
@app.get("/api/logs/{task_id}")
async def stream_logs(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")

    state = tasks[task_id]

    async def _generate():
        sent = 0
        while True:
            # send any new log lines
            while sent < len(state.logs):
                payload = json.dumps({"type": "log", "message": state.logs[sent]})
                yield f"data: {payload}\n\n"
                sent += 1

            # check completion
            if state.status in ("completed", "failed"):
                payload = json.dumps({
                    "type":   "status",
                    "status": state.status,
                    "result": state.result,
                })
                yield f"data: {payload}\n\n"
                break

            await asyncio.sleep(0.4)

    return StreamingResponse(_generate(), media_type="text/event-stream")


# ═════════════════════════════════════════════════════════════════════════
# FILE UPLOAD
# ═════════════════════════════════════════════════════════════════════════
@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}


@app.post("/api/upload-profile")
async def upload_profile(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(400, "Only .txt files are accepted")
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only .pdf files are accepted")
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}


@app.get("/api/download-template")
async def download_template():
    path = os.path.join(BASE_DIR, "resume(3.0).pdf")
    if not os.path.exists(path):
        raise HTTPException(404, "Template resume not found")
    return FileResponse(path, filename="resume_template.pdf", media_type="application/pdf")


# ═════════════════════════════════════════════════════════════════════════
# CSV PREVIEW
# ═════════════════════════════════════════════════════════════════════════
@app.get("/api/csv/preview/{filename}")
async def preview_csv(filename: str):
    for d in (UPLOAD_DIR, BASE_DIR):
        fp = os.path.join(d, filename)
        if os.path.exists(fp):
            df = pd.read_excel(fp) if filename.lower().endswith((".xlsx", ".xls")) else pd.read_csv(fp)
            return {
                "columns": list(df.columns),
                "rows":    df.fillna("").to_dict(orient="records"),
                "total":   len(df),
            }
    raise HTTPException(404, "CSV not found")


# ═════════════════════════════════════════════════════════════════════════
# FILE LISTING
# ═════════════════════════════════════════════════════════════════════════
@app.get("/api/files/csv")
async def list_csvs():
    seen, out = set(), []
    for d in (UPLOAD_DIR, BASE_DIR):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".csv") and f not in seen:
                seen.add(f)
                fp = os.path.join(d, f)
                out.append({
                    "filename": f,
                    "size":     os.path.getsize(fp),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(fp)
                    ).isoformat(),
                })
    return out


@app.get("/api/files/pdf")
async def list_pdfs():
    out = []
    if os.path.isdir(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".pdf"):
                fp = os.path.join(OUTPUT_DIR, f)
                out.append({
                    "filename": f,
                    "size":     os.path.getsize(fp),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(fp)
                    ).isoformat(),
                })
    return out


# ═════════════════════════════════════════════════════════════════════════
# FILE DOWNLOAD
# ═════════════════════════════════════════════════════════════════════════
@app.get("/api/download/{filepath:path}")
async def download_file(filepath: str):
    for d in (OUTPUT_DIR, BASE_DIR, UPLOAD_DIR):
        full = os.path.join(d, filepath)
        if os.path.exists(full):
            return FileResponse(full, filename=os.path.basename(full))
    raise HTTPException(404, "File not found")


# ═════════════════════════════════════════════════════════════════════════
# STATIC FRONTEND  (must be last – catch-all mount)
# ═════════════════════════════════════════════════════════════════════════
app.mount(
    "/",
    StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True),
    name="static",
)

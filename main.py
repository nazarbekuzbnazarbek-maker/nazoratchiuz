from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import os
import secrets
import uuid
import time
 
BASE_DIR = Path(__file__).resolve().parent
 
# O'qituvchi paroli. Render'da Environment bo'limida TEACHER_PASSWORD ni o'zgartiring.
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "focusedu2026")
 
app = FastAPI(title="FocusEdu MVP API", version="1.2")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
lessons_db = {}
students_db = {}
 
 
class StartLessonRequest(BaseModel):
    teacher_id: str = "teacher_1"
    subject: str
    duration_minutes: int = 80
    password: str
 
 
class JoinLessonRequest(BaseModel):
    student_id: str
    token: str = ""
    code: str = ""
 
 
class AwayRequest(BaseModel):
    student_id: str
    away: bool
 
 
def lesson_is_live(lesson: dict) -> bool:
    if not lesson["is_active"]:
        return False
    return (time.time() - lesson["created_at"]) < lesson["duration_minutes"] * 60
 
 
def new_code() -> str:
    live_codes = {l["code"] for l in lessons_db.values() if lesson_is_live(l)}
    while True:
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        if code not in live_codes:
            return code
 
 
# ---------- Frontend fayllari ----------
def _file(name: str, media_type: str):
    path = BASE_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} topilmadi")
    return FileResponse(path, media_type=media_type)
 
 
@app.get("/")
def index():
    return _file("index.html", "text/html")
 
 
@app.get("/style.css")
def style():
    return _file("style.css", "text/css")
 
 
@app.get("/script.js")
def script():
    return _file("script.js", "application/javascript")
 
 
# ---------- API ----------
@app.get("/api/status")
def server_status():
    return {"status": "FocusEdu MVP Server ishlayapti!"}
 
 
@app.post("/api/teacher/start-lesson")
def start_lesson(data: StartLessonRequest):
    if not secrets.compare_digest(data.password, TEACHER_PASSWORD):
        raise HTTPException(status_code=401, detail="Parol noto'g'ri!")
 
    lesson_id = str(uuid.uuid4())[:6]
    token = "TOKEN_" + str(uuid.uuid4())[:8]
    code = new_code()
 
    lessons_db[lesson_id] = {
        "teacher_id": data.teacher_id,
        "subject": data.subject,
        "token": token,
        "code": code,
        "is_active": True,
        "created_at": time.time(),
        "duration_minutes": data.duration_minutes,
    }
 
    return {
        "success": True,
        "lesson_id": lesson_id,
        "qr_token": token,
        "code": code,
        "message": "Dars muvaffaqiyatli boshlandi!",
    }
 
 
@app.post("/api/student/join-lesson")
def join_lesson(data: JoinLessonRequest):
    token = data.token.strip()
    code = data.code.strip()
 
    lesson = None
    lesson_id = None
    for l_id, l in lessons_db.items():
        if not lesson_is_live(l):
            continue
        if (token and l["token"] == token) or (code and l["code"] == code):
            lesson, lesson_id = l, l_id
            break
 
    if not lesson:
        raise HTTPException(status_code=400, detail="Kod yoki havola xato, yoki dars tugagan!")
 
    existing = students_db.get(data.student_id)
    leave_count = existing["away_count"] if existing and existing["lesson_id"] == lesson_id else 0
 
    students_db[data.student_id] = {
        "lesson_id": lesson_id,
        "status": "LOCKED",
        "joined_at": time.time(),
        "away": False,
        "away_count": leave_count,
    }
 
    total = lesson["duration_minutes"] * 60
    remaining = max(0, int(total - (time.time() - lesson["created_at"])))
 
    return {
        "success": True,
        "status": "LOCKED",
        "remaining_seconds": remaining,
        "message": "Telefon bloklandi!",
    }
 
 
@app.get("/api/student/status/{student_id}")
def student_status(student_id: str):
    info = students_db.get(student_id)
    if not info:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
 
    lesson = lessons_db.get(info["lesson_id"])
    if not lesson or not lesson_is_live(lesson):
        info["status"] = "UNLOCKED"
 
    return {"success": True, "status": info["status"]}
 
 
@app.post("/api/student/away")
def student_away(data: AwayRequest):
    info = students_db.get(data.student_id)
    if not info:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
 
    if data.away and not info["away"]:
        info["away_count"] += 1
    info["away"] = data.away
    return {"success": True}
 
 
@app.get("/api/teacher/lesson-stats/{lesson_id}")
def get_lesson_stats(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
 
    students = [
        {"id": s_id, "away": info["away"], "leave_count": info["away_count"]}
        for s_id, info in students_db.items()
        if info["lesson_id"] == lesson_id and info["status"] == "LOCKED"
    ]
    return {
        "success": True,
        "connected_count": len(students),
        "away_count": sum(1 for s in students if s["away"]),
        "students": students,
    }
 
 
@app.post("/api/teacher/end-lesson/{lesson_id}")
def end_lesson(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
 
    lessons_db[lesson_id]["is_active"] = False
    for info in students_db.values():
        if info["lesson_id"] == lesson_id:
            info["status"] = "UNLOCKED"
 
    return {"success": True, "message": "Dars yakunlandi!"}

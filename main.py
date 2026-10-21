from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uuid
import time
 
BASE_DIR = Path(__file__).resolve().parent
 
app = FastAPI(title="FocusEdu MVP API", version="1.1")
 
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
    teacher_id: str
    subject: str
    duration_minutes: int = 80
 
 
class JoinLessonRequest(BaseModel):
    student_id: str
    token: str
 
 
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
    lesson_id = str(uuid.uuid4())[:6]
    token = "TOKEN_" + str(uuid.uuid4())[:8]
 
    lessons_db[lesson_id] = {
        "teacher_id": data.teacher_id,
        "subject": data.subject,
        "token": token,
        "is_active": True,
        "created_at": time.time(),
        "duration_minutes": data.duration_minutes,
    }
 
    return {
        "success": True,
        "lesson_id": lesson_id,
        "qr_token": token,
        "message": "Dars muvaffaqiyatli boshlandi!",
    }
 
 
@app.get("/api/active-lesson")
def get_active_lesson():
    for lesson in reversed(list(lessons_db.values())):
        if lesson["is_active"]:
            return {"success": True, "token": lesson["token"]}
    raise HTTPException(status_code=404, detail="Faol dars topilmadi")
 
 
@app.post("/api/student/join-lesson")
def join_lesson(data: JoinLessonRequest):
    lesson = None
    lesson_id = None
    for l_id, l in lessons_db.items():
        if l["token"] == data.token and l["is_active"]:
            lesson, lesson_id = l, l_id
            break
 
    if not lesson:
        raise HTTPException(status_code=400, detail="Xato yoki eskirgan token!")
 
    students_db[data.student_id] = {
        "lesson_id": lesson_id,
        "status": "LOCKED",
        "joined_at": time.time(),
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
    return {"success": True, "status": info["status"]}
 
 
@app.get("/api/teacher/lesson-stats/{lesson_id}")
def get_lesson_stats(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
 
    connected = [
        s_id for s_id, info in students_db.items()
        if info["lesson_id"] == lesson_id and info["status"] == "LOCKED"
    ]
    return {"success": True, "connected_count": len(connected), "students": connected}
 
 
@app.post("/api/teacher/end-lesson/{lesson_id}")
def end_lesson(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
 
    lessons_db[lesson_id]["is_active"] = False
    for info in students_db.values():
        if info["lesson_id"] == lesson_id:
            info["status"] = "UNLOCKED"
 
    return {"success": True, "message": "Dars yakunlandi!"}

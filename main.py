from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import time

app = FastAPI(title="FocusEdu MVP API", version="1.0")

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

class JoinLessonRequest(BaseModel):
    student_id: str
    token: str

@app.get("/")
def root():
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
        "created_at": time.time()
    }
    
    return {
        "success": True,
        "lesson_id": lesson_id,
        "qr_token": token,
        "message": "Dars muvaffaqiyatli boshlandi!"
    }

@app.get("/api/active-lesson")
def get_active_lesson():
    for l_id, lesson in reversed(list(lessons_db.items())):
        if lesson["is_active"]:
            return {"success": True, "token": lesson["token"]}
    raise HTTPException(status_code=404, detail="Faol dars topilmadi")

@app.post("/api/student/join-lesson")
def join_lesson(data: JoinLessonRequest):
    active_lesson = None
    target_lesson_id = None
    
    for l_id, lesson in lessons_db.items():
        if lesson["token"] == data.token and lesson["is_active"]:
            active_lesson = lesson
            target_lesson_id = l_id
            break
            
    if not active_lesson:
        raise HTTPException(status_code=400, detail="Xato yoki eskirgan token!")
        
    students_db[data.student_id] = {
        "lesson_id": target_lesson_id,
        "status": "LOCKED",
        "joined_at": time.time()
    }
    
    return {"success": True, "status": "LOCKED", "message": "Telefon bloklandi!"}

@app.get("/api/teacher/lesson-stats/{lesson_id}")
def get_lesson_stats(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
        
    connected_students = [
        s_id for s_id, info in students_db.items() 
        if info["lesson_id"] == lesson_id and info["status"] == "LOCKED"
    ]
    
    return {"success": True, "connected_count": len(connected_students), "students": connected_students}

@app.post("/api/teacher/end-lesson/{lesson_id}")
def end_lesson(lesson_id: str):
    if lesson_id not in lessons_db:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
        
    lessons_db[lesson_id]["is_active"] = False
    for s_id, info in students_db.items():
        if info["lesson_id"] == lesson_id:
            info["status"] = "UNLOCKED"
            
    return {"success": True, "message": "Dars yakunlandi!"}
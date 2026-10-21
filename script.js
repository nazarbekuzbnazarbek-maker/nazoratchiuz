const API_URL = "http://192.168.31.226:8000";
const FRONTEND_URL = "http://192.168.31.226:5500";

let currentRole = null;
let currentLessonId = null;
let lessonTimer = null;
let statsInterval = null;
let remainingSeconds = 0;
const studentId = "student_" + Math.random().toString(36).substring(2, 7);

window.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const tokenFromUrl = urlParams.get('token');
  
  if (tokenFromUrl) {
    document.getElementById('role-selection').classList.add('hidden');
    document.getElementById('student-panel').classList.remove('hidden');
    await joinLessonWithToken(tokenFromUrl);
  }
});

function selectRole(role) {
  currentRole = role;
  document.getElementById('role-selection').classList.add('hidden');
  
  if (role === 'teacher') {
    document.getElementById('teacher-panel').classList.remove('hidden');
  } else {
    document.getElementById('student-panel').classList.remove('hidden');
    initStudentScanner();
  }
}

async function startTeacherLesson() {
  const subject = document.getElementById('subject-name').value || "Oliy Matematika";
  try {
    const response = await fetch(`${API_URL}/api/teacher/start-lesson`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ teacher_id: "teacher_1", subject: subject })
    });
    
    const data = await response.json();
    if (data.success) {
      currentLessonId = data.lesson_id;
      document.getElementById('start-lesson-form').classList.add('hidden');
      document.getElementById('active-lesson-info').classList.remove('hidden');
      document.getElementById('display-subject').innerText = subject;

      const joinLink = `${FRONTEND_URL}/?token=${data.qr_token}`;
      const qrContainer = document.getElementById('qrcode-container');
      qrContainer.innerHTML = "";
      
      new QRCode(qrContainer, { text: joinLink, width: 180, height: 180 });
      statsInterval = setInterval(fetchLessonStats, 3000);
    }
  } catch (error) {
    alert("Serverga ulanishda xatolik!");
  }
}

async function fetchLessonStats() {
  if (!currentLessonId) return;
  try {
    const response = await fetch(`${API_URL}/api/teacher/lesson-stats/${currentLessonId}`);
    const data = await response.json();
    if (data.success) {
      document.getElementById('connected-count').innerText = data.connected_count;
    }
  } catch (error) { console.error(error); }
}

async function endTeacherLesson() {
  if (!currentLessonId) return;
  try {
    await fetch(`${API_URL}/api/teacher/end-lesson/${currentLessonId}`, { method: "POST" });
    clearInterval(statsInterval);
    alert("Dars yakunlandi!");
    location.reload();
  } catch (error) { console.error(error); }
}

function initStudentScanner() {
  try {
    const html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", { fps: 10, qrbox: 250 });
    html5QrcodeScanner.render(async (decodedText) => {
      let token = decodedText;
      if (decodedText.includes("token=")) {
        token = new URL(decodedText).searchParams.get("token");
      }
      await joinLessonWithToken(token);
      html5QrcodeScanner.clear();
    });
  } catch (e) { console.log(e); }
}

async function simulateScan() {
  try {
    const response = await fetch(`${API_URL}/api/active-lesson`);
    const data = await response.json();
    if (data.success && data.token) {
      await joinLessonWithToken(data.token);
    }
  } catch (error) {
    alert("Faol dars topilmadi!");
  }
}

async function joinLessonWithToken(token) {
  try {
    const response = await fetch(`${API_URL}/api/student/join-lesson`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, token: token })
    });
    const data = await response.json();
    if (response.ok && data.success) {
      lockStudentPhone();
    } else {
      alert(data.detail || "Xato token!");
    }
  } catch (error) { alert("Serverga ulanib bo'lmadi!"); }
}

function lockStudentPhone() {
  document.getElementById('student-scanner-box').classList.add('hidden');
  document.getElementById('lock-screen').classList.remove('hidden');
  remainingSeconds = 80 * 60;
  startTimer();
  window.addEventListener('blur', () => {
    alert("⚠️ OGOHLANTIRISH: Dars vaqtida ilovadan chiqish taqiqlanadi!");
  });
}

function startTimer() {
  lessonTimer = setInterval(() => {
    if (remainingSeconds <= 0) {
      clearInterval(lessonTimer);
      alert("Dars tugadi!");
      location.reload();
      return;
    }
    remainingSeconds--;
    const mins = Math.floor(remainingSeconds / 60);
    const secs = remainingSeconds % 60;
    document.getElementById('countdown-timer').innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, 1000);
}

function requestEmergency() {
  alert("O'qituvchiga favqulodda qo'ng'iroq yuborildi.");
}

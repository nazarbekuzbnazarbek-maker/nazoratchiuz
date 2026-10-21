// Frontend va backend bitta serverda (FastAPI) ishlaydi.
const API_URL = window.location.origin;
const FRONTEND_URL = window.location.origin;

let currentRole = null;
let currentLessonId = null;
let lessonTimer = null;
let statsInterval = null;
let statusInterval = null;
let remainingSeconds = 0;
let isLocked = false;
let awayTrackingAdded = false;
let wakeLock = null;

// Talaba ID sahifa yangilanganda o'zgarmasligi uchun saqlab qo'yiladi
function getStudentId() {
  try {
    let id = localStorage.getItem('focusedu_student_id');
    if (!id) {
      id = "student_" + Math.random().toString(36).substring(2, 9);
      localStorage.setItem('focusedu_student_id', id);
    }
    return id;
  } catch (e) {
    return "student_" + Math.random().toString(36).substring(2, 9);
  }
}
const studentId = getStudentId();

window.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const tokenFromUrl = urlParams.get('token');

  if (tokenFromUrl) {
    document.getElementById('role-selection').classList.add('hidden');
    document.getElementById('student-panel').classList.remove('hidden');
    await joinLesson({ token: tokenFromUrl });
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

// ---------------- O'QITUVCHI ----------------
async function startTeacherLesson() {
  const subject = document.getElementById('subject-name').value || "Oliy Matematika";
  const duration = parseInt(document.getElementById('lesson-duration').value, 10) || 80;
  const password = document.getElementById('teacher-password').value;

  if (!password) {
    alert("O'qituvchi parolini kiriting!");
    return;
  }

  try {
    const response = await fetch(`${API_URL}/api/teacher/start-lesson`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        teacher_id: "teacher_1",
        subject: subject,
        duration_minutes: duration,
        password: password
      })
    });

    if (response.status === 401) {
      alert("Parol noto'g'ri!");
      return;
    }

    const data = await response.json();
    if (data.success) {
      currentLessonId = data.lesson_id;
      document.getElementById('start-lesson-form').classList.add('hidden');
      document.getElementById('active-lesson-info').classList.remove('hidden');
      document.getElementById('display-subject').innerText = subject;
      document.getElementById('lesson-code').innerText = data.code;

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
      document.getElementById('away-count').innerText = data.away_count;
    }
  } catch (error) { console.error(error); }
}

async function endTeacherLesson() {
  if (!currentLessonId) return;
  try {
    await fetch(`${API_URL}/api/teacher/end-lesson/${currentLessonId}`, { method: "POST" });
    clearInterval(statsInterval);
    alert("Dars yakunlandi!");
    location.href = FRONTEND_URL + "/";
  } catch (error) { console.error(error); }
}

// ---------------- TALABA ----------------
function initStudentScanner() {
  try {
    const html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", { fps: 10, qrbox: 250 });
    html5QrcodeScanner.render(async (decodedText) => {
      let token = decodedText;
      if (decodedText.includes("token=")) {
        token = new URL(decodedText).searchParams.get("token");
      }
      await joinLesson({ token: token });
      html5QrcodeScanner.clear();
    });
  } catch (e) { console.log(e); }
}

async function joinByCode() {
  const code = document.getElementById('join-code').value.trim();
  if (code.length !== 6) {
    alert("6 xonali dars kodini kiriting!");
    return;
  }
  await joinLesson({ code: code });
}

async function joinLesson(payload) {
  try {
    const response = await fetch(`${API_URL}/api/student/join-lesson`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: studentId,
        token: payload.token || "",
        code: payload.code || ""
      })
    });
    const data = await response.json();
    if (response.ok && data.success) {
      lockStudentPhone(data.remaining_seconds);
    } else {
      alert(data.detail || "Xatolik!");
    }
  } catch (error) { alert("Serverga ulanib bo'lmadi!"); }
}

function lockStudentPhone(seconds) {
  isLocked = true;
  document.getElementById('student-scanner-box').classList.add('hidden');
  document.getElementById('lock-screen').classList.remove('hidden');
  remainingSeconds = seconds || 80 * 60;
  startTimer();

  // O'qituvchi darsni tugatsa, telefon avtomatik ochiladi
  statusInterval = setInterval(checkStudentStatus, 3000);

  requestWakeLock();
  setupAwayTracking();
}

// Ekran o'chib qolmasligi uchun
async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
    }
  } catch (e) { console.log(e); }
}

// Butun ekran rejimi (tugma bosilganda ishlaydi)
function enterFullscreen() {
  try {
    const el = document.documentElement;
    const fn = el.requestFullscreen || el.webkitRequestFullscreen;
    if (fn) {
      const p = fn.call(el);
      if (p && p.catch) p.catch(() => {});
    }
  } catch (e) { console.log(e); }
}

function reportAway(away) {
  fetch(`${API_URL}/api/student/away`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: studentId, away: away }),
    keepalive: true
  }).catch(() => {});
}

function showAwayWarning() {
  const banner = document.getElementById('away-warning');
  if (!banner) return;
  banner.classList.remove('hidden');
  setTimeout(() => banner.classList.add('hidden'), 6000);
}

// Talaba ilovadan / sahifadan chiqsa, o'qituvchiga xabar boradi
function setupAwayTracking() {
  if (awayTrackingAdded) return;
  awayTrackingAdded = true;

  document.addEventListener('visibilitychange', () => {
    if (!isLocked) return;
    if (document.hidden) {
      reportAway(true);
    } else {
      reportAway(false);
      showAwayWarning();
      requestWakeLock();
    }
  });
}

async function checkStudentStatus() {
  try {
    const response = await fetch(`${API_URL}/api/student/status/${studentId}`);
    const data = await response.json();
    if (data.success && data.status === "UNLOCKED") {
      isLocked = false;
      clearInterval(statusInterval);
      clearInterval(lessonTimer);
      alert("Dars tugadi! Telefoningiz blokdan chiqarildi.");
      location.href = FRONTEND_URL + "/";
    }
  } catch (error) { console.error(error); }
}

function renderTimer() {
  const mins = Math.floor(remainingSeconds / 60);
  const secs = remainingSeconds % 60;
  document.getElementById('countdown-timer').innerText =
    `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function startTimer() {
  renderTimer();
  lessonTimer = setInterval(() => {
    if (remainingSeconds <= 0) {
      isLocked = false;
      clearInterval(lessonTimer);
      clearInterval(statusInterval);
      alert("Dars tugadi!");
      location.href = FRONTEND_URL + "/";
      return;
    }
    remainingSeconds--;
    renderTimer();
  }, 1000);
}

function requestEmergency() {
  alert("O'qituvchiga favqulodda qo'ng'iroq yuborildi.");
}

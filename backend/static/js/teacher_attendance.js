const enrollmentSelect = document.getElementById("enrollmentSelect");
const totalEl = document.getElementById("total");
const attendedEl = document.getElementById("attended");
const statusEl = document.getElementById("status");
const saveBtn = document.getElementById("saveBtn");

let enrollments = [];

async function loadEnrollments() {
  const res = await fetch("/teacher/enrollments");
  enrollments = await res.json();

  enrollmentSelect.innerHTML = "";
  enrollments.forEach((e, idx) => {
    const opt = document.createElement("option");
    opt.value = idx;
    opt.textContent = `${e.student_name} | ${e.code} | ${e.semester} ${e.year}`;
    enrollmentSelect.appendChild(opt);
  });

  if (enrollments.length === 0) {
    statusEl.textContent = "No assigned enrollments found. Admin must assign courses first.";
  }
}

saveBtn.addEventListener("click", async () => {
  const idx = parseInt(enrollmentSelect.value, 10);
  const e = enrollments[idx];
  if (!e) return;

  const payload = {
    enroll_id: e.enroll_id,
    total_class: parseInt(totalEl.value || "0", 10),
    attended_class: parseInt(attendedEl.value || "0", 10)
  };

  const res = await fetch("/teacher/submit-attendance", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  statusEl.textContent = res.ok
    ? `✅ ${data.message} | Attendance: ${data.attendance_percent}%`
    : `❌ ${data.error || "Failed"}`;
});

loadEnrollments();

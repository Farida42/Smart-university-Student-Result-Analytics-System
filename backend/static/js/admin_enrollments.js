const studentSel = document.getElementById("student");
const courseSel = document.getElementById("course");
const semSel = document.getElementById("semester");
const statusEl = document.getElementById("status");
const listEl = document.getElementById("list");

function tableHTML(headers, rows) {
  let html = `<table class="t"><thead><tr>`;
  headers.forEach(h => html += `<th>${h}</th>`);
  html += `</tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`;
  });
  html += `</tbody></table>`;
  return html;
}

async function loadMeta() {
  const res = await fetch("/admin/enroll-meta");
  const data = await res.json();

  studentSel.innerHTML = "";
  data.students.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.student_id;
    opt.textContent = `${s.name} (${s.email}) [${s.dept || ""} ${s.batch || ""}-${s.section || ""}]`;
    studentSel.appendChild(opt);
  });

  courseSel.innerHTML = "";
  data.courses.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.course_id;
    opt.textContent = `${c.code} - ${c.title}`;
    courseSel.appendChild(opt);
  });

  semSel.innerHTML = "";
  data.semesters.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.semester_id;
    opt.textContent = `${s.name} ${s.year}`;
    semSel.appendChild(opt);
  });
}

async function enroll() {
  const payload = {
    student_id: parseInt(studentSel.value, 10),
    course_id: parseInt(courseSel.value, 10),
    semester_id: parseInt(semSel.value, 10)
  };

  const res = await fetch("/admin/api/enroll", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  statusEl.textContent = res.ok
    ? `✅ ${data.message} (enroll_id=${data.enroll_id})`
    : `❌ ${data.error || "Failed"}`;
  loadEnrollments();
}

async function loadEnrollments() {
  const res = await fetch("/admin/api/enrollments");
  const rows = await res.json();

  const headers = ["Student", "Course", "Semester", "Dept", "Batch", "Sec", "Action"];
  const body = rows.map(r => ([
    `${r.student_name}<br><span class="muted">${r.email}</span>`,
    `${r.code} - ${r.title}`,
    `${r.semester} ${r.year}`,
    r.dept || "",
    r.batch || "",
    r.section || "",
    `<button class="btn" data-del="${r.enroll_id}" style="width:auto;padding:6px 10px;background:#ef4444;">Del</button>`
  ]));

  listEl.innerHTML = tableHTML(headers, body);

  listEl.querySelectorAll("button[data-del]").forEach(btn => {
    btn.addEventListener("click", () => delEnroll(btn.dataset.del));
  });
}

async function delEnroll(id) {
  if (!confirm("Delete this enrollment?")) return;
  const res = await fetch(`/admin/api/enrollments/${id}`, { method: "DELETE" });
  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ Failed`;
  loadEnrollments();
}

document.getElementById("enrollBtn").addEventListener("click", enroll);

loadMeta();
loadEnrollments();

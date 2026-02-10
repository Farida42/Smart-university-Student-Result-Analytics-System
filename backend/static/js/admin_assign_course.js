const tSel = document.getElementById("teacher");
const cSel = document.getElementById("course");
const sSel = document.getElementById("semester");
const sectionEl = document.getElementById("section");
const statusEl = document.getElementById("status");

async function loadMeta() {
  const res = await fetch("/admin/meta");
  const data = await res.json();

  data.teachers.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t.teacher_id;
    opt.textContent = `${t.name} (${t.email})`;
    tSel.appendChild(opt);
  });

  data.courses.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.course_id;
    opt.textContent = `${c.code} - ${c.title}`;
    cSel.appendChild(opt);
  });

  data.semesters.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.semester_id;
    opt.textContent = `${s.name} ${s.year}`;
    sSel.appendChild(opt);
  });
}

document.getElementById("assignBtn").addEventListener("click", async () => {
  const payload = {
    teacher_id: parseInt(tSel.value, 10),
    course_id: parseInt(cSel.value, 10),
    semester_id: parseInt(sSel.value, 10),
    section: sectionEl.value.trim()
  };

  const res = await fetch("/admin/assign-course", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ ${data.error || "Failed"}`;
});

loadMeta();

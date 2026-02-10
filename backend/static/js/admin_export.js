const semSel = document.getElementById("semester");
const courseSel = document.getElementById("course");
const qEl = document.getElementById("q");

async function loadMeta() {
  const res = await fetch("/admin/export/meta");
  const data = await res.json();

  data.semesters.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.semester_id;
    opt.textContent = `${s.name} ${s.year}`;
    semSel.appendChild(opt);
  });

  data.courses.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.course_id;
    opt.textContent = `${c.code} - ${c.title}`;
    courseSel.appendChild(opt);
  });
}

document.getElementById("downloadBtn").addEventListener("click", () => {
  const params = new URLSearchParams();
  if (semSel.value) params.set("semester_id", semSel.value);
  if (courseSel.value) params.set("course_id", courseSel.value);
  if (qEl.value.trim()) params.set("q", qEl.value.trim());

  window.location.href = `/admin/export/results.csv?${params.toString()}`;
});

loadMeta();

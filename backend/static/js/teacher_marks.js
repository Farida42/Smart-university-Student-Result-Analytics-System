const enrollmentSelect = document.getElementById("enrollmentSelect");
const marksForm = document.getElementById("marksForm");
const statusEl = document.getElementById("status");
const saveBtn = document.getElementById("saveBtn");

let enrollments = [];
let components = [];

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

  if (enrollments.length > 0) {
    await loadComponents();
  } else {
    marksForm.innerHTML = `<p class="muted">No assigned enrollments found. Admin must assign courses first.</p>`;
  }
}

async function loadComponents() {
  const idx = parseInt(enrollmentSelect.value, 10);
  const e = enrollments[idx];
  if (!e) return;

  const res = await fetch(`/teacher/components/${e.course_id}`);
  components = await res.json();

  renderMarksForm(components);
}

function renderMarksForm(comps) {
  if (!comps.length) {
    marksForm.innerHTML = `<p class="muted">No mark components found for this course.</p>`;
    return;
  }

  let html = `<table class="t">
    <thead>
      <tr><th>Component</th><th>Max</th><th>Weight</th><th>Obtained</th></tr>
    </thead>
    <tbody>`;

  comps.forEach(c => {
    html += `<tr>
      <td>${c.name}</td>
      <td>${parseFloat(c.max_marks).toFixed(2)}</td>
      <td>${parseFloat(c.weight).toFixed(2)}%</td>
      <td><input data-comp="${c.comp_id}" type="number" min="0" step="0.01" placeholder="0" /></td>
    </tr>`;
  });

  html += `</tbody></table>`;
  marksForm.innerHTML = html;
}

async function saveMarks() {
  const idx = parseInt(enrollmentSelect.value, 10);
  const e = enrollments[idx];
  if (!e) return;

  const items = [];
  marksForm.querySelectorAll("input[data-comp]").forEach(inp => {
    const comp_id = parseInt(inp.dataset.comp, 10);
    const obtained_marks = parseFloat(inp.value || "0");
    items.push({ comp_id, obtained_marks });
  });

  const payload = {
    enroll_id: e.enroll_id,
    course_id: e.course_id,
    items
  };

  const res = await fetch("/teacher/submit-marks", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (res.ok) {
    statusEl.innerHTML =
      `✅ ${data.message}<br/>Total: <b>${data.total_percent}%</b> | Grade: <b>${data.letter_grade}</b> | GP: <b>${data.grade_point}</b>`;
  } else {
    statusEl.textContent = `❌ ${data.error || "Failed to save marks"}`;
  }
}

enrollmentSelect.addEventListener("change", loadComponents);
saveBtn.addEventListener("click", saveMarks);

loadEnrollments();

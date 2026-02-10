const qEl = document.getElementById("q");
const listEl = document.getElementById("list");
const statusEl = document.getElementById("status");

const idEl = document.getElementById("student_id");
const nameEl = document.getElementById("name");
const emailEl = document.getElementById("email");
const deptEl = document.getElementById("dept");
const batchEl = document.getElementById("batch");
const sectionEl = document.getElementById("section");

function renderTable(rows) {
  let html = `<table class="t"><thead><tr>
    <th>Name</th><th>Email</th><th>Dept</th><th>Batch</th><th>Sec</th><th>Action</th>
  </tr></thead><tbody>`;

  rows.forEach(r => {
    html += `<tr>
      <td>${r.name}</td>
      <td>${r.email}</td>
      <td>${r.dept || ""}</td>
      <td>${r.batch || ""}</td>
      <td>${r.section || ""}</td>
      <td>
        <button data-edit="${r.student_id}" class="btn" style="width:auto;padding:6px 10px;">Edit</button>
        <button data-del="${r.student_id}" class="btn" style="width:auto;padding:6px 10px;background:#ef4444;">Del</button>
      </td>
    </tr>`;
  });

  html += `</tbody></table>`;
  listEl.innerHTML = html;

  listEl.querySelectorAll("button[data-edit]").forEach(btn => {
    btn.addEventListener("click", () => onEdit(btn.dataset.edit, rows));
  });
  listEl.querySelectorAll("button[data-del]").forEach(btn => {
    btn.addEventListener("click", () => onDelete(btn.dataset.del));
  });
}

async function load() {
  const q = encodeURIComponent(qEl.value.trim());
  const res = await fetch(`/admin/api/students?q=${q}`);
  const rows = await res.json();
  renderTable(rows);
}

function onEdit(id, rows) {
  const r = rows.find(x => String(x.student_id) === String(id));
  if (!r) return;
  idEl.value = r.student_id;
  nameEl.value = r.name;
  emailEl.value = r.email;
  deptEl.value = r.dept || "";
  batchEl.value = r.batch || "";
  sectionEl.value = r.section || "";
  statusEl.textContent = "Editing mode enabled.";
}

async function onDelete(id) {
  if (!confirm("Delete this student (and user account)?")) return;
  const res = await fetch(`/admin/api/students/${id}`, { method: "DELETE" });
  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ ${data.error || "Failed"}`;
  resetForm();
  load();
}

async function save() {
  const payload = {
    name: nameEl.value.trim(),
    email: emailEl.value.trim(),
    dept: deptEl.value.trim(),
    batch: batchEl.value.trim(),
    section: sectionEl.value.trim()
  };

  const id = idEl.value.trim();
  const url = id ? `/admin/api/students/${id}` : "/admin/api/students";
  const method = id ? "PUT" : "POST";

  const res = await fetch(url, {
    method,
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ ${data.error || "Failed"}`;
  if (res.ok) resetForm();
  load();
}

function resetForm() {
  idEl.value = "";
  nameEl.value = "";
  emailEl.value = "";
  deptEl.value = "";
  batchEl.value = "";
  sectionEl.value = "";
}

document.getElementById("searchBtn").addEventListener("click", load);
document.getElementById("saveBtn").addEventListener("click", save);
document.getElementById("resetBtn").addEventListener("click", () => {
  resetForm();
  statusEl.textContent = "";
});

load();

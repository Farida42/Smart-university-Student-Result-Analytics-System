const qEl = document.getElementById("q");
const listEl = document.getElementById("list");
const statusEl = document.getElementById("status");

const idEl = document.getElementById("course_id");
const codeEl = document.getElementById("code");
const titleEl = document.getElementById("title");
const creditEl = document.getElementById("credit");

function renderTable(rows) {
  let html = `<table class="t"><thead><tr>
    <th>Code</th><th>Title</th><th>Credit</th><th>Action</th>
  </tr></thead><tbody>`;

  rows.forEach(r => {
    html += `<tr>
      <td>${r.code}</td>
      <td>${r.title}</td>
      <td>${parseFloat(r.credit).toFixed(1)}</td>
      <td>
        <button data-edit="${r.course_id}" class="btn" style="width:auto;padding:6px 10px;">Edit</button>
        <button data-del="${r.course_id}" class="btn" style="width:auto;padding:6px 10px;background:#ef4444;">Del</button>
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
  const res = await fetch(`/admin/api/courses?q=${q}`);
  const rows = await res.json();
  renderTable(rows);
}

function onEdit(id, rows) {
  const r = rows.find(x => String(x.course_id) === String(id));
  if (!r) return;
  idEl.value = r.course_id;
  codeEl.value = r.code;
  titleEl.value = r.title;
  creditEl.value = r.credit;
  statusEl.textContent = "Editing mode enabled.";
}

async function onDelete(id) {
  if (!confirm("Delete this course?")) return;
  const res = await fetch(`/admin/api/courses/${id}`, { method: "DELETE" });
  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ ${data.error || "Failed"}`;
  resetForm();
  load();
}

async function save() {
  const payload = {
    code: codeEl.value.trim(),
    title: titleEl.value.trim(),
    credit: parseFloat(creditEl.value || "3.0")
  };

  const id = idEl.value.trim();
  const url = id ? `/admin/api/courses/${id}` : "/admin/api/courses";
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
  codeEl.value = "";
  titleEl.value = "";
  creditEl.value = "3.0";
}

document.getElementById("searchBtn").addEventListener("click", load);
document.getElementById("saveBtn").addEventListener("click", save);
document.getElementById("resetBtn").addEventListener("click", () => {
  resetForm();
  statusEl.textContent = "";
});

load();

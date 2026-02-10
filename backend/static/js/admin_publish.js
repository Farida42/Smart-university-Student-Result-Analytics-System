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

async function loadDrafts() {
  const res = await fetch("/admin/drafts");
  const drafts = await res.json();

  const headers = ["Student", "Course", "Semester", "Percent", "Grade", "GP", "Action"];
  const body = drafts.map(d => ([
    `${d.student_name}<br><span class="muted">${d.email}</span>`,
    `${d.code} - ${d.title}`,
    `${d.semester} ${d.year}`,
    `${parseFloat(d.total_percent).toFixed(2)}%`,
    d.letter_grade,
    parseFloat(d.grade_point).toFixed(2),
    `<button class="btn" data-id="${d.result_id}" style="width:auto;padding:8px 12px;">Publish</button>`
  ]));

  const wrap = document.getElementById("draftTable");
  wrap.innerHTML = tableHTML(headers, body);

  wrap.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => publishOne(btn.dataset.id));
  });
}

async function publishOne(id) {
  const res = await fetch("/admin/publish-result", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ result_id: parseInt(id, 10), publish: true })
  });

  const data = await res.json();
  document.getElementById("status").textContent = res.ok ? `✅ ${data.message}` : `❌ Failed`;
  loadDrafts();
}

loadDrafts();

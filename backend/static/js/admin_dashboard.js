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

async function loadGradeChart() {
  const res = await fetch("/admin/analytics/grade-distribution");
  const data = await res.json();

  const ctx = document.getElementById("gradeChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels || [],
      datasets: [{ label: "Count", data: data.values || [] }]
    },
    options: { responsive: true }
  });
}

async function loadCourseDifficulty() {
  const res = await fetch("/admin/analytics/course-difficulty");
  const rows = await res.json();

  const headers = ["Course", "Avg %", "Fail Rate %", "Fail", "Total"];
  const body = rows.map(r => ([
    `${r.code} - ${r.title}`,
    r.avg_percent.toFixed(2),
    r.fail_rate.toFixed(2),
    r.fail_count,
    r.total_count
  ]));

  document.getElementById("courseTable").innerHTML = tableHTML(headers, body);
}

async function loadTopStudents() {
  const res = await fetch("/admin/analytics/top-students");
  const rows = await res.json();

  const headers = ["Name", "Email", "Avg GP", "Courses"];
  const body = rows.map(r => ([r.name, r.email, r.avg_gp, r.courses_count]));

  document.getElementById("topTable").innerHTML = tableHTML(headers, body);
}

async function loadRiskStudents() {
  const res = await fetch("/admin/analytics/at-risk");
  const rows = await res.json();

  const headers = ["Name", "Email", "Avg GP", "F Count", "Courses"];
  const body = rows.map(r => ([r.name, r.email, r.avg_gp, r.f_count, r.courses_count]));

  document.getElementById("riskTable").innerHTML = tableHTML(headers, body);
}

loadGradeChart();
loadCourseDifficulty();
loadTopStudents();
loadRiskStudents();

async function loadCGPA() {
  const res = await fetch("/student/cgpa");
  const data = await res.json();

  const cgpaBox = document.getElementById("cgpaBox");
  if (cgpaBox) {
    cgpaBox.innerHTML = `CGPA: <b>${data.cgpa}</b> <span class="muted">(Credits: ${data.total_credits})</span>`;
  }
}

async function loadRisk() {
  const res = await fetch("/student/risk-status");
  const data = await res.json();

  const riskBox = document.getElementById("riskBox");
  if (!riskBox) return;

  let label = "Low";
  if (data.risk === "medium") label = "Medium";
  if (data.risk === "high") label = "High";

  riskBox.innerHTML =
    `Risk: <b>${label}</b><br/>Avg Attendance: ${data.avg_attendance}% | Avg GP: ${data.avg_gp} | F: ${data.f_count}`;
}

loadCGPA();
loadRisk();

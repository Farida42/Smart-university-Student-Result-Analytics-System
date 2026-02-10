async function loadGpaTrend() {
  const res = await fetch("/student/gpa-trend");
  const data = await res.json();

  const ctx = document.getElementById("gpaChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels || [],
      datasets: [{
        label: "GPA",
        data: data.gpa || [],
        tension: 0.2
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { suggestedMin: 0, suggestedMax: 4 }
      }
    }
  });
}

loadGpaTrend();

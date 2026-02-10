const emailEl = document.getElementById("email");
const pwEl = document.getElementById("pw");
const statusEl = document.getElementById("status");

document.getElementById("resetBtn").addEventListener("click", async () => {
  const payload = {
    email: emailEl.value.trim(),
    new_password: pwEl.value.trim()
  };

  const res = await fetch("/admin/api/reset-password", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  statusEl.textContent = res.ok ? `✅ ${data.message}` : `❌ ${data.error || "Failed"}`;
});

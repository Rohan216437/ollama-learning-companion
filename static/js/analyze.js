(function () {
  const form = document.getElementById("analyzeForm");
  if (!form) return;

  const btn = document.getElementById("analyzeBtn");
  const loadingRow = document.getElementById("loadingRow");
  const loadingText = document.getElementById("loadingText");
  const errorBox = document.getElementById("errorBox");
  const urlInput = document.getElementById("videoUrl");

  const stages = [
    "Fetching transcript…",
    "Reading through the video…",
    "Asking Ollama to draft your study guide…",
    "Almost there…",
  ];

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    errorBox.classList.add("d-none");

    const url = urlInput.value.trim();
    if (!url) return;

    btn.disabled = true;
    btn.textContent = "Working…";
    loadingRow.classList.add("active");

    let stageIndex = 0;
    loadingText.textContent = stages[0];
    const stageTimer = setInterval(() => {
      stageIndex = Math.min(stageIndex + 1, stages.length - 1);
      loadingText.textContent = stages[stageIndex];
    }, 4000);

    try {
      const resp = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await resp.json();

      if (data.ok) {
        window.location.href = data.redirect;
        return;
      }
      showError(data.error || "Something went wrong. Please try again.");
    } catch (err) {
      showError("Network error — please check your connection and try again.");
    } finally {
      clearInterval(stageTimer);
      btn.disabled = false;
      btn.textContent = "Generate study guide";
      loadingRow.classList.remove("active");
    }
  });

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove("d-none");
  }
})();

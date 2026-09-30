(function () {
  const wrap = document.getElementById("quizWrap");
  if (!wrap) return;

  const questions = Array.from(wrap.querySelectorAll(".lc-quiz-q"));
  const scoreBox = document.getElementById("quizScore");
  const answered = new Set();

  questions.forEach((qEl) => {
    const correctIdx = parseInt(qEl.dataset.correct, 10);
    const opts = Array.from(qEl.querySelectorAll(".lc-quiz-opt"));
    const explain = qEl.querySelector(".lc-quiz-explain");

    opts.forEach((optEl) => {
      optEl.addEventListener("click", () => {
        if (qEl.dataset.locked) return;
        qEl.dataset.locked = "1";
        answered.add(qEl);

        const chosenIdx = parseInt(optEl.dataset.idx, 10);
        opts.forEach((o) => {
          const idx = parseInt(o.dataset.idx, 10);
          if (idx === correctIdx) o.classList.add("correct");
          else if (idx === chosenIdx) o.classList.add("incorrect");
        });
        explain.classList.add("show");
        updateScore();
      });
    });
  });

  function updateScore() {
    if (answered.size === 0) {
      scoreBox.textContent = "";
      return;
    }
    let correct = 0;
    answered.forEach((qEl) => {
      const correctIdx = parseInt(qEl.dataset.correct, 10);
      const chosen = qEl.querySelector(".lc-quiz-opt.incorrect, .lc-quiz-opt.correct.selected");
      const correctPicked = qEl.querySelector(".lc-quiz-opt.correct");
      const incorrectPicked = qEl.querySelector(".lc-quiz-opt.incorrect");
      if (correctPicked && !incorrectPicked) correct += 1;
    });
    scoreBox.innerHTML = `<strong>${answered.size}/${questions.length}</strong> answered · <strong>${correct}</strong> correct so far`;
  }
})();

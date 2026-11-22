const goalForm = document.getElementById("goalForm");

if (goalForm) {
  goalForm.addEventListener("submit", function () {
    const button = document.getElementById("goalButton");

    setTimeout(function () {
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Myślę...';
    }, 0);
  });
}
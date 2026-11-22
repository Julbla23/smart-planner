document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("overlapModal");
  if (modalElement) {
    new bootstrap.Modal(modalElement).show();
  }
});
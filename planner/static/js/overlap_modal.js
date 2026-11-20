// Okienko "Konflikt terminów".
// Szablon wstawia je do strony tylko wtedy, gdy nowe zadanie nachodzi na inne,
// a ten skrypt otwiera je automatycznie po wczytaniu strony.
document.addEventListener("DOMContentLoaded", function () {
  const modalElement = document.getElementById("overlapModal");
  if (modalElement) {
    new bootstrap.Modal(modalElement).show();
  }
});
// Okienko potwierdzenia usunięcia zadania.
// Przycisk "Usuń" niesie dane w atrybutach data-task-name i data-delete-url,
// a ten skrypt wpisuje je do okienka tuż przed jego otwarciem.
const deleteModal = document.getElementById("deleteModal");

if (deleteModal) {
  deleteModal.addEventListener("show.bs.modal", function (event) {
    const button = event.relatedTarget;   // przycisk "Usuń", który kliknięto
    document.getElementById("deleteTaskName").textContent = button.dataset.taskName;
    document.getElementById("deleteForm").action = button.dataset.deleteUrl;
  });
}
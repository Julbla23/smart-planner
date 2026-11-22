const deleteModal = document.getElementById("deleteModal");

if (deleteModal) {
  deleteModal.addEventListener("show.bs.modal", function (event) {
    const button = event.relatedTarget;
    document.getElementById("deleteTaskName").textContent = button.dataset.taskName;
    document.getElementById("deleteForm").action = button.dataset.deleteUrl;
  });
}
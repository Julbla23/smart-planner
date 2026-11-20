// Przycisk "Zaproponuj kroki": po kliknięciu pokazuje "Myślę..." z kręcącym się kółkiem,
// żeby było widać, że AI pracuje, i żeby nie dało się kliknąć drugi raz.
const goalForm = document.getElementById("goalForm");

if (goalForm) {
  goalForm.addEventListener("submit", function () {
    const button = document.getElementById("goalButton");

    // setTimeout(..., 0): wyłączamy przycisk dopiero PO wysłaniu formularza.
    // Gdyby był wyłączony wcześniej, przeglądarka nie wysłałaby jego wartości
    // (akcja=zaproponuj) i widok nie wiedziałby, co zrobić.
    setTimeout(function () {
      button.disabled = true;
      button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Myślę...';
    }, 0);
  });
}
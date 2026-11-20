// Kalendarz z godziną: pola z data-picker="datetime"
document.querySelectorAll('[data-picker="datetime"]').forEach(function (el) {
  flatpickr(el, {
    enableTime: true,
    time_24hr: true,
    dateFormat: "Y-m-d H:i",   // format wysyłany do Django
    altInput: true,
    altFormat: "d.m.Y H:i",    // format, który widzisz w polu
    locale: "pl",
    minuteIncrement: 5
  });
});

// Sam kalendarz: pola z data-picker="date"
document.querySelectorAll('[data-picker="date"]').forEach(function (el) {
  flatpickr(el, {
    dateFormat: "Y-m-d",
    altInput: true,
    altFormat: "d.m.Y",
    locale: "pl"
  });
});
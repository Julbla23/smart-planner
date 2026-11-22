document.querySelectorAll('[data-picker="datetime"]').forEach(function (el) {
  flatpickr(el, {
    enableTime: true,
    time_24hr: true,
    dateFormat: "Y-m-d H:i",
    altInput: true,
    altFormat: "d.m.Y H:i",
    locale: "pl",
    minuteIncrement: 5
  });
});

document.querySelectorAll('[data-picker="date"]').forEach(function (el) {
  flatpickr(el, {
    dateFormat: "Y-m-d",
    altInput: true,
    altFormat: "d.m.Y",
    locale: "pl"
  });
});
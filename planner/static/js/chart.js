const canvas = document.getElementById("periodChart");

if (canvas) {
    const chart = JSON.parse(document.getElementById("chart-data").textContent);

    const styles = getComputedStyle(document.documentElement);
    const color = name => styles.getPropertyValue(name).trim();

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: chart.labels,
            datasets: [
                { label: "Zrobione",     data: chart.done,    backgroundColor: color("--prio-low") },
                { label: "Do zrobienia", data: chart.todo,    backgroundColor: color("--puder") },
                { label: "Zaległe",      data: chart.overdue, backgroundColor: color("--prio-high") }
            ]
        },
        options: {
            plugins: {
                legend: { position: "bottom" }
            },
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}
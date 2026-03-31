// Instância global
window.lineChartInstance = null;

function createLineChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  window.lineChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: "Consumo (kWh)",
        data: [],
        borderColor: '#113d9e',
        backgroundColor: '#eeaa55',
        fill: false,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
}

function updateLineChart(chart, labels, values, labelText) {
  if (!chart) return;

  chart.data.labels = labels;
  chart.data.datasets[0].data = values;
  chart.data.datasets[0].label = labelText;

  chart.update();
}

document.addEventListener("DOMContentLoaded", function () {
  createLineChart("linechart");
});

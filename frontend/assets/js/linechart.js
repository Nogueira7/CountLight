function createLineChart(canvasId, labels, datasets, yMax = null) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          mode: 'index',
          intersect: false,
        }
      },
      hover: {
        mode: 'nearest',
        intersect: true
      },
      scales: {
        x: {
          display: true,
          title: {
            display: true,
            text: 'Período do dia'
          }
        },
        y: {
          display: true,
          title: {
            display: true,
            text: 'Consumo (kWh)'
          },
          beginAtZero: true,
          max: yMax || 5 // Limite máximo padrão
        }
      }
    }
  });
}

// === EXEMPLO DE USO: CONSUMO POR PERÍODO DO DIA ===
const periods = ['00-03h', '03-06h', '06-09h', '09-12h', '12-15h', '15-18h', '18-21h', '21-24h'];

// Dados estáticos plausíveis em kWh por período de 3h
const consumoHoje = [0.8, 0.6, 1.2, 1.8, 2.0, 2.2, 2.0, 1.5];   // Consumo do dia de hoje
const consumoOntem = [0.7, 0.5, 1.0, 1.5, 1.8, 2.3, 2.2, 1.2];  // Consumo do dia anterior

// Calcula máximo para definir Y
const maxConsumo = Math.max(...consumoHoje, ...consumoOntem);
const yMax = Math.ceil(maxConsumo * 1.2); // margem de 20%

// Cria o gráfico
createLineChart('linechart', periods, [
  {
    label: 'Hoje',
    data: consumoHoje,
    backgroundColor: '#eeaa55',
    borderColor: '#113d9e',
    fill: false,
    tension: 0.3
  },
  {
    label: 'Ontem',
    data: consumoOntem,
    backgroundColor: '#90fffc',
    borderColor: '#ac90ca',
    fill: false,
    tension: 0.3
  }
], yMax);

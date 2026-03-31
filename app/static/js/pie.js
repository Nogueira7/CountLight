// =====================================================
// PIE CHART MODULE - CountLight
// =====================================================



// ==============================
// FUNÇÃO GENÉRICA PARA CRIAR PIE CHART
// ==============================

function createPieChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const ctx = canvas.getContext('2d');

  return new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['A carregar...'],
      datasets: [{
        data: [1],
        backgroundColor: getDefaultColors(1),
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom'
        }
      }
    }
  });
}



// ==============================
// CORES DEFAULT
// ==============================

function getDefaultColors(count) {
  const palette = [
    window.chartColors?.blue1,
    window.chartColors?.blue2,
    window.chartColors?.blue3,
    window.chartColors?.blue4,
    window.chartColors?.blue5,
    window.chartColors?.blue6,
    window.chartColors?.blue7
  ].filter(Boolean);

  // fallback caso chartColors não exista
  if (palette.length === 0) {
    return Array(count).fill('#4e73df');
  }

  const colors = [];
  for (let i = 0; i < count; i++) {
    colors.push(palette[i % palette.length]);
  }

  return colors;
}



// ==============================
// MOSTRAR ESTADO "SEM DADOS"
// ==============================

function showNoData(chartInstance) {
  if (!chartInstance) return;

  chartInstance.data.labels = ['Sem dados'];
  chartInstance.data.datasets[0].data = [1];
  chartInstance.data.datasets[0].backgroundColor = ['#e0e0e0'];
  chartInstance.update();
}



// ==============================
// ATUALIZAR PIE CHART (ROBUSTO)
// ==============================

function updatePieChart(chartInstance, labels, values) {
  if (!chartInstance) return;

  // proteção extra
  if (!Array.isArray(values) || values.length === 0) {
    showNoData(chartInstance);
    return;
  }

  // verifica se todos os valores são 0
  const allZero = values.every(v => Number(v) === 0);

  if (allZero) {
    showNoData(chartInstance);
    return;
  }

  chartInstance.data.labels = labels;
  chartInstance.data.datasets[0].data = values;
  chartInstance.data.datasets[0].backgroundColor = getDefaultColors(values.length);
  chartInstance.update();
}



// ==============================
// CRIAÇÃO DAS INSTÂNCIAS
// ==============================

window.pieChartInstance = createPieChart('piechart');     // Por divisão
window.pieChart2Instance = createPieChart('piechart2');   // Por tipo
window.pieChart3Instance = createPieChart('piechart3');   // Por dispositivo (se existir)



// ==============================
// EXPORT PARA GARANTIR ACESSO GLOBAL
// ==============================

window.updatePieChart = updatePieChart;
window.showNoData = showNoData;

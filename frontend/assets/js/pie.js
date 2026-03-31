function createPieChart(canvasId, data, labels, colors) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;

  var ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'pie',
    data: {
      datasets: [{
        data: data,
        backgroundColor: colors,
        label: 'Dataset'
      }],
      labels: labels
    },
    options: {
      responsive: true
    }
  });
}

// PIE CHART 1
createPieChart(
  'piechart',
  [120, 80, 200, 40, 150, 30, 0], // kWh por divisão
  ['Quarto Pedro e Silvia', 'Quarto Tomás', 'Sala', 'Casa de banho', 'Cozinha', 'Salão', 'Casa de banho de serviço'],
  [
    window.chartColors.blue1,
    window.chartColors.blue2,
    window.chartColors.blue3,
    window.chartColors.blue4,
    window.chartColors.blue5,
    window.chartColors.blue6,
    window.chartColors.blue7
  ]
);

// PIE CHART 2
createPieChart(
  'piechart2',
  [30, 20, 25, 15, 10],
  ['Eletrodomésticos', 'Utensílios', 'Climatização', 'Entretenimento', 'Outros'],
  [
    window.chartColors.blue1,
    window.chartColors.blue2,
    window.chartColors.blue3,
    window.chartColors.blue4,
    window.chartColors.blue5
  ]
);

// PIE CHART 3
createPieChart(
  'piechart3',
  [20, 10, 25, 45, 20],
  ['Tomada TV', 'Tomada Roteador', 'Tomada Abajur', 'Tomada Ar-condicionado', 'Outros'],
  [
    window.chartColors.blue1,
    window.chartColors.blue2,
    window.chartColors.blue3,
    window.chartColors.blue4,
    window.chartColors.blue5
  ]
);
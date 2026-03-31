function getDaysInMonth(year, month) {
  // Retorna o número de dias do mês
  return new Date(year, month + 1, 0).getDate();
}

function generateDaysArray(year, month) {
  const daysCount = getDaysInMonth(year, month);
  const daysArray = [];
  for (let i = 1; i <= daysCount; i++) {
    daysArray.push(i);
  }
  return daysArray;
}

function createBarChart(canvasId, labels, datasets) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        }
      }
    }
  });
}

// Pega o mês e ano atual
const today = new Date();
const currentYear = today.getFullYear();
const currentMonth = today.getMonth(); // Janeiro = 0, Fevereiro = 1 ...

// Gera dias do mês atual
const daysOfMonth = generateDaysArray(currentYear, currentMonth);

// Gera dados aleatórios para o exemplo (mesmo tamanho dos dias)
const dataset1 = daysOfMonth.map(() => Math.floor(Math.random() * 100));
const dataset2 = daysOfMonth.map(() => Math.floor(Math.random() * 50));

// Cria o bar chart com dias do mês
createBarChart('barchart', daysOfMonth, [
  {
    data: dataset1,
    label: 'Mês atual',
    backgroundColor: "#113d9e",
    borderWidth: 1
  },
  {
    data: dataset2,
    label: 'Mês passado',
    backgroundColor: "#eeaa55",
    borderWidth: 1
  }
]);

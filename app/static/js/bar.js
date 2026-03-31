// =====================================================
// 🔥 Criar gráfico vazio ao iniciar
// =====================================================
function createBarComparisonChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const ctx = canvas.getContext("2d");

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Mês atual",
          data: [],
          backgroundColor: "#113d9e",
          borderWidth: 1,
        },
        {
          label: "Mês passado",
          data: [],
          backgroundColor: "#eeaa55",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "top" },
      },
      scales: {
        x: {
          title: { display: true, text: "Dia do mês" },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Consumo (kWh)" },
        },
      },
    },
  });
}

// =====================================================
// 🔄 Atualizar gráfico com novos dados
// =====================================================
function updateBarComparisonChart(chartInstance, labels, currentData, previousData) {
  if (!chartInstance) return;

  chartInstance.data.labels = labels;
  chartInstance.data.datasets[0].data = currentData;
  chartInstance.data.datasets[1].data = previousData;

  chartInstance.update();
}

// =====================================================
// 🌐 Buscar dados do backend e preencher o gráfico
// =====================================================
async function loadBarComparisonData(chartInstance) {
  if (!chartInstance) return;

  try {
    const res = await fetch("/api/dashboard/summary", {
      headers: {
        "Authorization": "Bearer " + localStorage.getItem("token"),
      },
    });

    if (!res.ok) {
      console.error("Erro a obter /api/dashboard/summary:", res.status);
      return;
    }

    const data = await res.json();
    const mc = data.month_comparison;

    if (!mc || !Array.isArray(mc.labels)) {
      console.error("Resposta sem month_comparison válido:", data);
      return;
    }

    updateBarComparisonChart(
      chartInstance,
      mc.labels,
      mc.current_month || [],
      mc.previous_month || []
    );
  } catch (err) {
    console.error("Erro ao carregar dados do bar chart:", err);
  }
}

// =====================================================
// 🚀 Inicialização automática
// =====================================================
document.addEventListener("DOMContentLoaded", async function () {
  window.barChartInstance = createBarComparisonChart("barchart");
  window.updateBarComparisonChart = updateBarComparisonChart;

  await loadBarComparisonData(window.barChartInstance);
});
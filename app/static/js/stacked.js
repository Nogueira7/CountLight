const stackedCanvas = document.getElementById("stackedbar");

if (stackedCanvas) {
  new Chart(stackedCanvas, {
    type: 'bar',
    data: {
      labels: ['January', 'February', 'March', 'April', 'May', 'June', 'July'],
      datasets: [
        {
          data: [10,20,30,40,50,60,70,80],
          label: 'Dataset 1',
          backgroundColor: window.chartColors.navy,
          borderWidth: 1,
        },
        {
          data: [30,10,70,15,30,20,70,80],
          label: 'Dataset 2',
          backgroundColor: window.chartColors.purple,
          borderWidth: 1,
        },
        {
          data: [20,30,40,50,60,70,80,80],
          label: 'Dataset 3',
          backgroundColor: window.chartColors.grey,
        }
      ]
    },
    options: {
      tooltips: {
        mode: 'index',
        intersect: false
      },
      responsive: true,
      scales: {
        xAxes: [{ stacked: true }],
        yAxes: [{ stacked: true }]
      }
    }
  });
}

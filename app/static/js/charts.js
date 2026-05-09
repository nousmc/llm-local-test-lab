function makeBarChart(canvasId, labels, data, label, color) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    var ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: color || 'rgba(34,139,34,0.7)',
                borderColor: color ? color.replace('0.7', '1') : 'rgba(34,139,34,1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { font: { size: 11 } }
                },
                x: {
                    ticks: { font: { size: 11 }, maxRotation: 45 }
                }
            }
        }
    });
}

function makeGroupedBarChart(canvasId, labels, datasets) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    var ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top', labels: { font: { size: 10 }, boxWidth: 12 } }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { font: { size: 11 } }
                },
                x: {
                    ticks: { font: { size: 11 }, maxRotation: 45 }
                }
            }
        }
    });
}

function makePieChart(canvasId, labels, data, label) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    var ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: [
                    'rgba(34,139,34,0.7)',
                    'rgba(54,162,235,0.7)',
                    'rgba(255,159,64,0.7)',
                    'rgba(153,102,255,0.7)',
                    'rgba(255,99,132,0.7)',
                    'rgba(255,205,86,0.7)',
                ],
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 10 } } } }
        }
    });
}

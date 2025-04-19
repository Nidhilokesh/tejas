// Global variables
let chartInstance = null;
let chartData = null;
let showFuture = false;

// Send message to server
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (message) {
        // Clear input
        input.value = '';
        
        // Send to server
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        })
        .then(response => response.json())
        .then(data => {
            updateChatMessages(data.history);
            
            // Check if we need to fetch chart data
            const lastMessages = data.history.slice(-2);
            if (lastMessages.some(msg => msg[1].includes("Generating charts"))) {
                fetchChartData();
            }
        })
        .catch(error => console.error('Error:', error));
    }
}


// Convenience function for ticker buttons
function sendTickerMessage(ticker) {
    document.getElementById('messageInput').value = ticker;
    sendMessage();
}

// Update chat messages
function updateChatMessages(history) {
    const chatContainer = document.getElementById('chatMessages');
    chatContainer.innerHTML = '';
    
    history.forEach(([role, message]) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `${role}-message`;
        
        const nameSpan = document.createElement('strong');
        nameSpan.textContent = role === 'you' ? 'You: ' : 'StockBot: ';
        
        const messageSpan = document.createElement('span');
        messageSpan.innerHTML = message; // We're using innerHTML since message may contain markdown
        
        messageDiv.appendChild(nameSpan);
        messageDiv.appendChild(messageSpan);
        chatContainer.appendChild(messageDiv);
    });
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Fetch chart data from server
function fetchChartData() {
    fetch('/chart_data')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                return;
            }
            
            chartData = data;
            populateModelSelector(Object.keys(data.models));
            updateMetrics(data.models);
            createChart(); // Call to create the chart initially
        })
        .catch(error => console.error('Error fetching chart data:', error));
}

// Populate model dropdown
function populateModelSelector(modelNames) {
    const selector = document.getElementById('modelSelector');
    selector.innerHTML = '<option value="" disabled selected>Select Model</option>';
    
    modelNames.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model.charAt(0).toUpperCase() + model.slice(1);
        selector.appendChild(option);
    });
    
    // Select first model by default
    if (modelNames.length > 0) {
        selector.value = modelNames[0];
        updateChartView(); // Update chart for the selected model
    }
}

// Update metrics display
function updateMetrics(models) {
    const container = document.getElementById('metricsContainer');
    container.innerHTML = '<h3>Performance Metrics</h3>';
    
    Object.entries(models).forEach(([modelName, data]) => {
        const metricDiv = document.createElement('div');
        metricDiv.className = 'metric-box';
        metricDiv.innerHTML = `
            <h4>${modelName.charAt(0).toUpperCase() + modelName.slice(1)}</h4>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value">${data.metrics.rmse}</div>
                    <div class="metric-label">RMSE</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${data.metrics.r2}</div>
                    <div class="metric-label">R²</div>
                </div>
            </div>
        `;
        container.appendChild(metricDiv);
    });
}

// Create or update chart
function createChart() {
    const ctx = document.getElementById('stockChart').getContext('2d');
    
    // Destroy previous chart if it exists
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    // Get selected model
    const selectedModel = document.getElementById('modelSelector').value;
    if (!selectedModel || !chartData || !chartData.models[selectedModel]) {
        return;
    }
    
    const modelData = chartData.models[selectedModel];
    //----------------------------------
    console.log("modelData:", modelData);
    console.log("Future preds:", modelData.future_preds);
    console.log("Future dates:", modelData.future_dates);
    //----------------------------------

    // Prepare datasets
    const datasets = [
        {
            label: 'Historical Close Price',
            data: chartData.historical.close,
            borderColor: 'rgba(75, 192, 192, 1)',
            fill: false,
            pointRadius: 0,
            borderWidth: 2
        },
        {
            label: 'Actual (Test Set)',
            data: Array(chartData.historical.dates.length - modelData.actuals.length).fill(null).concat(modelData.actuals),
            borderColor: 'rgba(54, 162, 235, 1)',
            fill: false,
            pointRadius: 2,
            borderWidth: 2
        },
        {
            label: 'Predicted',
            data: Array(chartData.historical.dates.length - modelData.predictions.length).fill(null).concat(modelData.predictions),
            borderColor: 'rgba(255, 99, 132, 1)',
            fill: false,
            pointRadius: 2,
            borderWidth: 2
        }
    ];
    
    // Add future predictions if available and toggled on
    if (showFuture && modelData.future_dates && modelData.future_preds) {
        const allDates = [...chartData.historical.dates, ...modelData.future_dates];
        
        datasets[0].data = [...chartData.historical.close, ...Array(modelData.future_dates.length).fill(null)];
        
        datasets.push({
            label: 'Future Forecast',
            data: [...Array(chartData.historical.dates.length).fill(null), ...modelData.future_preds],
            borderColor: 'rgba(255, 159, 64, 1)',
            borderDash: [5, 5],
            fill: false,
            pointRadius: 3,
            borderWidth: 2
        });
        
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allDates,
                datasets: datasets
            },
            options: getChartOptions()
        });
    } else {
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.historical.dates,
                datasets: datasets
            },
            options: getChartOptions()
        });
    }
}

// Chart options
function getChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: 'Stock Price Analysis',
                font: {
                    size: 16,
                    weight: 'bold'
                }
            },
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false,
            }
        },
        scales: {
            x: {
                ticks: {
                    maxRotation: 45,
                    minRotation: 45
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Price ($)'
                }
            }
        }
    };
}

// Toggle future predictions view
function toggleFutureView() {
    showFuture = !showFuture;
    console.log("Toggled future view:", showFuture);/////////////////////////////////////
    createChart();
}

// Update chart when model selection changes
function updateChartView() {
    createChart();
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Setup enter key for chat input
    const input = document.getElementById('messageInput');
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Listen to model selection change
    const modelSelector = document.getElementById('modelSelector');
    if (modelSelector) {
        modelSelector.addEventListener('change', updateChartView);
    }
});


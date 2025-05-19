// JavaScript code for AHP application
const charts = {};
const colors = [
    'rgba(255, 99, 132, 0.7)',  // Đỏ
    'rgba(54, 162, 235, 0.7)',  // Xanh dương
    'rgba(255, 206, 86, 0.7)',  // Vàng
    'rgba(75, 192, 192, 0.7)',  // Xanh lam
    'rgba(153, 102, 255, 0.7)'  // Tím
];
let selectedCriteria = [];
const validValues = [
    '2', '3', '4', '5', '6', '7', '8', '9',
    '1/2', '1/3', '1/4', '1/5', '1/6', '1/7', '1/8', '1/9'
];
let customCriteria = [];

function addCustomCriterion() {
    const input = document.getElementById('customCriterion');
    const criterion = input.value.trim();
    if (criterion && criterion.length <= 50 && !selectedCriteria.includes(criterion) && !customCriteria.includes(criterion)) {
        customCriteria.push(criterion);
        updateCustomCriteriaList();
        input.value = '';
        alert(`Đã thêm tiêu chí: ${criterion}`);
    } else {
        alert('Tiêu chí phải hợp lệ, không trùng lặp và dưới 50 ký tự!');
    }
}

function updateCustomCriteriaList() {
    const container = document.getElementById('customCriteriaList');
    container.innerHTML = '<h3 class="text-sm font-medium mt-2">Tiêu chí mới:</h3>';
    customCriteria.forEach(c => {
        container.innerHTML += `
                    <div class="flex items-center gap-2">
                        <input type="checkbox" value="${c}" class="criteria-checkbox" checked>
                        <span>${c}</span>
                        <button onclick="removeCustomCriterion('${c}')" class="text-red-500 hover:text-red-700">Xóa</button>
                    </div>
                `;
    });
}

function removeCustomCriterion(criterion) {
    customCriteria = customCriteria.filter(c => c !== criterion);
    updateCustomCriteriaList();
}


function restrictInput(input) {
    const value = input.value.trim();
    const errorDiv = input.nextElementSibling || document.createElement('div');
    errorDiv.className = 'error-message';
    if (!input.nextElementSibling) input.parentElement.appendChild(errorDiv);

    if (value && !validValues.includes(value)) {
        input.classList.add('input-error');
        errorDiv.textContent = 'Chỉ được nhập: 2, 3, 4, 5, 6, 7, 8, 9, 1/2, 1/3, 1/4, 1/5, 1/6, 1/7, 1/8, 1/9';
        return false;
    } else {
        input.classList.remove('input-error');
        errorDiv.textContent = '';
        return true;
    }
}

function showCriteriaMatrix() {
    const checkboxes = document.querySelectorAll('.criteria-checkbox:checked');
    selectedCriteria = Array.from(checkboxes).map(cb => cb.value);
    if (selectedCriteria.length < 2) {
        alert('Vui lòng chọn ít nhất 2 tiêu chí!');
        return;
    }

    document.getElementById('criteria-selection').classList.add('hidden');
    document.getElementById('criteria-matrix-input').classList.remove('hidden');

    let criteriaHtml = '<table>';
    criteriaHtml += '<tr><th></th>' + selectedCriteria.map(c => `<th>${c}</th>`).join('') + '</tr>';
    for (let i = 0; i < selectedCriteria.length; i++) {
        criteriaHtml += `<tr><td>${selectedCriteria[i]}</td>`;
        for (let j = 0; j < selectedCriteria.length; j++) {
            if (i === j) {
                criteriaHtml += '<td>1</td>';
            } else {
                criteriaHtml += `<td><input type="text" class="matrix-input criteria-matrix-input" data-row="${i}" data-col="${j}" placeholder="2, 3, 1/3,..."></td>`;
            }
        }
        criteriaHtml += '</tr>';
    }
    criteriaHtml += '</table>';
    document.getElementById('criteria-matrix').innerHTML = criteriaHtml;

    document.querySelectorAll('.criteria-matrix-input').forEach(input => {
        input.addEventListener('input', () => {
            if (restrictInput(input)) {
                const row = parseInt(input.dataset.row);
                const col = parseInt(input.dataset.col);
                const value = input.value.trim();
                const inverseInput = document.querySelector(`.criteria-matrix-input[data-row="${col}"][data-col="${row}"]`);
                if (inverseInput) {
                    if (value) {
                        const inverseValue = value.startsWith('1/') ? value.slice(2) : `1/${value}`;
                        inverseInput.value = inverseValue;
                        inverseInput.setAttribute('readonly', 'readonly'); // Make inverse cell read-only
                        restrictInput(inverseInput);
                    } else {
                        inverseInput.value = ''; // Clear inverse input
                        inverseInput.removeAttribute('readonly'); // Make inverse cell editable again
                        restrictInput(inverseInput);
                    }
                }
            }
        });
    });
}

async function checkCriteriaMatrix() {
    const criteriaMatrix = Array(selectedCriteria.length).fill().map(() => Array(selectedCriteria.length).fill(1));
    let valid = true;
    const inputs = document.querySelectorAll('.criteria-matrix-input');
    inputs.forEach(input => {
        const row = parseInt(input.dataset.row);
        const col = parseInt(input.dataset.col);
        let value = input.value.trim() || '1';
        if (!validValues.includes(value)) {
            valid = false;
            restrictInput(input);
            return;
        }
        value = value.includes('/') ? eval(value) : Number(value);
        criteriaMatrix[row][col] = value;
        criteriaMatrix[col][row] = 1 / value;
    });

    if (!valid) {
        document.getElementById('criteria-matrix-error').textContent = 'Vui lòng nhập đúng các giá trị: 2, 3, 4, 5, 6, 7, 8, 9, 1/2, 1/3, 1/4, 1/5, 1/6, 1/7, 1/8, 1/9';
        return;
    }

    try {
        const response = await fetch('/api/calculate-ahp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ criteria: selectedCriteria, criteria_matrix: criteriaMatrix })
        });
        const result = await response.json();
        if (result.error && result.error.includes('không nhất quán')) {
            document.getElementById('criteria-matrix-error').textContent = `Ma trận tiêu chí không nhất quán: ${result.error}`;
            return;
        }
        document.getElementById('criteria-matrix-error').textContent = '';
        showAlternativeMatrices();
    } catch (error) {
        document.getElementById('criteria-matrix-error').textContent = `Lỗi: ${error.message}`;
    }
}

function showAlternativeMatrices() {
    document.getElementById('criteria-matrix-input').classList.add('hidden');
    document.getElementById('alternative-matrices-input').classList.remove('hidden');

    const alternatives = [
        'Ký túc xá trong trường', 'Nhà trọ gần trường', 'Nhà trọ xa trường',
        'Chung cư mini', 'Nhà ở cùng người thân'
    ];
    let altHtml = '';
    selectedCriteria.forEach(criterion => {
        altHtml += `<h3>Ma trận so sánh cặp phương án theo ${criterion}</h3><table>`;
        altHtml += '<tr><th></th>' + alternatives.map(a => `<th>${a}</th>`).join('') + '</tr>';
        for (let i = 0; i < alternatives.length; i++) {
            altHtml += `<tr><td>${alternatives[i]}</td>`;
            for (let j = 0; j < alternatives.length; j++) {
                if (i === j) {
                    altHtml += '<td>1</td>';
                } else {
                    altHtml += `<td><input type="text" class="matrix-input alternative-matrix-input" data-criterion="${criterion}" data-row="${i}" data-col="${j}" placeholder="2, 3, 1/3,..."></td>`;
                }
            }
            altHtml += '</tr>';
        }
        altHtml += '</table>';
    });
    document.getElementById('alternative-matrices').innerHTML = altHtml;

    document.querySelectorAll('.alternative-matrix-input').forEach(input => {
        input.addEventListener('input', () => {
            if (restrictInput(input)) {
                const criterion = input.dataset.criterion;
                const row = parseInt(input.dataset.row);
                const col = parseInt(input.dataset.col);
                const value = input.value.trim();
                if (value) {
                    const inverseInput = document.querySelector(`.alternative-matrix-input[data-criterion="${criterion}"][data-row="${col}"][data-col="${row}"]`);
                    if (inverseInput) {
                        const inverseValue = value.startsWith('1/') ? value.slice(2) : `1/${value}`;
                        inverseInput.value = inverseValue;
                        restrictInput(inverseInput);
                    }
                }
            }
        });
    });
}

async function calculateAHP() {
    const criteriaMatrix = Array(selectedCriteria.length).fill().map(() => Array(selectedCriteria.length).fill(1));
    const alternativeMatrices = {};
    let valid = true;

    // Thu thập ma trận tiêu chí
    const criteriaInputs = document.querySelectorAll('.criteria-matrix-input');
    criteriaInputs.forEach(input => {
        const row = parseInt(input.dataset.row);
        const col = parseInt(input.dataset.col);
        let value = input.value.trim() || '1';
        if (!validValues.includes(value)) {
            valid = false;
            restrictInput(input);
            return;
        }
        value = value.includes('/') ? eval(value) : Number(value);
        criteriaMatrix[row][col] = value;
        criteriaMatrix[col][row] = 1 / value;
    });

    // Thu thập ma trận phương án
    selectedCriteria.forEach(criterion => {
        const matrix = Array(5).fill().map(() => Array(5).fill(1));
        const inputs = document.querySelectorAll(`.alternative-matrix-input[data-criterion="${criterion}"]`);
        inputs.forEach(input => {
            const row = parseInt(input.dataset.row);
            const col = parseInt(input.dataset.col);
            let value = input.value.trim() || '1';
            if (!validValues.includes(value)) {
                valid = false;
                restrictInput(input);
                return;
            }
            value = value.includes('/') ? eval(value) : Number(value);
            matrix[row][col] = value;
            matrix[col][row] = 1 / value;
        });
        alternativeMatrices[criterion] = matrix;
    });

    if (!valid) {
        document.getElementById('alternative-matrices-error').textContent = 'Vui lòng nhập đúng các giá trị: 2, 3, 4, 5, 6, 7, 8, 9, 1/2, 1/3, 1/4, 1/5, 1/6, 1/7, 1/8, 1/9';
        return;
    }

    // Kiểm tra CR cho từng ma trận phương án
    for (const criterion of selectedCriteria) {
        try {
            const response = await fetch('/api/calculate-ahp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    criteria: [criterion],
                    alternative_matrices: { [criterion]: alternativeMatrices[criterion] }
                })
            });
            const result = await response.json();
            if (result.error && result.error.includes('không nhất quán')) {
                document.getElementById('alternative-matrices-error').textContent = `Ma trận phương án cho '${criterion}' không nhất quán: ${result.error}`;
                return;
            }
        } catch (error) {
            document.getElementById('alternative-matrices-error').textContent = `Lỗi: ${error.message}`;
            return;
        }
    }
    document.getElementById('alternative-matrices-error').textContent = '';

    document.getElementById('alternative-matrices-input').classList.add('hidden');
    document.getElementById('loading').textContent = 'Đang tính toán...';
    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/calculate-ahp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                criteria: selectedCriteria,
                criteria_matrix: criteriaMatrix,
                alternative_matrices: alternativeMatrices
            })
        });
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Lỗi khi tính toán AHP');
        }

        renderCharts(data);
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('content').classList.remove('hidden');
    } catch (error) {
        document.getElementById('alternative-matrices-input').classList.remove('hidden');
        document.getElementById('loading').textContent = `Lỗi: ${error.message}`;
        console.error('Lỗi:', error);
    }
}

async function fetchDefaultData() {
    document.getElementById('buttons').classList.add('hidden');
    document.getElementById('loading').textContent = 'Đang tải...';
    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/ahp-data');
        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Lỗi khi tải dữ liệu từ server');
        }

        // Đảm bảo dữ liệu đầy đủ
        if (!data.criteria_weights && !data.alternative_weights && !data.rankings && !data.alternative_rankings) {
            throw new Error('Dữ liệu không đầy đủ từ server');
        }

        renderCharts(data);
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('content').classList.remove('hidden');
    } catch (error) {
        document.getElementById('buttons').classList.remove('hidden');
        document.getElementById('loading').textContent = `Lỗi: ${error.message}`;
        console.error('Lỗi:', error);
    }
}

async function showHistory() {
    document.getElementById('buttons').classList.add('hidden');
    document.getElementById('loading').textContent = 'Đang tải lịch sử...';
    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/history');
        const history = await response.json();

        if (!response.ok || history.error) {
            throw new Error(history.error || 'Lỗi khi tải lịch sử');
        }

        const historyList = document.getElementById('history-list');
        historyList.innerHTML = history.map(item => `
                    <div class="border-b py-2">
                        <p><strong>Thời gian:</strong> ${new Date(item.timestamp).toLocaleString()}</p>
                        <p><strong>Tiêu chí:</strong> ${item.criteria.join(', ')}</p>
                        <p><strong>Trọng số tiêu chí:</strong> ${Object.entries(item.criteria_weights).map(([k, v]) => `${k}: ${v}%`).join(', ')}</p>
                        <p><strong>Xếp hạng:</strong> ${item.rankings.map(r => `${r.name}: ${r.score}%`).join(', ')}</p>
                    </div>
                `).join('');
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('history').classList.remove('hidden');
    } catch (error) {
        document.getElementById('buttons').classList.remove('hidden');
        document.getElementById('loading').textContent = `Lỗi: ${error.message}`;
        console.error('Lỗi:', error);
    }
}

async function renderCharts(data) {
    // Destroy existing charts to prevent memory leaks
    Object.keys(charts).forEach(chartId => {
        if (charts[chartId]) {
            charts[chartId].destroy();
            delete charts[chartId];
        }
    });

    // Ensure Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Please ensure the Chart.js script is included.');
        document.getElementById('loading').textContent = 'Lỗi: Chart.js không được tải.';
        return;
    }

    // Render overall chart (pie chart for rankings)
    const overallCtx = document.getElementById('overallChart')?.getContext('2d');
    if (!overallCtx) {
        console.error('Overall chart canvas not found.');
        document.getElementById('loading').textContent = 'Lỗi: Không tìm thấy canvas cho biểu đồ tổng hợp.';
        return;
    }

    charts['overallChart'] = new Chart(overallCtx, {
        type: 'pie',
        data: {
            labels: data.rankings.map(item => item.name),
            datasets: [{
                label: 'Điểm tổng hợp (%)',
                data: data.rankings.map(item => item.score || 0),
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.7', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: { display: true, text: 'Xếp hạng tổng hợp' },
                legend: { position: 'bottom' }
            }
        }
    });

    // Update overall ranking list
    const overallRanking = document.getElementById('overall-ranking');
    overallRanking.innerHTML = data.rankings.map(item => `<li>${item.name}: ${(item.score || 0).toFixed(2)}%</li>`).join('');

    // Render criteria-specific charts
    const criteriaChartsDiv = document.getElementById('criteria-charts');
    criteriaChartsDiv.innerHTML = ''; // Clear previous charts

    const actualCriteria = Object.keys(data.alternative_rankings);
    for (const criterion of actualCriteria) {
        const safeId = criterion.replace(/[^\w-]/g, '-');
        const chartId = `chart-${safeId}`;
        const rankingId = `ranking-${safeId}`;

        // Add chart container to DOM
        criteriaChartsDiv.innerHTML += `
            <div class="card bg-white p-4 rounded-lg shadow">
                <h2 class="text-xl font-semibold mb-2">Xếp hạng theo ${criterion}</h2>
                <div class="chart-container">
                    <canvas id="${chartId}"></canvas>
                </div>
                <ol id="${rankingId}" class="list-decimal list-inside mt-4"></ol>
            </div>
        `;
    }

    // Wait for DOM to update (ensure canvas elements are rendered)
    await new Promise(resolve => setTimeout(resolve, 0));

    // Initialize charts for each criterion
    for (const criterion of actualCriteria) {
        const safeId = criterion.replace(/[^\w-]/g, '-');
        const chartId = `chart-${safeId}`;
        const rankingId = `ranking-${safeId}`;

        const ctx = document.getElementById(chartId)?.getContext('2d');
        if (!ctx) {
            console.warn(`Canvas not found for criterion "${criterion}" with ID "${chartId}"`);
            continue;
        }

        const rankings = data.alternative_rankings[criterion] || [];
        charts[chartId] = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: rankings.map(item => item.name),
                datasets: [{
                    label: `Trọng số theo ${criterion} (%)`,
                    data: rankings.map(item => item.score || 0),
                    backgroundColor: colors,
                    borderColor: colors.map(c => c.replace('0.7', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `Xếp hạng theo ${criterion}` },
                    legend: { position: 'bottom' }
                }
            }
        });

        // Update ranking list for this criterion
        const rankingDiv = document.getElementById(rankingId);
        rankingDiv.innerHTML = rankings.map(item => `<li>${item.name}: ${(item.score || 0).toFixed(2)}%</li>`).join('');
    }
}


function resetToCriteria() {
    document.getElementById('criteria-matrix-input').classList.add('hidden');
    document.getElementById('alternative-matrices-input').classList.add('hidden');
    document.getElementById('criteria-selection').classList.remove('hidden');
    document.querySelectorAll('.criteria-checkbox').forEach(cb => cb.checked = false);
    selectedCriteria = [];
}

function backToCriteriaMatrix() {
    document.getElementById('alternative-matrices-input').classList.add('hidden');
    document.getElementById('criteria-matrix-input').classList.remove('hidden');
}

function resetInterface() {
    document.getElementById('content').classList.add('hidden');
    document.getElementById('history').classList.add('hidden');
    document.getElementById('buttons').classList.remove('hidden');
    document.getElementById('loading').classList.add('hidden');
    Object.keys(charts).forEach(chartId => {
        if (charts[chartId]) {
            charts[chartId].destroy();
            delete charts[chartId];
        }
    });
}

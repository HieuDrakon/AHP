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
                <button onclick="removeCustomCriterion('${c.replace(/'/g, "\\'")}')" class="text-red-500 hover:text-red-700">Xóa</button>
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
                        inverseInput.setAttribute('readonly', 'readonly');
                        restrictInput(inverseInput);
                    } else {
                        inverseInput.value = '';
                        inverseInput.removeAttribute('readonly');
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

function normalizeMatrix(matrix) {
    const n = matrix.length;
    const colSums = matrix[0].map((_, col) => matrix.reduce((sum, row) => sum + row[col], 0));
    const normalizedMatrix = matrix.map(row => row.map((value, col) => value / colSums[col]));
    return normalizedMatrix;
}

function calculateWeightsFromMatrix(matrix) {
    const normalizedMatrix = normalizeMatrix(matrix);
    const weights = normalizedMatrix.map(row => row.reduce((sum, val) => sum + val, 0) / row.length);
    return weights;
}

const alternatives = [
    'Ký túc xá trong trường', 'Nhà trọ gần trường', 'Nhà trọ xa trường',
    'Chung cư mini', 'Nhà ở cùng người thân'
];

function createTable(headers, rows, rowLabels) {
    const table = document.createElement('table');
    table.className = 'border-collapse border border-gray-300 w-full mb-4';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.appendChild(createCell('th', '', 'border border-gray-300 bg-gray-100'));
    headers.forEach(header => headerRow.appendChild(createCell('th', header, 'border border-gray-300 bg-gray-100')));
    thead.appendChild(headerRow);

    const tbody = document.createElement('tbody');
    rows.forEach((row, i) => {
        const tr = document.createElement('tr');
        tr.appendChild(createCell('td', rowLabels[i], 'border border-gray-300'));
        row.forEach(val => tr.appendChild(createCell('td', Number(val).toFixed(2), 'border border-gray-300')));
        tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    return table;
}

function createCell(tag, content, className) {
    const cell = document.createElement(tag);
    cell.textContent = content;
    if (className) cell.className = className;
    return cell;
}

function showHistoryDetails(item) {
    const historyDetails = document.getElementById('history-details');
    if (!historyDetails) {
        console.error('Không tìm thấy phần tử history-details');
        return;
    }

    let id = item.calculation_id;
    let criteriaMatrix = item.criteria_matrix;
    let alternativeMatrices = item.alternative_matrices;
    let criteriaWeights = item.criteria_weights;
    let alternativeWeights = item.alternative_weights;
    let rankings = item.rankings;
    let alternativeRankings = item.alternative_rankings;
    let alternativeLambdaMax = item.alternative_lambda_max;
    let alternativeCi = item.alternative_ci;
    let alternativeCr = item.alternative_cr;
    let timestamp = item.timestamp;
    let lambdaMax = item.lambda_max;
    let ci = item.ci;
    let cr = item.cr;

    try {
        if (typeof id === 'string') id = JSON.parse(id);
        if (typeof criteriaMatrix === 'string') criteriaMatrix = JSON.parse(criteriaMatrix);
        if (typeof alternativeMatrices === 'string') alternativeMatrices = JSON.parse(alternativeMatrices);
        if (typeof criteriaWeights === 'string') criteriaWeights = JSON.parse(criteriaWeights);
        if (typeof alternativeWeights === 'string') alternativeWeights = JSON.parse(alternativeWeights);
        if (typeof rankings === 'string') rankings = JSON.parse(rankings);
        if (typeof alternativeRankings === 'string') alternativeRankings = JSON.parse(alternativeRankings);
        if (typeof alternativeLambdaMax === 'string') alternativeLambdaMax = JSON.parse(alternativeLambdaMax);
        if (typeof alternativeCi === 'string') alternativeCi = JSON.parse(alternativeCi);
        if (typeof alternativeCr === 'string') alternativeCr = JSON.parse(alternativeCr);
        
    } catch (error) {
        console.error('Lỗi khi phân tích JSON:', error);
        historyDetails.innerHTML = '<p class="text-red-500">Lỗi: Không thể phân tích dữ liệu lịch sử.</p>';
        return;
    }

    if (!item.criteria || !criteriaMatrix || !alternativeMatrices || !criteriaWeights || !alternativeWeights || !rankings) {
        historyDetails.innerHTML = '<p class="text-red-500">Dữ liệu lịch sử không đầy đủ để hiển thị.</p>';
        return;
    }

    const normalizedCriteriaMatrix = normalizeMatrix(criteriaMatrix);
    const criteriaWeightsCalc = calculateWeightsFromMatrix(criteriaMatrix);
    const normalizedAlternativeMatrices = {};
    const alternativeWeightsCalc = {};
    
    for (const criterion in alternativeMatrices) {
        normalizedAlternativeMatrices[criterion] = normalizeMatrix(alternativeMatrices[criterion]);
        alternativeWeightsCalc[criterion] = calculateWeightsFromMatrix(alternativeMatrices[criterion]);
    }

    const modal = document.createElement('div');
    modal.className = 'modal fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center';

    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content bg-white p-6 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto';

    modalContent.appendChild(createCell('h2', 'Chi tiết lịch sử tính toán', 'text-2xl font-bold mb-4'));
    modalContent.appendChild(createCell('p', `Thời gian: ${new Date(item.timestamp).toLocaleString('vi-VN')}`, 'mb-4'));

    modalContent.appendChild(createCell('h3', 'Ma trận tiêu chí đã nhập', 'text-xl font-semibold mb-2'));
    modalContent.appendChild(createTable(item.criteria, criteriaMatrix, item.criteria));

    modalContent.appendChild(createCell('h3', 'Ma trận tiêu chí chuẩn hóa', 'text-xl font-semibold mb-2'));
    modalContent.appendChild(createTable(item.criteria, normalizedCriteriaMatrix, item.criteria));

    modalContent.appendChild(createCell('h3', 'Xếp hạng theo trọng số tiêu chí', 'text-xl font-semibold mb-2'));
    const criteriaUl = document.createElement('ul');
    criteriaUl.className = 'list-disc pl-5 mb-4';
    Object.entries(criteriaWeights).forEach(([k, v]) => {
        const li = document.createElement('li');
        li.textContent = `${k}: ${Number(v).toFixed(2)}%`;
        criteriaUl.appendChild(li);
    });
    modalContent.appendChild(criteriaUl);

    modalContent.appendChild(createCell('h3', 'Chỉ số nhất quán tiêu chí', 'text-xl font-semibold mb-2'));
    modalContent.appendChild(createCell('p', `Lambda_max: ${Number(item.lambda_max || 0).toFixed(2)}`, 'mb-1'));
    modalContent.appendChild(createCell('p', `CI: ${Number(item.ci || 0).toFixed(2)}`, 'mb-1'));
    modalContent.appendChild(createCell('p', `CR: ${Number(item.cr || 0).toFixed(2)}`, 'mb-4'));
    
    for (const criterion of Object.keys(alternativeMatrices)) {
        const matrix = alternativeMatrices[criterion];
        const normMatrix = normalizedAlternativeMatrices[criterion];
        const altWeights = alternativeWeights[criterion];
        const altRanks = alternativeRankings?.[criterion] || [];

        modalContent.appendChild(createCell('h3', `Ma trận phương án theo ${criterion}`, 'text-xl font-semibold mb-2'));
        modalContent.appendChild(createTable(alternatives, matrix, alternatives));

        modalContent.appendChild(createCell('h3', `Ma trận chuẩn hóa theo ${criterion}`, 'text-xl font-semibold mb-2'));
        modalContent.appendChild(createTable(alternatives, normMatrix, alternatives));

        modalContent.appendChild(createCell('h3', `Trọng số phương án theo ${criterion}`, 'text-xl font-semibold mb-2'));
        const altUl = document.createElement('ul');
        altUl.className = 'list-disc pl-5 mb-4';
        Object.entries(altWeights).forEach(([k, v]) => {
            const li = document.createElement('li');
            li.textContent = `${k}: ${Number(v).toFixed(2)}%`;
            altUl.appendChild(li);
        });
        modalContent.appendChild(altUl);

        modalContent.appendChild(createCell('h3', `Xếp hạng phương án theo ${criterion}`, 'text-xl font-semibold mb-2'));
        const altOl = document.createElement('ol');
        altOl.className = 'list-decimal pl-5 mb-4';
        altRanks.forEach(r => {
            const li = document.createElement('li');
            li.textContent = `${r.name}: ${Number(r.score).toFixed(2)}%`;
            altOl.appendChild(li);
        });
        modalContent.appendChild(altOl);

        modalContent.appendChild(createCell('h3', `Chỉ số nhất quán theo ${criterion}`, 'text-xl font-semibold mb-2'));
        modalContent.appendChild(createCell('p', `Lambda_max: ${Number(alternativeLambdaMax?.[criterion] || 0).toFixed(2)}`, 'mb-1'));
        modalContent.appendChild(createCell('p', `CI: ${Number(alternativeCi?.[criterion] || 0).toFixed(2)}`, 'mb-1'));
        modalContent.appendChild(createCell('p', `CR: ${Number(alternativeCr?.[criterion] || 0).toFixed(2)}`, 'mb-4'));
    }

    modalContent.appendChild(createCell('h3', 'Xếp hạng tổng hợp', 'text-xl font-semibold mb-2'));
    const rankOl = document.createElement('ol');
    rankOl.className = 'list-decimal pl-5 mb-4';
    rankings.forEach(r => {
        const li = document.createElement('li');
        li.textContent = `${r.name}: ${Number(r.score).toFixed(2)}%`;
        rankOl.appendChild(li);
    });
    modalContent.appendChild(rankOl);

    const buttonDiv = document.createElement('div');
    buttonDiv.className = 'flex gap-2';

    const closeButton = document.createElement('button');
    closeButton.textContent = 'Đóng';
    closeButton.className = 'bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600';
    closeButton.onclick = closeHistoryDetails;
    buttonDiv.appendChild(closeButton);

    const pdfButton = document.createElement('button');
    pdfButton.textContent = 'Tải báo cáo PDF';
    pdfButton.className = 'bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600';
    pdfButton.onclick = () => downloadServerPDFFromClientData(item);
    buttonDiv.appendChild(pdfButton);

    const resetButton = document.createElement('button');
    resetButton.textContent = 'Quay lại';
    resetButton.className = 'bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600';
    resetButton.onclick = resetInterface;
    buttonDiv.appendChild(resetButton);

    modalContent.appendChild(buttonDiv);
    modal.appendChild(modalContent);
    historyDetails.innerHTML = '';
    historyDetails.appendChild(modal);
    historyDetails.classList.remove('hidden');

    document.addEventListener('keydown', handleEscKey);
}

function handleEscKey(event) {
    if (event.key === 'Escape') {
        closeHistoryDetails();
        document.removeEventListener('keydown', handleEscKey);
    }
}

function downloadServerPDFFromClientData(item) {
    fetch('/api/export-pdf-from-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
    })
    .then(res => {
        if (!res.ok) throw new Error("Tải PDF thất bại");
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Bao_cao_AHP_${item.calculation_id}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => console.error(err));
}


function closeHistoryDetails() {
    const historyDetails = document.getElementById('history-details');
    historyDetails.classList.add('hidden');
    historyDetails.innerHTML = '';
    document.removeEventListener('keydown', handleEscKey);
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

        window.historyData = history;

        const historyList = document.getElementById('history-list');
        if (!Array.isArray(history) || history.length === 0) {
            historyList.innerHTML = '<p class="text-gray-500">Không có bản ghi nào.</p>';
        } else {
            historyList.innerHTML = history.map((item, index) => `
                <div class="border-b py-2">
                    <p><strong>ID:</strong> ${item.calculation_id ?? 'N/A'}</p>
                    <p><strong>Thời gian:</strong> ${new Date(item.timestamp).toLocaleString()}</p>
                    <button onclick="showHistoryDetails(window.historyData[${index}])"
                            class="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                        Xem chi tiết lịch sử
                    </button>
                </div>
            `).join('');
        }

        document.getElementById('loading').classList.add('hidden');
        document.getElementById('history').classList.remove('hidden');
    } catch (error) {
        document.getElementById('buttons').classList.remove('hidden');
        document.getElementById('loading').textContent = `Lỗi: ${error.message}`;
        console.error('Lỗi:', error);
    }
}

async function showHistoryDetail(index) {
    const item = window.historyData?.[index];
    if (!item) {
        alert("Không tìm thấy dữ liệu lịch sử!");
        return;
    }

    showHistoryDetails(item);
}

function formatMatrix(matrix) {
    if (!matrix || !Array.isArray(matrix)) return 'Không có dữ liệu';
    return matrix.map(row => row.map(val => Number(val).toFixed(2)).join(' | ')).join('<br>');
}

function formatAlternativeRankings(altRankings) {
    if (!altRankings) return '<p>Không có dữ liệu xếp hạng theo tiêu chí.</p>';

    return Object.entries(altRankings).map(([criterion, rankings]) => {
        const listItems = rankings.map(r => `<li>${r.name}: ${Number(r.score).toFixed(2)}%</li>`).join('');
        return `<strong>${criterion}:</strong><ul>${listItems}</ul>`;
    }).join('');
}

async function renderCharts(data) {
    Object.keys(charts).forEach(chartId => {
        if (charts[chartId]) {
            charts[chartId].destroy();
            delete charts[chartId];
        }
    });

    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded. Please ensure the Chart.js script is included.');
        document.getElementById('loading').textContent = 'Lỗi: Chart.js không được tải.';
        return;
    }

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

    const overallRanking = document.getElementById('overall-ranking');
    overallRanking.innerHTML = `
        ${data.rankings.map(item => `<li>${item.name}: ${(item.score || 0).toFixed(2)}%</li>`).join('')}`;

    const criteriaChartsDiv = document.getElementById('criteria-charts');
    criteriaChartsDiv.innerHTML = '';

    const actualCriteria = Object.keys(data.alternative_rankings);
    for (const criterion of actualCriteria) {
        const safeId = criterion.replace(/[^\w-]/g, '-');
        const chartId = `chart-${safeId}`;
        const rankingId = `ranking-${safeId}`;

        criteriaChartsDiv.innerHTML += `
            <div class="card bg-white p-4 rounded-lg shadow">
                <h2 class="text-xl font-semibold mb-2">Xếp hạng theo ${criterion}</h2>
                <div class="chart-container">
                    <canvas id="${chartId}"></canvas>
                </div>
                <ol id="${rankingId}" class="list-decimal list-inside mt-4"></ol>
                <p class="mt-2"><strong>Lambda_max:</strong> ${(data.alternative_lambda_max[criterion] || 0).toFixed(2)}</p>
                <p><strong>CI:</strong> ${(data.alternative_ci[criterion] || 0).toFixed(2)}</p>
                <p><strong>CR:</strong> ${(data.alternative_cr[criterion] || 0).toFixed(2)}</p>
            </div>
        `;
    }

    await new Promise(resolve => setTimeout(resolve, 0));

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

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('excelFile');
    if (!fileInput.files.length) {
        alert('Vui lòng chọn một file Excel!');
        return;
    }

    const reader = new FileReader();
    reader.onload = async function (e) {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });

            if (!workbook.SheetNames.length) {
                throw new Error('File Excel không chứa sheet nào');
            }

            const criteriaSheet = workbook.Sheets[workbook.SheetNames[0]];
            const criteriaData = XLSX.utils.sheet_to_json(criteriaSheet, { header: 1 });
            if (!criteriaData.length) {
                throw new Error('Sheet tiêu chí rỗng');
            }

            const criteria = criteriaData[0].filter(c => c && typeof c === 'string');
            if (!criteria.length) {
                throw new Error('Không tìm thấy tiêu chí hợp lệ');
            }

            const criteria_matrix_raw = criteriaData.slice(1).filter(row => Array.isArray(row) && row.length > 0);
            if (criteria_matrix_raw.length < criteria.length) {
                throw new Error('Ma trận tiêu chí không đủ hàng so với số tiêu chí');
            }
            const criteria_matrix = criteria_matrix_raw.map(row => {
                const newRow = row.slice(0, criteria.length + 1);
                while (newRow.length < criteria.length + 1) {
                    newRow.push(0);
                }
                return newRow.slice(1).map(value => {
                    const num = parseFloat(value);
                    return isNaN(num) ? 0 : num;
                });
            });

            const alternative_matrices = {};
            for (let i = 1; i < workbook.SheetNames.length; i++) {
                const sheetName = workbook.SheetNames[i];
                const matrixSheet = workbook.Sheets[sheetName];
                const matrixDataRaw = XLSX.utils.sheet_to_json(matrixSheet, { header: 1 });
                const matrixData = matrixDataRaw.filter(row => Array.isArray(row) && row.length > 0);
                if (matrixData.length === 0) {
                    throw new Error(`Sheet "${sheetName}" không chứa dữ liệu hợp lệ`);
                }
                const matrixSize = matrixData.length - 1;
                alternative_matrices[sheetName] = matrixData.slice(1).map(row => {
                    const newRow = row.slice(1);
                    while (newRow.length < matrixSize) {
                        newRow.push(0);
                    }
                    return newRow.map(value => {
                        const num = parseFloat(value);
                        return isNaN(num) ? 0 : num;
                    });
                });
                if (alternative_matrices[sheetName].length !== matrixSize) {
                    throw new Error(`Ma trận phương án "${sheetName}" không đủ hàng`);
                }
            }

            console.log('criteria:', criteria);
            console.log('criteria_matrix:', criteria_matrix);
            console.log('alternative_matrices:', alternative_matrices);

            const loading = document.getElementById('loading');
            loading.textContent = 'Đang xử lý file Excel...';
            loading.classList.remove('hidden');

            try {
                const response = await fetch('/api/calculate-ahp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        criteria: criteria,
                        criteria_matrix: criteria_matrix,
                        alternative_matrices: alternative_matrices
                    })
                });
                const data = await response.json();
                loading.classList.add('hidden');
                if (response.ok) {
                    renderCharts(data);
                    document.getElementById('content').classList.remove('hidden');
                    alert('Tính toán AHP từ file Excel thành công!');
                } else {
                    alert(`Lỗi: ${data.error || 'Không thể xử lý ma trận'}`);
                }
            } catch (error) {
                loading.classList.add('hidden');
                alert(`Lỗi khi gửi file: ${error.message}`);
            }
        } catch (error) {
            alert(`Lỗi khi đọc file Excel: ${error.message}`);
        }
    };
    reader.readAsArrayBuffer(fileInput.files[0]);
});

function cleanMatrix(matrix) {
    if (!Array.isArray(matrix)) {
        throw new Error(`Ma trận không hợp lệ: Phải là mảng, nhận được ${typeof matrix}`);
    }
    if (matrix.length === 0 || !matrix.every(row => Array.isArray(row))) {
        throw new Error('Ma trận không hợp lệ: Phải là mảng 2 chiều');
    }

    const n = matrix.length;
    if (matrix.some((row, index) => row.length !== n)) {
        throw new Error(`Ma trận không vuông: Hàng ${index + 1} có ${row.length} cột, cần ${n} cột`);
    }

    const cleanedMatrix = matrix.slice(1).map(row => row.slice(1));
    const newSize = n - 1;

    if (newSize <= 0) {
        throw new Error('Ma trận sau khi bỏ hàng/cột đầu tiên không hợp lệ');
    }
    if (cleanedMatrix.some((row, index) => row.length !== newSize)) {
        throw new Error(`Ma trận sau khi bỏ cột đầu không vuông: Hàng ${index + 2} có ${row.length} cột, cần ${newSize} cột`);
    }

    for (let i = 0; i < newSize; i++) {
        for (let j = 0; j < newSize; j++) {
            const value = cleanedMatrix[i][j];
            if (i === j && Math.abs(value - 1) > 0.0001) {
                throw new Error(`Giá trị trên đường chéo chính tại [${i + 2}][${j + 2}] phải là 1`);
            }
            if (i !== j && (isNaN(value) || value <= 0)) {
                throw new Error(`Giá trị tại [${i + 2}][${j + 2}] phải là số dương`);
            }
        }
    }

    return cleanedMatrix;
}
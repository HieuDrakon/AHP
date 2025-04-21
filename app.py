from flask import Flask, request, jsonify, render_template
import numpy as np
import pandas as pd
from io import BytesIO
import base64
import matplotlib
# Use a non-interactive backend to avoid display issues
matplotlib.use('Agg')  # Set Agg backend before importing pyplot
import matplotlib.pyplot as plt
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Default data from Excel
criteria_names = ["Giá cả", "Khoảng cách", "Tiện nghi", "An ninh", "Dịch vụ xung quanh", "Môi trường sống"]
alternatives = ["Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường", "Chung cư mini", "Nhà ở cùng người thân"]

# Criteria comparison matrix (6x6)
default_criteria_matrix = np.array([
    [1, 3, 4, 5, 5, 7],
    [1/3, 1, 4, 3, 3, 5],
    [1/4, 1/4, 1, 3, 3, 5],
    [1/5, 1/3, 1/3, 1, 3, 5],
    [1/5, 1/3, 1/3, 1/3, 1, 3],
    [1/7, 1/5, 1/5, 1/5, 1/3, 1]
])

# Alternative comparison matrices (5x5 for each criterion)
default_alt_matrices = {
    "Giá cả": np.array([
        [1, 2, 3, 4, 4],
        [1/2, 1, 2, 3, 3],
        [1/3, 1/2, 1, 3, 3],
        [1/4, 1/3, 1/3, 1, 2],
        [1/4, 1/3, 1/3, 1/2, 1]
    ]),
    "Khoảng cách": np.array([
        [1, 2, 4, 5, 4],
        [1/2, 1, 3, 4, 4],
        [1/4, 1/3, 1, 3, 3],
        [1/5, 1/4, 1/3, 1, 2],
        [1/4, 1/4, 1/3, 1/2, 1]
    ]),
    "Tiện nghi": np.array([
        [1, 4, 4, 5, 4],
        [1/4, 1, 3, 4, 4],
        [1/4, 1/3, 1, 3, 3],
        [1/5, 1/4, 1/3, 1, 2],
        [1/4, 1/4, 1/3, 1/2, 1]
    ]),
    "An ninh": np.array([
        [1, 2, 3, 5, 0.25],
        [1/2, 1, 2, 0.25, 3],
        [1/3, 1/2, 1, 3, 4],
        [1/5, 4, 1/3, 1, 3],
        [4, 1/3, 1/4, 1/3, 1]
    ]),
    "Dịch vụ xung quanh": np.array([
        [1, 1/3, 0.2, 0.14285714285714285, 0.3333333333333333],
        [3, 1, 0.3333333333333333, 0.25, 3],
        [5, 3, 1, 0.3333333333333333, 3],
        [7, 4, 3, 1, 4],
        [3, 1/3, 1/3, 1/4, 1]
    ]),
    "Môi trường sống": np.array([
        [1, 0.3333333333333333, 0.25, 0.16666666666666666, 0.5],
        [3, 1, 0.3333333333333333, 0.2, 2],
        [4, 3, 1, 3, 6],
        [6, 5, 0.3333333333333333, 1, 5],
        [2, 0.5, 0.16666666666666666, 0.2, 1]
    ])
}

# Default weights and CR from Excel
default_criteria_weights = np.array([0.4094, 0.2308, 0.1492, 0.1101, 0.0667, 0.0338])
default_alt_weights = {
    "Giá cả": np.array([0.4028, 0.2492, 0.1809, 0.0956, 0.0715]),
    "Khoảng cách": np.array([0.4188, 0.2833, 0.1505, 0.0823, 0.0652]),
    "Tiện nghi": np.array([0.4632, 0.2456, 0.1474, 0.0802, 0.0636]),
    "An ninh": np.array([0.2841, 0.1614, 0.1879, 0.1931, 0.1734]),
    "Dịch vụ xung quanh": np.array([0.0468, 0.1466, 0.2496, 0.4611, 0.0959]),
    "Môi trường sống": np.array([0.0575, 0.1262, 0.4212, 0.3215, 0.0737])
}
default_criteria_cr = 0.0964
default_alt_cr = {
    "Giá cả": 0.0379,
    "Khoảng cách": 0.0553,
    "Tiện nghi": 0.0892,
    "An ninh": 0.6818,
    "Dịch vụ xung quanh": 0.0636,
    "Môi trường sống": 0.0865
}

# Saaty's scale for validation
saaty_scale = [1, 3, 5, 7, 9] + [1/x for x in [1, 3, 5, 7, 9]]

def normalize_matrix(matrix):
    col_sums = np.sum(matrix, axis=0)
    return matrix / col_sums

def calculate_weights(matrix):
    norm_matrix = normalize_matrix(matrix)
    return np.mean(norm_matrix, axis=1)

def consistency_ratio(matrix):
    n = matrix.shape[0]
    weights = calculate_weights(matrix)
    weighted_sum = np.dot(matrix, weights)
    lambda_max = np.mean(weighted_sum / weights)
    CI = (lambda_max - n) / (n - 1)
    RI = {1: 0.00, 2:0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49, 11: 1.51, 12: 1.54, 13: 1.56, 14: 1.58, 15: 1.59}
    if n > 15:
        RI[n] = 1.59 + (n - 15) * 0.01  # Approximation for larger matrices
    else:
        RI[n] = RI.get(n, 1.51)  # Default to 1.51 if not found
    return CI / RI

def validate_matrix(matrix):
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if i != j and not any(abs(matrix[i][j] - s) < 1e-6 for s in saaty_scale):
                return False, f"Giá trị {matrix[i][j]} tại [{i+1},{j+1}] không thuộc thang Saaty."
    return True, ""

def generate_chart(data, labels, title, ylabel):
    try:
        plt.figure(figsize=(8, 6))
        plt.bar(labels, data, color='skyblue')
        plt.title(title)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45)
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error generating chart: {str(e)}")
        return None

@app.route('/')
def index():
    try:
        # Calculate default normalized matrices
        default_norm_crit_matrix = normalize_matrix(default_criteria_matrix)
        default_norm_alt_matrices = {k: normalize_matrix(v) for k, v in default_alt_matrices.items()}
        
        # Calculate default final scores
        default_final_scores = np.zeros(len(alternatives))
        for i, crit in enumerate(criteria_names):
            default_final_scores += default_criteria_weights[i] * default_alt_weights[crit]
        
        # Default rankings
        default_rankings = np.argsort(-default_final_scores)
        default_ranked_alts = [{"name": alternatives[i], "score": default_final_scores[i]} for i in default_rankings]
        
        # Generate default visualizations
        default_crit_chart = generate_chart(
            default_criteria_weights, criteria_names, 'Trọng số tiêu chí (Mặc định)', 'Trọng số'
        )
        default_alt_chart = generate_chart(
            default_final_scores, alternatives, 'Điểm số phương án (Mặc định)', 'Điểm'
        )
        
        if default_crit_chart is None or default_alt_chart is None:
            app.logger.error("Failed to generate one or both charts")
            return "Error generating charts", 500

        return render_template(
            'index.j2',
            criteria_names=criteria_names,
            alternatives=alternatives,
            default_criteria_matrix=default_criteria_matrix.tolist(),
            default_norm_crit_matrix=default_norm_crit_matrix.tolist(),
            default_criteria_weights=default_criteria_weights.tolist(),
            default_criteria_cr=default_criteria_cr,
            default_alt_matrices={k: v.tolist() for k, v in default_alt_matrices.items()},
            default_norm_alt_matrices={k: v.tolist() for k, v in default_norm_alt_matrices.items()},
            default_alt_weights={k: v.tolist() for k, v in default_alt_weights.items()},
            default_alt_cr=default_alt_cr,
            default_final_scores=default_final_scores.tolist(),
            default_rankings=default_ranked_alts,
            default_crit_chart=default_crit_chart,
            default_alt_chart=default_alt_chart
        )
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return f"Internal server error: {str(e)}", 500

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        crit_matrix = np.array(data['criteria_matrix'], dtype=float)
        alt_matrices = {k: np.array(v, dtype=float) for k, v in data['alt_matrices'].items()}

        # Validate criteria matrix
        valid, msg = validate_matrix(crit_matrix)
        if not valid:
            return jsonify({"error": msg}), 400

        # Validate alternative matrices
        for crit, matrix in alt_matrices.items():
            valid, msg = validate_matrix(matrix)
            if not valid:
                return jsonify({"error": f"Ma trận {crit}: {msg}"}), 400

        # Calculate normalized matrices
        norm_crit_matrix = normalize_matrix(crit_matrix)
        norm_alt_matrices = {k: normalize_matrix(v) for k, v in alt_matrices.items()}

        # Calculate weights
        crit_weights = calculate_weights(crit_matrix)
        alt_weights = {k: calculate_weights(v) for k, v in alt_matrices.items()}

        # Calculate consistency ratios
        crit_cr = consistency_ratio(crit_matrix)
        alt_cr = {k: consistency_ratio(v) for k, v in alt_matrices.items()}

        # Calculate final scores
        final_scores = np.zeros(len(alternatives))
        for i, crit in enumerate(criteria_names):
            if crit in alt_weights:
                final_scores += crit_weights[i] * alt_weights[crit]

        # Rankings
        rankings = np.argsort(-final_scores)
        ranked_alternatives = [{"name": alternatives[i], "score": final_scores[i]} for i in rankings]

        # Generate visualizations
        crit_chart = generate_chart(crit_weights, criteria_names, 'Trọng số tiêu chí', 'Trọng số')
        alt_chart = generate_chart(final_scores, alternatives, 'Điểm số phương án', 'Điểm')
        
        if crit_chart is None or alt_chart is None:
            return jsonify({"error": "Failed to generate charts"}), 500

        return jsonify({
            "norm_crit_matrix": norm_crit_matrix.tolist(),
            "criteria_weights": crit_weights.tolist(),
            "criteria_cr": crit_cr,
            "norm_alt_matrices": {k: v.tolist() for k, v in norm_alt_matrices.items()},
            "alt_weights": {k: v.tolist() for k, v in alt_weights.items()},
            "alt_cr": alt_cr,
            "final_scores": final_scores.tolist(),
            "rankings": ranked_alternatives,
            "crit_chart": crit_chart,
            "alt_chart": alt_chart
        })
    except Exception as e:
        app.logger.error(f"Error in calculate route: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
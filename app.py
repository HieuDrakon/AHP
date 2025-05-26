import logging
import psycopg2
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime
import json
import pandas as pd
from werkzeug.utils import secure_filename
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="ahp",
            user="postgres",
            password="12345"
        )
        logging.debug("Kết nối cơ sở dữ liệu thành công")
        return conn
    except Exception as e:
        logging.error(f"Lỗi khi kết nối cơ sở dữ liệu: {e}")
        return None

def get_ahp_data_from_db():
    conn = get_db_connection()
    if not conn:
        return {"error": "Không thể kết nối đến cơ sở dữ liệu"}

    try:
        cur = conn.cursor()
        cur.execute("SELECT criterion_name, weight FROM criteria_weights")
        criteria_rows = cur.fetchall()
        criteria_weights = {row[0]: float(row[1]) for row in criteria_rows}

        alternatives = [
            "Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường",
            "Chung cư mini", "Nhà ở cùng người thân"
        ]
        alternative_weights = {}
        for criterion in criteria_weights.keys():
            cur.execute(
                "SELECT alternative_name, weight FROM alternative_weights WHERE criterion_name = %s",
                (criterion,)
            )
            weights = {row[0]: float(row[1]) for row in cur.fetchall()}
            alternative_weights[criterion] = weights

        overall_scores = {}
        for alt in alternatives:
            score = 0
            for criterion in criteria_weights:
                score += alternative_weights[criterion][alt] * criteria_weights[criterion]
            overall_scores[alt] = round(score * 100, 2)

        criteria_rankings = [
            {"name": criterion, "score": round(weight * 100, 2)}
            for criterion, weight in criteria_weights.items()
        ]
        criteria_rankings = sorted(criteria_rankings, key=lambda x: x["score"], reverse=True)

        alternative_rankings = {}
        for criterion in criteria_weights.keys():
            rankings = [
                {"name": alt, "score": round(alternative_weights[criterion][alt] * 100, 2)}
                for alt in alternatives
            ]
            alternative_rankings[criterion] = sorted(rankings, key=lambda x: x["score"], reverse=True)

        rankings = [
            {"name": alt, "score": score}
            for alt, score in overall_scores.items()
        ]
        rankings = sorted(rankings, key=lambda x: x["score"], reverse=True)

        return {
            "criteria_weights": {k: round(v * 100, 2) for k, v in criteria_weights.items()},
            "alternative_weights": {
                criterion: {alt: round(weight * 100, 2) for alt, weight in weights.items()}
                for criterion, weights in alternative_weights.items()
            },
            "rankings": rankings,
            "criteria_rankings": criteria_rankings,
            "alternative_rankings": alternative_rankings
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

def calculate_weights(matrix):
    matrix = np.array(matrix)
    n = matrix.shape[0]
    col_sums = matrix.sum(axis=0)
    normalized_matrix = matrix / col_sums
    weights = normalized_matrix.mean(axis=1)
    eigen_vector = weights
    lambda_max = (matrix @ eigen_vector).sum() / eigen_vector.sum()
    ci = (lambda_max - n) / (n - 1)
    ri_values = [0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    ri = ri_values[n-1] if n <= len(ri_values) else 1.49
    cr = ci / ri if ri > 0 else 0
    return weights.tolist(), cr, lambda_max, ci

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ahp-data', methods=['GET'])
def get_ahp_data():
    data = get_ahp_data_from_db()
    if "error" in data:
        return jsonify(data), 500
    return jsonify(data)

@app.route('/api/calculate-ahp', methods=['POST'])
def calculate_ahp():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Không có dữ liệu gửi lên"}), 400

    try:
        criteria = data.get('criteria', [])
        criteria_matrix = data.get('criteria_matrix', [])
        alternative_matrices = data.get('alternative_matrices', {})

        if len(criteria) < 2:
            return jsonify({"error": "Phải chọn ít nhất 2 tiêu chí"}), 400
        if len(criteria_matrix) != len(criteria):
            return jsonify({"error": "Ma trận tiêu chí không hợp lệ"}), 400

        # Tính trọng số tiêu chí
        criteria_weights, criteria_cr, criteria_lambda_max, criteria_ci = calculate_weights(criteria_matrix)
        if criteria_cr > 0.1:
            return jsonify({"error": f"Ma trận tiêu chí không nhất quán (CR = {criteria_cr:.2f})"}), 400

        criteria_weights_dict = {criteria[i]: round(w * 100, 2) for i, w in enumerate(criteria_weights)}

        alternatives = [
            "Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường",
            "Chung cư mini", "Nhà ở cùng người thân"
        ]
        alternative_weights = {}
        alternative_rankings = {}
        alternative_lambda_max = {}
        alternative_ci = {}
        alternative_cr = {}
        for criterion in criteria:
            matrix = alternative_matrices.get(criterion, [])
            if len(matrix) != len(alternatives):
                return jsonify({"error": f"Ma trận phương án cho '{criterion}' không hợp lệ"}), 400
            weights, cr, lambda_max, ci = calculate_weights(matrix)
            if cr > 0.1:
                return jsonify({"error": f"Ma trận phương án cho '{criterion}' không nhất quán (CR = {cr:.2f})"}), 400
            alternative_weights[criterion] = {alternatives[i]: round(w * 100, 2) for i, w in enumerate(weights)}
            rankings = [{"name": alternatives[i], "score": round(w * 100, 2)} for i, w in enumerate(weights)]
            alternative_rankings[criterion] = sorted(rankings, key=lambda x: x["score"], reverse=True)
            alternative_lambda_max[criterion] = lambda_max
            alternative_ci[criterion] = ci
            alternative_cr[criterion] = cr

        overall_scores = {}
        for alt in alternatives:
            score = 0
            for i, criterion in enumerate(criteria):
                score += alternative_weights[criterion][alt] * criteria_weights[i]
            overall_scores[alt] = round(score, 2)

        rankings = [
            {"name": alt, "score": score}
            for alt, score in overall_scores.items()
        ]
        rankings = sorted(rankings, key=lambda x: x["score"], reverse=True)

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500

        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO calculation_history (
                    timestamp, criteria, criteria_matrix, alternative_matrices,
                    criteria_weights, alternative_weights, rankings, lambda_max, ci, cr
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(),
                    criteria,
                    json.dumps(criteria_matrix),
                    json.dumps(alternative_matrices),
                    json.dumps(criteria_weights_dict),
                    json.dumps(alternative_weights),
                    json.dumps(rankings),
                    criteria_lambda_max,
                    criteria_ci,
                    criteria_cr
                )
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            return jsonify({"error": f"Lỗi khi lưu lịch sử: {str(e)}"}), 500
        finally:
            cur.close()
            conn.close()

        result = {
            "criteria_weights": criteria_weights_dict,
            "alternative_weights": alternative_weights,
            "rankings": rankings,
            "alternative_rankings": alternative_rankings,
            "lambda_max": criteria_lambda_max,
            "ci": criteria_ci,
            "cr": criteria_cr,
            "alternative_lambda_max": alternative_lambda_max,
            "alternative_ci": alternative_ci,
            "alternative_cr": alternative_cr
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/calculate-ahp-from-excel', methods=['POST'])
def calculate_ahp_from_excel():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Please upload an Excel file (.xlsx or .xls)"}), 400

    file_path = None
    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Read the Excel file with proper resource management
        with pd.ExcelFile(file_path) as xl:
            if "Criteria" not in xl.sheet_names:
                return jsonify({"error": "Excel file must contain a 'Criteria' sheet"}), 400

            # Read criteria matrix
            criteria_df = pd.read_excel(xl, sheet_name="Criteria", header=None)
            criteria_matrix = criteria_df.values.tolist()
            n_criteria = len(criteria_matrix)
            if any(len(row) != n_criteria for row in criteria_matrix):
                return jsonify({"error": "Criteria matrix must be square"}), 400

            # Assuming criteria names are in the first column (excluding header)
            criteria = criteria_df.iloc[:, 0].tolist()[1:] if criteria_df.shape[0] > 1 else [f"C{i+1}" for i in range(n_criteria)]
            if len(criteria) != n_criteria:
                return jsonify({"error": "Number of criteria names does not match matrix size"}), 400

            # Calculate criteria weights
            criteria_weights, criteria_cr, criteria_lambda_max, criteria_ci = calculate_weights(criteria_matrix)
            if criteria_cr > 0.1:
                return jsonify({"error": f"Criteria matrix is not consistent (CR = {criteria_cr:.2f})"}), 400

            criteria_weights_dict = {criteria[i]: round(w * 100, 2) for i, w in enumerate(criteria_weights)}

            # Define alternatives
            alternatives = [
                "Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường",
                "Chung cư mini", "Nhà ở cùng người thân"
            ]
            n_alternatives = len(alternatives)

            alternative_matrices = {}
            alternative_weights = {}
            alternative_rankings = {}
            alternative_lambda_max = {}
            alternative_ci = {}
            alternative_cr = {}

            # Read alternative matrices
            for criterion in criteria:
                if criterion not in xl.sheet_names:
                    return jsonify({"error": f"Sheet for criterion '{criterion}' not found"}), 400
                alt_df = pd.read_excel(xl, sheet_name=criterion, header=None)
                matrix = alt_df.values.tolist()
                if len(matrix) != n_alternatives or any(len(row) != n_alternatives for row in matrix):
                    return jsonify({"error": f"Alternative matrix for '{criterion}' must be {n_alternatives}x{n_alternatives}"}), 400
                alternative_matrices[criterion] = matrix
                weights, cr, lambda_max, ci = calculate_weights(matrix)
                if cr > 0.1:
                    return jsonify({"error": f"Alternative matrix for '{criterion}' is not consistent (CR = {cr:.2f})"}), 400
                alternative_weights[criterion] = {alternatives[i]: round(w * 100, 2) for i, w in enumerate(weights)}
                rankings = [{"name": alternatives[i], "score": round(w * 100, 2)} for i, w in enumerate(weights)]
                alternative_rankings[criterion] = sorted(rankings, key=lambda x: x["score"], reverse=True)
                alternative_lambda_max[criterion] = lambda_max
                alternative_ci[criterion] = ci
                alternative_cr[criterion] = cr

            # Calculate overall scores
            overall_scores = {}
            for alt in alternatives:
                score = 0
                for i, criterion in enumerate(criteria):
                    score += alternative_weights[criterion][alt] * criteria_weights[i]
                overall_scores[alt] = round(score, 2)

            rankings = [
                {"name": alt, "score": score}
                for alt, score in overall_scores.items()
            ]
            rankings = sorted(rankings, key=lambda x: x["score"], reverse=True)

            # Save to database
            conn = get_db_connection()
            if not conn:
                return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500

            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO calculation_history (
                        timestamp, criteria, criteria_matrix, alternative_matrices,
                        criteria_weights, alternative_weights, rankings, lambda_max, ci, cr
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.now(),
                        criteria,
                        json.dumps(criteria_matrix),
                        json.dumps(alternative_matrices),
                        json.dumps(criteria_weights_dict),
                        json.dumps(alternative_weights),
                        json.dumps(rankings),
                        criteria_lambda_max,
                        criteria_ci,
                        criteria_cr
                    )
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                return jsonify({"error": f"Lỗi khi lưu lịch sử: {str(e)}"}), 500
            finally:
                cur.close()
                conn.close()

            result = {
                "criteria_weights": criteria_weights_dict,
                "alternative_weights": alternative_weights,
                "rankings": rankings,
                "alternative_rankings": alternative_rankings,
                "lambda_max": criteria_lambda_max,
                "ci": criteria_ci,
                "cr": criteria_cr,
                "alternative_lambda_max": alternative_lambda_max,
                "alternative_ci": alternative_ci,
                "alternative_cr": alternative_cr
            }
            return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the uploaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError as pe:
                logging.warning(f"Could not delete file {file_path}: {pe}")
                # Optionally, schedule deletion for later or notify user

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT calculation_id, timestamp, criteria, criteria_weights, 
                   alternative_weights, rankings, lambda_max, ci, cr
            FROM calculation_history
            ORDER BY timestamp DESC
            """
        )
        rows = cur.fetchall()
        history = [
            {
                "calculation_id": row[0],
                "timestamp": row[1].isoformat(),
                "criteria": row[2],
                "criteria_weights": row[3],
                "alternative_weights": row[4],
                "rankings": row[5],
                "lambda_max": float(row[6]) if row[6] is not None else 0.0,
                "ci": float(row[7]) if row[7] is not None else 0.0,
                "cr": float(row[8]) if row[8] is not None else 0.0
            }
            for row in rows
        ]
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)

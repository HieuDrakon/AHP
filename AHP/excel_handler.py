# excel_handler.py
import pandas as pd
from config import Config
from ahp_utils import calculate_weights
import os, json
from werkzeug.utils import secure_filename
from datetime import datetime
from db import get_db_connection
import logging
from flask import jsonify, send_file

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def validate_matrix(matrix, valid_values=[2, 3, 4, 5, 6, 7, 8, 9, 0.5, 0.333, 0.25, 0.2, 0.167, 0.143, 0.125, 0.111]):
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            if i == j and matrix[i][j] != 1:
                return False, f"Diagonal element at ({i},{j}) must be 1"
            if i != j and not any(abs(matrix[i][j] - v) < 1e-4 for v in valid_values):
                return False, f"Invalid value {matrix[i][j]} at position ({i},{j})"
            if i != j and abs(matrix[i][j] - 1/matrix[j][i]) > 0.01:
                return False, f"Matrix not symmetric at positions ({i},{j}) and ({j},{i})"
    return True, None

def process_excel_file(file):
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format. Only .xlsx and .xls are allowed"}), 400
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        with pd.ExcelFile(file_path) as xl:
            if "Criteria" not in xl.sheet_names:
                return jsonify({"error": "Excel file must contain a 'Criteria' sheet"}), 400

            criteria_df = pd.read_excel(xl, sheet_name="Criteria", header=None)
            criteria = criteria_df.iloc[0, 1:].tolist()
            criteria_matrix = criteria_df.iloc[1:, 1:].values.tolist()
            n_criteria = len(criteria_matrix)
            if any(len(row) != n_criteria for row in criteria_matrix):
                return jsonify({"error": "Criteria matrix must be square"}), 400

            valid, error = validate_matrix(criteria_matrix)
            if not valid:
                return jsonify({"error": error}), 400

            criteria = criteria_df.iloc[:, 0].tolist()[1:] if criteria_df.shape[0] > 1 else [f"C{i+1}" for i in range(n_criteria)]
            if len(criteria) != n_criteria:
                return jsonify({"error": "Number of criteria names does not match matrix size"}), 400

            criteria_weights, criteria_cr, criteria_lambda_max, criteria_ci = calculate_weights(criteria_matrix)
            if criteria_cr > 0.1:
                return jsonify({"error": f"Criteria matrix is not consistent (CR = {criteria_cr:.2f})"}), 400

            criteria_weights_dict = {criteria[i]: round(w * 100, 2) for i, w in enumerate(criteria_weights)}

            alternatives = [
                "Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường",
                "Chung cư mini", "Nhà ở cùng người thân"
            ]
            n_alt = len(alternatives)

            alternative_matrices = {}
            alternative_weights = {}
            alternative_rankings = {}
            alternative_lambda_max = {}
            alternative_ci = {}
            alternative_cr = {}

            for criterion in criteria:
                if criterion not in xl.sheet_names:
                    return jsonify({"error": f"Sheet for criterion '{criterion}' not found"}), 400
                alt_df = pd.read_excel(xl, sheet_name=criterion, header=None)
                matrix = alt_df.iloc[1:, 1:].values.tolist()  # bỏ dòng/cột tiêu đề

                if len(matrix) != n_alt or any(len(row) != n_alt for row in matrix):
                    return jsonify({"error": f"Matrix for '{criterion}' must be {n_alt}x{n_alt}"}), 400
                
                valid, error = validate_matrix(matrix)
                if not valid:
                    return jsonify({"error": error}), 400

                alternative_matrices[criterion] = matrix
                weights, cr, lambda_max, ci = calculate_weights(matrix)
                if cr > 0.1:
                    return jsonify({"error": f"Matrix for '{criterion}' is not consistent (CR = {cr:.2f})"}), 400
                alternative_weights[criterion] = {alternatives[i]: round(w * 100, 2) for i, w in enumerate(weights)}
                alternative_rankings[criterion] = sorted(
                    [{"name": alternatives[i], "score": round(w * 100, 2)} for i, w in enumerate(weights)],
                    key=lambda x: x["score"], reverse=True
                )
                alternative_lambda_max[criterion] = lambda_max
                alternative_ci[criterion] = ci
                alternative_cr[criterion] = cr

            overall_scores = {}
            for alt in alternatives:
                score = sum(alternative_weights[criterion][alt] * criteria_weights[i] for i, criterion in enumerate(criteria))
                overall_scores[alt] = round(score, 2)

            rankings = sorted(
                [{"name": alt, "score": score} for alt, score in overall_scores.items()],
                key=lambda x: x["score"], reverse=True
            )

            conn = get_db_connection()
            if not conn:
                return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO calculation_history (
                        timestamp, criteria, criteria_matrix, alternative_matrices,
                        criteria_weights, alternative_weights, rankings, 
                        lambda_max, ci, cr,
                        alternative_rankings, alternative_lambda_max, alternative_ci, alternative_cr
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        criteria_cr,
                        json.dumps(alternative_rankings),
                        json.dumps(alternative_lambda_max),
                        json.dumps(alternative_ci),
                        json.dumps(alternative_cr)
                    )
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                return jsonify({"error": f"Lỗi khi lưu lịch sử: {str(e)}"}), 500
            finally:
                cur.close()
                conn.close()

            return {
                "criteria": criteria,
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
    except Exception as e:
        return jsonify({"error": f"Error processing Excel file: {str(e)}"}), 500
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError as pe:
                logging.warning(f"Could not delete file {file_path}: {pe}")


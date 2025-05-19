
import logging
import psycopg2
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime
import json
# Cấu hình logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

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

        # Lấy danh sách tiêu chí và trọng số
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

        # Tính điểm tổng hợp
        overall_scores = {}
        for alt in alternatives:
            score = 0
            for criterion in criteria_weights:
                score += alternative_weights[criterion][alt] * criteria_weights[criterion]
            overall_scores[alt] = round(score * 100, 2)

        # Tạo xếp hạng tiêu chí
        criteria_rankings = [
            {"name": criterion, "score": round(weight * 100, 2)}
            for criterion, weight in criteria_weights.items()
        ]
        criteria_rankings = sorted(criteria_rankings, key=lambda x: x["score"], reverse=True)

        # Tạo xếp hạng phương án theo tiêu chí
        alternative_rankings = {}
        for criterion in criteria_weights.keys():
            rankings = [
                {"name": alt, "score": round(alternative_weights[criterion][alt] * 100, 2)}
                for alt in alternatives
            ]
            alternative_rankings[criterion] = sorted(rankings, key=lambda x: x["score"], reverse=True)

        # Tạo xếp hạng tổng hợp
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
    """Tính trọng số từ ma trận so sánh cặp"""
    matrix = np.array(matrix)
    n = matrix.shape[0]
    # Chuẩn hóa ma trận
    col_sums = matrix.sum(axis=0)
    normalized_matrix = matrix / col_sums
    # Tính trọng số
    weights = normalized_matrix.mean(axis=1)
    # Tính CR (Consistency Ratio)
    eigen_vector = weights
    lambda_max = (matrix @ eigen_vector).sum() / eigen_vector.sum()
    ci = (lambda_max - n) / (n - 1)
    ri_values = [0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    ri = ri_values[n-1] if n <= len(ri_values) else 1.49
    cr = ci / ri if ri > 0 else 0
    return weights.tolist(), cr

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
        criteria_weights, criteria_cr = calculate_weights(criteria_matrix)
        if criteria_cr > 0.1:
            return jsonify({"error": f"Ma trận tiêu chí không nhất quán (CR = {criteria_cr:.2f})"}), 400

        criteria_weights_dict = {criteria[i]: round(w * 100, 2) for i, w in enumerate(criteria_weights)}

        # Tính trọng số phương án
        alternatives = [
            "Ký túc xá trong trường", "Nhà trọ gần trường", "Nhà trọ xa trường",
            "Chung cư mini", "Nhà ở cùng người thân"
        ]
        alternative_weights = {}
        alternative_rankings = {}
        for criterion in criteria:
            matrix = alternative_matrices.get(criterion, [])
            if len(matrix) != len(alternatives):
                return jsonify({"error": f"Ma trận phương án cho '{criterion}' không hợp lệ"}), 400
            weights, cr = calculate_weights(matrix)
            if cr > 0.1:
                return jsonify({"error": f"Ma trận phương án cho '{criterion}' không nhất quán (CR = {cr:.2f})"}), 400
            alternative_weights[criterion] = {alternatives[i]: round(w * 100, 2) for i, w in enumerate(weights)}
            rankings = [{"name": alternatives[i], "score": round(w * 100, 2)} for i, w in enumerate(weights)]
            alternative_rankings[criterion] = sorted(rankings, key=lambda x: x["score"], reverse=True)

        # Tính điểm tổng hợp
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

        # Lưu vào database
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500

        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO calculation_history (
                    timestamp, criteria, criteria_matrix, alternative_matrices,
                    criteria_weights, alternative_weights, rankings
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    datetime.now(),
                    criteria,
                    json.dumps(criteria_matrix),
                    json.dumps(alternative_matrices),
                    json.dumps(criteria_weights_dict),
                    json.dumps(alternative_weights),
                    json.dumps(rankings)
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
            "alternative_rankings": alternative_rankings
        }
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Không thể kết nối đến cơ sở dữ liệu"}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT calculation_id, timestamp, criteria, criteria_weights, alternative_weights, rankings
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
                "rankings": row[5]
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

# ahp_api.py
import io
from flask import Blueprint, abort, render_template, request, jsonify,send_file
import pdfkit
from ahp_utils import calculate_weights
from db import get_db_connection
from excel_handler import process_excel_file
from getdata import get_history_data
from datetime import datetime
import json

from datetime import datetime

ahp_bp = Blueprint('ahp', __name__)


import json

@ahp_bp.route('/api/export-pdf-from-json', methods=['POST'])
def export_pdf_from_json():
    try:
        data = request.get_json()
        if not data:
            abort(400, 'Không nhận được dữ liệu JSON')

        # Tiền xử lý: chuyển các trường JSON string thành dict/list Python
        if isinstance(data.get('criteria'), str):
            data['criteria'] = json.loads(data['criteria'].replace("'", '"'))

        # Nếu alternative_matrices là string JSON, parse luôn
        if isinstance(data.get('alternative_matrices'), str):
            data['alternative_matrices'] = json.loads(data['alternative_matrices'].replace("'", '"'))

        # Tương tự với các trường khác nếu cần

        html = render_template('report_template.html', data=data)
        options = {
            'encoding': 'UTF-8',
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'enable-local-file-access': None
        }
        pdf = pdfkit.from_string(html, False, options=options)

        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Bao_cao_AHP_{data.get("calculation_id", "unknown")}.pdf'
        )
    except Exception as e:
        abort(500, f'Lỗi khi tạo PDF: {str(e)}')



@ahp_bp.route('/api/calculate-ahp', methods=['POST'])
def calculate_ahp():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Không có dữ liệu gửi lên"}), 400

    criteria = data.get('criteria', [])
    criteria_matrix = data.get('criteria_matrix', [])
    alternative_matrices = data.get('alternative_matrices', {})

    if len(criteria) < 2:
        return jsonify({"error": "Phải chọn ít nhất 2 tiêu chí"}), 400

    if len(criteria_matrix) != len(criteria):
        return jsonify({"error": "Ma trận tiêu chí không hợp lệ"}), 400

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

    return jsonify({
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
    })

@ahp_bp.route('/api/calculate-ahp-from-excel', methods=['POST'])
def calculate_ahp_from_excel():
    if 'file' not in request.files:
        return jsonify({"error": "Không có file được tải lên"}), 400
    file = request.files['file']
    result = process_excel_file(file)
    if isinstance(result, tuple):
        return result  # Trả về phản hồi lỗi trực tiếp (jsonify response, status code)
    return jsonify(result)  # Trả về kết quả thành công dưới dạng JSON

@ahp_bp.route('/api/history', methods=['GET'])
def get_history():
    history_id = request.args.get('id')
    if history_id:
        try:
            history_id = int(history_id)
        except ValueError:
            return jsonify({"error": "ID không hợp lệ"}), 400
    
    data = get_history_data(history_id)  # trả về 1 bản ghi hoặc danh sách tùy tham số
    
    if "error" in data:
        return jsonify(data), 500
    return jsonify(data)


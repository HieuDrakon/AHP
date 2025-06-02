# getdata.py
import logging
from db import get_db_connection
from flask import jsonify

def get_history_data_by_id(history_id):
    conn = get_db_connection()
    if not conn:
        logging.error("Không thể kết nối đến cơ sở dữ liệu")
        return {"error": "Không thể kết nối đến cơ sở dữ liệu"}

    try:
        cur = conn.cursor()
        logging.debug(f"Truy vấn bản ghi lịch sử với calculation_id: {history_id}")
        cur.execute(
            """
            SELECT calculation_id, timestamp, criteria, criteria_matrix, 
                criteria_weights, alternative_matrices, alternative_weights, 
                rankings, alternative_rankings, lambda_max, ci, cr,
                alternative_lambda_max, alternative_ci, alternative_cr
            FROM calculation_history
            WHERE calculation_id = %s
            """,
            (history_id,)  # Truyền history_id vào truy vấn
        )
        rows = cur.fetchall()
        logging.debug(f"Số bản ghi trả về: {len(rows)}")
        if not rows:
            logging.warning(f"Không tìm thấy bản ghi với calculation_id: {history_id}")
            return []
        history = [
            {
                "calculation_id": row[0],
                "timestamp": row[1].isoformat(),
                "criteria": row[2],
                "criteria_matrix": row[3],
                "criteria_weights": row[4],
                "alternative_matrices": row[5],
                "alternative_weights": row[6],
                "rankings": row[7],
                "alternative_rankings": row[8],
                "lambda_max": float(row[9]) if row[9] is not None else 0.0,
                "ci": float(row[10]) if row[10] is not None else 0.0,
                "cr": float(row[11]) if row[11] is not None else 0.0,
                "alternative_lambda_max": row[12],
                "alternative_ci": row[13],
                "alternative_cr": row[14]
            }
            for row in rows
        ]
        return history
    except Exception as e:
        logging.error(f"Lỗi khi truy vấn lịch sử với ID {history_id}: {str(e)}")
        return {"error": f"Lỗi khi truy vấn lịch sử: {str(e)}"}
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()

def get_history_data(history_id=None):
    conn = get_db_connection()
    if not conn:
        logging.error("Không thể kết nối đến cơ sở dữ liệu")
        return {"error": "Không thể kết nối đến cơ sở dữ liệu"}

    try:
        cur = conn.cursor()
        if history_id:
            logging.debug(f"Truy vấn bản ghi lịch sử với calculation_id: {history_id}")
            cur.execute(
                """
                SELECT calculation_id, timestamp, criteria, criteria_matrix, 
                    criteria_weights, alternative_matrices, alternative_weights, 
                    rankings, alternative_rankings, lambda_max, ci, cr,
                    alternative_lambda_max, alternative_ci, alternative_cr
                FROM calculation_history
                WHERE calculation_id = %s
                """,
                (history_id,)
            )
        else:
            logging.debug("Truy vấn tất cả lịch sử")
            cur.execute(
                """
                SELECT calculation_id, timestamp, criteria, criteria_matrix, 
                    criteria_weights, alternative_matrices, alternative_weights, 
                    rankings, alternative_rankings, lambda_max, ci, cr,
                    alternative_lambda_max, alternative_ci, alternative_cr
                FROM calculation_history
                ORDER BY timestamp DESC
                """
            )
        rows = cur.fetchall()
        logging.debug(f"Số bản ghi trả về: {len(rows)}")
        if not rows and history_id:
            logging.warning(f"Không tìm thấy bản ghi với calculation_id: {history_id}")
            return []
        history = [
            {
                "calculation_id": row[0],
                "timestamp": row[1].isoformat(),
                "criteria": row[2],
                "criteria_matrix": row[3],
                "criteria_weights": row[4],
                "alternative_matrices": row[5],
                "alternative_weights": row[6],
                "rankings": row[7],
                "alternative_rankings": row[8],
                "lambda_max": float(row[9]) if row[9] is not None else 0.0,
                "ci": float(row[10]) if row[10] is not None else 0.0,
                "cr": float(row[11]) if row[11] is not None else 0.0,
                "alternative_lambda_max": row[12],
                "alternative_ci": row[13],
                "alternative_cr": row[14]
            }
            for row in rows
        ]
        return history
    except Exception as e:
        logging.error(f"Lỗi khi truy vấn lịch sử: {str(e)}")
        return {"error": f"Lỗi khi truy vấn lịch sử: {str(e)}"}
    finally:
        if 'cur' in locals():
            cur.close()
        if conn:
            conn.close()
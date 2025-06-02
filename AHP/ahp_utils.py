# ahp_utils.py
import numpy as np

def calculate_weights(matrix):
    matrix = np.array(matrix)
    n = matrix.shape[0]
    
    # Bước 1: Chuẩn hóa ma trận
    col_sums = matrix.sum(axis=0)
    normalized_matrix = matrix / col_sums
    weights = normalized_matrix.mean(axis=1)
    
    # Bước 2: Tính lambda_max đúng cách
    Aw = matrix @ weights
    lambda_max = np.sum(Aw / weights) / n

    # Bước 3: Tính CI và CR
    ci = (lambda_max - n) / (n - 1)
    ri_values = [0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]
    ri = ri_values[n - 1] if n <= len(ri_values) else 1.49
    cr = ci / ri if ri > 0 else 0

    if cr >= 0.1:
        raise ValueError("Tỷ lệ nhất quán (CR) quá cao, cho thấy sự không nhất quán trong so sánh từng cặp.")

    return weights.tolist(), cr, lambda_max, ci


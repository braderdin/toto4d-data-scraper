# Path: /home/braderdin/toto4d-data-scraper/python_script/experiments/exp_filter_engine.py

import math
from collections import Counter

def apply_sum_filter(candidates, min_sum=10, max_sum=26):
    """
    Menapis nombor dengan jumlah digit di luar julat biasa (10 <= S <= 26).
    """
    filtered = []
    for num in candidates:
        digits_sum = sum(int(d) for d in num)
        if min_sum <= digits_sum <= max_sum:
            filtered.append(num)
    return filtered

def apply_parity_filter(candidates):
    """
    Menolak nisbah ganjil:genap ekstrim (0:4 dan 4:0).
    Hanya mengekalkan nisbah 2:2, 3:1, dan 1:3.
    """
    filtered = []
    for num in candidates:
        odd_count = sum(1 for d in num if int(d) % 2 != 0)
        if odd_count in [1, 2, 3]:  # Menolak 0 ganjil atau 4 ganjil
            filtered.append(num)
    return filtered

def build_position_probability_matrix(all_numbers):
    """
    Menghitung kebarangkalian marginal P(d_i = k) bagi setiap posisi (0 hingga 3).
    """
    total_samples = len(all_numbers)
    matrix = [{d: 0 for d in range(10)} for _ in range(4)]

    for num in all_numbers:
        for pos in range(4):
            digit = int(num[pos])
            matrix[pos][digit] += 1

    # Tukar kepada kebarangkalian P(d_i = k)
    prob_matrix = []
    for pos in range(4):
        prob_matrix.append({k: v / total_samples for k, v in matrix[pos].items()})

    return prob_matrix

def calculate_candidate_score(num_str, prob_matrix):
    """
    Menghitung skor kebarangkalian gabungan bagi sesuatu nombor berdasarkan matriks posisi.
    """
    score = 1.0
    for pos in range(4):
        digit = int(num_str[pos])
        score *= prob_matrix[pos][digit]
    return score

def compute_poisson_latency(all_numbers, target_length=100):
    """
    Menghitung selang masa (latency) dan kadar ekspektasi Poisson bagi setiap digit.
    """
    recent_sample = all_numbers[-target_length:] if len(all_numbers) >= target_length else all_numbers
    counts = Counter("".join(recent_sample))
    
    # Lambda (kadar jangkaan kemunculan digit per kedudukan)
    total_digits = len(recent_sample) * 4
    lambda_rate = total_digits / 10.0

    scores = {}
    for d in range(10):
        k = counts.get(str(d), 0)
        # Taburan Poisson: P(k) = (lambda^k * e^(-lambda)) / k!
        poisson_prob = (math.pow(lambda_rate, k) * math.exp(-lambda_rate)) / math.factorial(k)
        scores[str(d)] = poisson_prob

    return scores
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 37_ensemble_multi_regime_ibox.py
FORMULA NAME : Multi-Regime Ensemble & Asymmetric iBox Master (V2 - 9M Train / 3M Test)
DESCRIPTION  : Menggabungkan 4 formula teras:
               1. F18 - Dual-Window Dirichlet Bayesian Momentum (Short 12 vs Long 60)
               2. F20 - Dynamic Regime-Switching Gate (Twin Density + Entropy Filter)
               3. F22 - Triplet / 4-Way Asymmetric Yield Hunter (Permutation Multiplier)
               4. F36 - Tuned Continuous Exponential Decay Gate (EMA lambda=0.08)

PENAMBAHBAIKAN V2:
               - Tetingkap Latihan Tepat 9 Bulan (~275 Hari Gelongsor).
               - Tetingkap Ujian 3 Bulan Terkini (~92 Hari).
               - Orthogonal Triplet & Twin Diversification (Haramkan digit triplet sama).
               - Pembobotan Hadiah Utama Diperkukuh (Mengurangkan noise consolation).
               
STRATEGI BET : Tepat 20 Nombor (Modal Tetap RM 20.00 / Cabutan):
               - 4x Permutasi 4  (Triplet AAAB) : iBox RM1 = RM4
               - 7x Permutasi 6  (2-Pasang AABB): iBox RM1 = RM7
               - 6x Permutasi 12 (1-Pasang AABC): iBox RM1 = RM6
               - 3x Permutasi 24 (Berbeza ABCD) : iBox RM1 = RM3
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import sys
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict, Counter

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

# ==========================================
# KONFIGURASI DIREKTORI & LALUAN FAIL (DINAMIK)
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_37_ensemble_multi_regime_ibox.json")

# ==========================================
# STRUKTUR BAYARAN RASMI TOTO 4D (BIG iBOX RM1)
# ==========================================
IBOX_BIG_PAYOUT = {
    '1st': {24: 105.0, 12: 209.0, 6: 417.0, 4: 625.0},
    '2nd': {24: 42.0,  12: 84.0,  6: 167.0, 4: 250.0},
    '3rd': {24: 21.0,  12: 42.0,  6: 84.0,  4: 125.0},
    'special': {24: 8.0, 12: 15.0, 6: 30.0, 4: 45.0},
    'consolation': {24: 3.0, 12: 5.0, 6: 10.0, 4: 15.0}
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, TypeError):
            pass
    return datetime.min

def get_permutation_count(num_str):
    counts = Counter(str(num_str)).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def get_canonical_box(num_str):
    return "".join(sorted(str(num_str).strip()))

# ==========================================
# ENJIN 4 FORMULA ASAL (TERSELARAS)
# ==========================================
def compute_formula_18_engine(history_draws):
    """F18: Dual-Window Bayesian Momentum"""
    total_draws = len(history_draws)
    short_history = history_draws[-12:] if total_draws >= 12 else history_draws
    long_history = history_draws[-50:] if total_draws >= 50 else history_draws

    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(4)]
    for draw in long_history:
        items = [(draw.get('1st_prize'), 4.5), (draw.get('2nd_prize'), 3.2), (draw.get('3rd_prize'), 2.2)]
        items += [(x, 0.8) for x in draw.get('special_prizes', [])]
        items += [(x, 0.4) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4):
                    pos_alphas_long[p][int(s[p])] += w

    pos_alphas_short = [{d: 0.5 for d in range(10)} for _ in range(4)]
    pair_alphas_short = defaultdict(lambda: 0.2)
    for idx, draw in enumerate(short_history):
        rec_boost = 1.0 + (idx / len(short_history)) * 1.2
        items = [(draw.get('1st_prize'), 5.0), (draw.get('2nd_prize'), 3.5), (draw.get('3rd_prize'), 2.5)]
        items += [(x, 1.0) for x in draw.get('special_prizes', [])]
        items += [(x, 0.5) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                wb = w * rec_boost
                for p in range(4):
                    pos_alphas_short[p][int(s[p])] += wb
                pair_alphas_short[(int(s[0]), int(s[1]))] += wb * 0.5
                pair_alphas_short[(int(s[2]), int(s[3]))] += wb * 0.5

    combined_pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        tot_l = sum(pos_alphas_long[p].values())
        tot_s = sum(pos_alphas_short[p].values())
        for d in range(10):
            p_long = pos_alphas_long[p][d] / tot_l
            p_short = pos_alphas_short[p][d] / tot_s
            prob = (0.30 * p_long) + (0.70 * p_short)
            combined_pos_probs[p][d] = max(prob, 1e-6)
            shannon_entropy -= prob * math.log(max(prob, 1e-6))

    tot_pair = sum(pair_alphas_short.values()) or 1.0
    return combined_pos_probs, pair_alphas_short, tot_pair, shannon_entropy

def compute_formula_20_engine(history_draws):
    """F20: Dynamic Regime-Switching"""
    total_draws = len(history_draws)
    recent_15 = history_draws[-15:] if total_draws >= 15 else history_draws

    twin_count = 0
    total_prizes = 0
    for draw in recent_15:
        items = [draw.get('1st_prize'), draw.get('2nd_prize'), draw.get('3rd_prize')]
        items += draw.get('special_prizes', []) + draw.get('consolation_prizes', [])
        for num_str in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                total_prizes += 1
                if get_permutation_count(num_str) in (12, 6, 4):
                    twin_count += 1

    twin_ratio = twin_count / max(total_prizes, 1)

    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_alphas = defaultdict(lambda: 0.5)
    double_scores = defaultdict(float)

    for idx, draw in enumerate(history_draws):
        recency = 1.0 + (idx / total_draws) * 0.9
        items = [(draw.get('1st_prize'), 4.5), (draw.get('2nd_prize'), 3.2), (draw.get('3rd_prize'), 2.2)]
        items += [(x, 0.8) for x in draw.get('special_prizes', [])]
        items += [(x, 0.4) for x in draw.get('consolation_prizes', [])]
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * recency
                cnt = Counter(num_str)
                for d_val, freq in cnt.items():
                    if freq >= 2:
                        double_scores[int(d_val)] += w * freq
                for p in range(4):
                    pos_alphas[p][int(num_str[p])] += w
                pair_alphas[(int(num_str[0]), int(num_str[1]))] += w * 0.5
                pair_alphas[(int(num_str[2]), int(num_str[3]))] += w * 0.5

    pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        tot_a = sum(pos_alphas[p].values())
        for d in range(10):
            prob = pos_alphas[p][d] / tot_a
            pos_probs[p][d] = max(prob, 1e-6)
            shannon_entropy -= prob * math.log(max(prob, 1e-6))

    tot_pair = sum(pair_alphas.values()) or 1.0
    tot_double = sum(double_scores.values()) or 1.0
    is_twin_regime = (twin_ratio >= 0.38) and (shannon_entropy < 8.35)
    return pos_probs, pair_alphas, tot_pair, double_scores, tot_double, twin_ratio, is_twin_regime

def compute_formula_22_engine(history_draws):
    """F22: Triplet / 4-Way Asymmetric Yield Hunter"""
    total_draws = len(history_draws)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    digit_momentum = defaultdict(float)
    pair_affinity = defaultdict(float)

    for idx, draw in enumerate(history_draws):
        recency = 1.0 + (idx / total_draws) * 1.0
        items = [(draw.get('1st_prize'), 5.0), (draw.get('2nd_prize'), 3.5), (draw.get('3rd_prize'), 2.5)]
        items += [(x, 0.8) for x in draw.get('special_prizes', [])]
        items += [(x, 0.4) for x in draw.get('consolation_prizes', [])]
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * recency
                for p in range(4):
                    d = int(num_str[p])
                    pos_alphas[p][d] += w
                    digit_momentum[d] += w
                pair_affinity[(int(num_str[0]), int(num_str[1]))] += w * 0.5
                pair_affinity[(int(num_str[2]), int(num_str[3]))] += w * 0.5

    pos_probs = [{} for _ in range(4)]
    for p in range(4):
        tot_a = sum(pos_alphas[p].values())
        for d in range(10):
            pos_probs[p][d] = max(pos_alphas[p][d] / tot_a, 1e-6)

    tot_mom = sum(digit_momentum.values()) or 1.0
    tot_pair = sum(pair_affinity.values()) or 1.0
    top_digits = sorted(digit_momentum.items(), key=lambda x: x[1], reverse=True)
    dominant_power = (top_digits[0][1] / tot_mom) if top_digits else 0.1
    is_high_triplet = dominant_power >= 0.125
    return pos_probs, pair_affinity, tot_pair, dominant_power, is_high_triplet

def compute_formula_36_engine(history_draws):
    """F36: Tuned Continuous EMA Decay Gate"""
    total_draws = len(history_draws)
    decay_lambda = 0.08
    pos_ema_weights = [defaultdict(float) for _ in range(4)]
    pair_ema_weights = defaultdict(float)
    double_scores = defaultdict(float)

    for idx, draw in enumerate(history_draws):
        delta_t = total_draws - 1 - idx
        time_factor = math.exp(-decay_lambda * delta_t)
        items = [(draw.get('1st_prize'), 4.5), (draw.get('2nd_prize'), 3.2), (draw.get('3rd_prize'), 2.2)]
        items += [(x, 0.9) for x in draw.get('special_prizes', [])]
        items += [(x, 0.4) for x in draw.get('consolation_prizes', [])]
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * time_factor
                cnt = Counter(num_str)
                for d_val, freq in cnt.items():
                    if freq >= 2:
                        double_scores[int(d_val)] += w * freq
                for p in range(4):
                    pos_ema_weights[p][int(num_str[p])] += w
                pair_ema_weights[(int(num_str[0]), int(num_str[1]))] += w
                pair_ema_weights[(int(num_str[2]), int(num_str[3]))] += w

    pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        tot_w = sum(pos_ema_weights[p].values()) or 1.0
        for d in range(10):
            prob = (pos_ema_weights[p][d] + 0.05) / (tot_w + 0.5)
            pos_probs[p][d] = max(prob, 1e-6)
            shannon_entropy -= prob * math.log(max(prob, 1e-6))

    tot_pair = sum(pair_ema_weights.values()) or 1.0
    tot_double = sum(double_scores.values()) or 1.0
    is_high_conf = shannon_entropy < 9.17
    return pos_probs, pair_ema_weights, tot_pair, double_scores, tot_double, shannon_entropy, is_high_conf

# ==========================================
# PENJANAAN 20 NOMBOR DENGAN DIVERSIFIKASI ORTOGONAL
# ==========================================
def generate_formula_37_recommendations(history_draws):
    if len(history_draws) < 10:
        return [], {}

    f18_probs, f18_pairs, f18_tot_p, f18_H = compute_formula_18_engine(history_draws)
    f20_probs, f20_pairs, f20_tot_p, f20_doubles, f20_tot_d, twin_ratio, is_twin_regime = compute_formula_20_engine(history_draws)
    f22_probs, f22_pairs, f22_tot_p, dominant_pwr, is_high_triplet = compute_formula_22_engine(history_draws)
    f36_probs, f36_pairs, f36_tot_p, f36_doubles, f36_tot_d, f36_H, is_ema_conf = compute_formula_36_engine(history_draws)

    w18 = 0.25 + (0.10 if f18_H < 8.20 else 0.0)
    w20 = 0.25 + (0.15 if is_twin_regime else 0.0)
    w22 = 0.25 + (0.15 if is_high_triplet else 0.0)
    w36 = 0.25 + (0.10 if is_ema_conf else 0.0)
    sum_w = w18 + w20 + w22 + w36
    w18 /= sum_w; w20 /= sum_w; w22 /= sum_w; w36 /= sum_w

    candidates_by_perm = {4: [], 6: [], 12: [], 24: []}

    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    if perms not in candidates_by_perm:
                        continue

                    p_front = (d0, d1)
                    p_back = (d2, d3)

                    pf18_f = f18_pairs.get(p_front, 0.2) / f18_tot_p
                    pf18_b = f18_pairs.get(p_back, 0.2) / f18_tot_p
                    s18 = (math.log(f18_probs[0][d0]) + math.log(f18_probs[1][d1]) +
                           math.log(f18_probs[2][d2]) + math.log(f18_probs[3][d3]) +
                           0.35 * math.log(pf18_f) + 0.35 * math.log(pf18_b))

                    pf20_f = f20_pairs.get(p_front, 0.5) / f20_tot_p
                    pf20_b = f20_pairs.get(p_back, 0.5) / f20_tot_p
                    d_boost_20 = sum(f20_doubles.get(d, 0.0) / f20_tot_d for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                    s20 = (math.log(f20_probs[0][d0]) + math.log(f20_probs[1][d1]) +
                           math.log(f20_probs[2][d2]) + math.log(f20_probs[3][d3]) +
                           0.30 * math.log(pf20_f) + 0.30 * math.log(pf20_b) +
                           0.40 * math.log(1.0 + d_boost_20))

                    pf22_f = f22_pairs.get(p_front, 0.5) / f22_tot_p
                    pf22_b = f22_pairs.get(p_back, 0.5) / f22_tot_p
                    s22 = (math.log(f22_probs[0][d0]) + math.log(f22_probs[1][d1]) +
                           math.log(f22_probs[2][d2]) + math.log(f22_probs[3][d3]) +
                           0.30 * math.log(pf22_f) + 0.30 * math.log(pf22_b) +
                           math.log(24.0 / perms) + 0.5 * math.log(1.0 + dominant_pwr))

                    pf36_f = (f36_pairs.get(p_front, 0.0) + 0.01) / (f36_tot_p + 1.0)
                    pf36_b = (f36_pairs.get(p_back, 0.0) + 0.01) / (f36_tot_p + 1.0)
                    d_boost_36 = sum(f36_doubles.get(d, 0.0) / f36_tot_d for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                    s36 = (math.log(f36_probs[0][d0]) + math.log(f36_probs[1][d1]) +
                           math.log(f36_probs[2][d2]) + math.log(f36_probs[3][d3]) +
                           0.35 * math.log(pf36_f) + 0.35 * math.log(pf36_b) +
                           0.30 * math.log(1.0 + d_boost_36))

                    ensemble_score = (w18 * s18) + (w20 * s20) + (w22 * s22) + (w36 * s36)
                    candidates_by_perm[perms].append((ensemble_score, num_str))

    for p in candidates_by_perm:
        candidates_by_perm[p].sort(key=lambda x: x[0], reverse=True)

    selected_numbers = []
    seen_canonical_boxes = set()

    # 1. Pilih 4 Nombor Permutasi 4 (Triplet AAAB) - WAJIB Digit Triplet Berbeza
    triplet_selected = []
    used_triplet_digits = set()
    for score, num in candidates_by_perm[4]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        cnt = Counter(num)
        triplet_digit = [d for d, c in cnt.items() if c == 3][0]
        if triplet_digit in used_triplet_digits:
            continue

        used_triplet_digits.add(triplet_digit)
        seen_canonical_boxes.add(c_box)
        triplet_selected.append({"number": num, "permutation": 4, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(triplet_selected) == 4:
            break

    # Fallback Triplet
    if len(triplet_selected) < 4:
        for score, num in candidates_by_perm[4]:
            c_box = get_canonical_box(num)
            if c_box not in seen_canonical_boxes:
                seen_canonical_boxes.add(c_box)
                triplet_selected.append({"number": num, "permutation": 4, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
            if len(triplet_selected) == 4:
                break
    selected_numbers.extend(triplet_selected)

    # 2. Pilih 7 Nombor Permutasi 6 (2-Pasang AABB) - Elak Pasangan Kembar Bertindih
    sixway_selected = []
    twin_digit_usage = Counter()
    for score, num in candidates_by_perm[6]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        cnt = Counter(num)
        pair_digits = tuple(sorted(cnt.keys()))
        if max(twin_digit_usage[d] for d in pair_digits) >= 3 and len(sixway_selected) < 6:
            continue

        for d in pair_digits:
            twin_digit_usage[d] += 1
        seen_canonical_boxes.add(c_box)
        sixway_selected.append({"number": num, "permutation": 6, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(sixway_selected) == 7:
            break

    if len(sixway_selected) < 7:
        for score, num in candidates_by_perm[6]:
            c_box = get_canonical_box(num)
            if c_box not in seen_canonical_boxes:
                seen_canonical_boxes.add(c_box)
                sixway_selected.append({"number": num, "permutation": 6, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
            if len(sixway_selected) == 7:
                break
    selected_numbers.extend(sixway_selected)

    # 3. Pilih 6 Nombor Permutasi 12 (1-Pasang AABC) - Diversiti Digit Seimbang
    twelveway_selected = []
    digit_12_usage = Counter()
    for score, num in candidates_by_perm[12]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        digits = [int(d) for d in num]
        if max(digit_12_usage[d] for d in set(digits)) >= 3 and len(twelveway_selected) < 5:
            continue

        for d in set(digits):
            digit_12_usage[d] += 1
        seen_canonical_boxes.add(c_box)
        twelveway_selected.append({"number": num, "permutation": 12, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(twelveway_selected) == 6:
            break

    if len(twelveway_selected) < 6:
        for score, num in candidates_by_perm[12]:
            c_box = get_canonical_box(num)
            if c_box not in seen_canonical_boxes:
                seen_canonical_boxes.add(c_box)
                twelveway_selected.append({"number": num, "permutation": 12, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
            if len(twelveway_selected) == 6:
                break
    selected_numbers.extend(twelveway_selected)

    # 4. Pilih 3 Nombor Permutasi 24 (Berbeza ABCD) - Liputan Seluruh Spektrum
    twentyfour_selected = []
    for score, num in candidates_by_perm[24]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        seen_canonical_boxes.add(c_box)
        twentyfour_selected.append({"number": num, "permutation": 24, "score": round(score, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(twentyfour_selected) == 3:
            break
    selected_numbers.extend(twentyfour_selected)

    for idx, item in enumerate(selected_numbers):
        item["rank"] = idx + 1

    meta_info = {
        "twin_ratio": round(twin_ratio, 3),
        "dominant_digit_power": round(dominant_pwr, 4),
        "entropy_f18": round(f18_H, 2),
        "entropy_f36": round(f36_H, 2),
        "regime_status": "TWIN-DOMINANT" if is_twin_regime else "EXPONENTIAL-BALANCED"
    }

    return selected_numbers, meta_info

def evaluate_draw_ibox(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]

    c_p1 = get_canonical_box(p1)
    c_p2 = get_canonical_box(p2)
    c_p3 = get_canonical_box(p3)
    c_specials = [get_canonical_box(x) for x in specials]
    c_consolations = [get_canonical_box(x) for x in consolations]

    total_winnings = 0.0
    hit_logs = []

    for item in recommendations:
        num = item['number']
        perm = item['permutation']
        rank = item['rank']
        c_num = get_canonical_box(num)

        if c_num == c_p1:
            win = IBOX_BIG_PAYOUT['1st'][perm]
            total_winnings += win
            hit_logs.append(f"🥇 Rank {rank:02d} [{num} ({perm}-Way)] KENA 1st Prize ({p1}) -> +RM {win:.2f}")
        if c_num == c_p2:
            win = IBOX_BIG_PAYOUT['2nd'][perm]
            total_winnings += win
            hit_logs.append(f"🥈 Rank {rank:02d} [{num} ({perm}-Way)] KENA 2nd Prize ({p2}) -> +RM {win:.2f}")
        if c_num == c_p3:
            win = IBOX_BIG_PAYOUT['3rd'][perm]
            total_winnings += win
            hit_logs.append(f"🥉 Rank {rank:02d} [{num} ({perm}-Way)] KENA 3rd Prize ({p3}) -> +RM {win:.2f}")
        for idx_sp, sp_box in enumerate(c_specials):
            if c_num == sp_box:
                win = IBOX_BIG_PAYOUT['special'][perm]
                total_winnings += win
                hit_logs.append(f"⭐ Rank {rank:02d} [{num} ({perm}-Way)] KENA Special ({specials[idx_sp]}) -> +RM {win:.2f}")
                break
        for idx_cs, cs_box in enumerate(c_consolations):
            if c_num == cs_box:
                win = IBOX_BIG_PAYOUT['consolation'][perm]
                total_winnings += win
                hit_logs.append(f"🎖️  Rank {rank:02d} [{num} ({perm}-Way)] KENA Consolation ({consolations[idx_cs]}) -> +RM {win:.2f}")
                break

    return total_winnings, hit_logs

# ==========================================
# ENJIN UTAMA (MAIN)
# ==========================================
def main():
    os.makedirs(TEMP_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data tidak dijumpai di: {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)

    draws = [d for d in draws if parse_date(d.get('date', '')) != datetime.min]
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)

    if total_records < 30:
        print("[AMARAN] Data tidak mencukupi.")
        return

    # Penetapan Tetingkap Tepat: 3 Bulan Terkini (~92 Hari) untuk Ujian
    latest_date = parse_date(draws[-1].get('date', ''))
    test_cutoff_date = latest_date - timedelta(days=92)

    split_index = None
    for idx, d in enumerate(draws):
        if parse_date(d.get('date', '')) >= test_cutoff_date:
            split_index = idx
            break

    if split_index is None or split_index < 20:
        split_index = int(total_records * 0.75)

    # Penetapan Tetingkap Latihan Tepat 9 Bulan (~275 Hari) Sebelum Fasa Ujian Bermula
    test_start_date = parse_date(draws[split_index].get('date', ''))
    train_cutoff_date = test_start_date - timedelta(days=275)

    # Tapis data latihan awal agar tidak melebihi 9 bulan burn-in
    train_start_index = 0
    for idx, d in enumerate(draws[:split_index]):
        if parse_date(d.get('date', '')) >= train_cutoff_date:
            train_start_index = idx
            break

    testing_draws = draws[split_index:]
    initial_training_draws = draws[train_start_index:split_index]

    start_train_str = initial_training_draws[0].get('date', 'N/A')
    end_train_str = initial_training_draws[-1].get('date', 'N/A')
    start_test_str = testing_draws[0].get('date', 'N/A')
    end_test_str = testing_draws[-1].get('date', 'N/A')

    if HAS_RICH:
        panel_text = Text()
        panel_text.append("🚀 FORMULA 37: ENSEMBLE MASTER (V2 - ORTHOGONAL DIVERSITY)\n", style="bold yellow")
        panel_text.append("Penalaan Gelongsor: Tepat 9 Bulan Latihan ➔ Diuji ke atas 3 Bulan Terkini\n", style="cyan")
        panel_text.append(f"📁 Konteks Latihan (9 Bulan)  : {len(initial_training_draws)} Sesi ({start_train_str} -> {end_train_str})\n", style="white")
        panel_text.append(f"🎯 Fasa Ujian Sebenar (3 Bulan): {len(testing_draws)} Cabutan ({start_test_str} -> {end_test_str})\n", style="white")
        panel_text.append("💰 Konfigurasi Modal Tetap    : RM 20.00 / Cabutan (20 Nombor iBox RM1.00)", style="bold green")
        console.print(Panel(panel_text, box=box.ROUNDED, border_style="bright_blue"))
    else:
        print("=" * 80)
        print(" FORMULA 37: ENSEMBLE MASTER (V2 - 9M TRAIN / 3M TEST)")
        print(f" Latihan 9 Bulan : {len(initial_training_draws)} sesi ({start_train_str} -> {end_train_str})")
        print(f" Ujian 3 Bulan   : {len(testing_draws)} sesi ({start_test_str} -> {end_test_str})")
        print("=" * 80)

    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    prize_counts = Counter()
    latest_payload = None

    # Walk-Forward Backtesting Menggunakan Tetingkap Gelongsor 9 Bulan
    for i, current_draw in enumerate(testing_draws):
        curr_test_date = parse_date(current_draw.get('date', ''))
        draw_no = current_draw.get('draw_no', 'N/A')
        target_date = current_draw.get('date', 'N/A')

        # Hadkan konteks sejarah hanya 9 bulan sebelum cabutan semasa (Rolling Window)
        window_start_date = curr_test_date - timedelta(days=275)
        rolling_context = [d for d in draws[:split_index + i] if parse_date(d.get('date', '')) >= window_start_date]

        recs, meta = generate_formula_37_recommendations(rolling_context)

        cost_this_draw = sum(item['bet_amount_rm'] for item in recs)
        winnings, hit_logs = evaluate_draw_ibox(recs, current_draw)

        total_invested += cost_this_draw
        total_won += winnings
        net_draw = winnings - cost_this_draw

        if winnings > 0:
            hits_count += 1
            for l in hit_logs:
                if "1st Prize" in l: prize_counts['1st'] += 1
                elif "2nd Prize" in l: prize_counts['2nd'] += 1
                elif "3rd Prize" in l: prize_counts['3rd'] += 1
                elif "Special" in l: prize_counts['special'] += 1
                elif "Consolation" in l: prize_counts['consolation'] += 1

        latest_payload = {
            "formula_id": "37_ensemble_multi_regime_ibox",
            "formula_name": "Multi-Regime Ensemble & Asymmetric iBox Master V2",
            "target_date": target_date,
            "draw_no": draw_no,
            "meta_signals": meta,
            "budget_rm": cost_this_draw,
            "quota_breakdown": {"perm_4": 4, "perm_6": 7, "perm_12": 6, "perm_24": 3},
            "recommendations": recs
        }

        prefix = f"[{i+1:02d}/{len(testing_draws)}] {target_date} (#{draw_no})"
        if winnings > 0:
            status_str = f"🎉 MENANG RM {winnings:7.2f} (Untung: +RM {net_draw:6.2f})"
            if HAS_RICH:
                console.print(f"[bold green]{prefix} | {meta['regime_status'][:12]} | {status_str}[/bold green]")
                for h in hit_logs:
                    console.print(f"     └─ {h}", style="yellow")
            else:
                print(f"{prefix} | {meta['regime_status'][:12]} | {status_str}")
                for h in hit_logs:
                    print(f"     └─ {h}")
        else:
            status_str = f"❌ Kalah  -RM {cost_this_draw:5.2f}"
            if HAS_RICH:
                console.print(f"[dim]{prefix} | {meta['regime_status'][:12]} | {status_str}[/dim]")
            else:
                print(f"{prefix} | {meta['regime_status'][:12]} | {status_str}")

    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_payload, f, indent=4)

    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0

    if HAS_RICH:
        summary_table = Table(title="📊 RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 37 V2)", box=box.HEAVY_EDGE, header_style="bold magenta")
        summary_table.add_column("Metrik Prestasi", style="bold cyan")
        summary_table.add_column("Nilai Sebenar", justify="right", style="bold white")

        summary_table.add_row("🗓️ Jumlah Cabutan Diuji", f"{len(testing_draws)} sesi")
        summary_table.add_row("🎯 Cabutan Mengena (Hit Rate)", f"{hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        summary_table.add_row("💵 Jumlah Modal Dilabur", f"RM {total_invested:,.2f}")
        summary_table.add_row("🏆 Jumlah Pulangan Hadiah", f"RM {total_won:,.2f}")
        
        profit_color = "bold green" if net_profit >= 0 else "bold red"
        summary_table.add_row("📈 Untung / Rugi Bersih", f"[{profit_color}]RM {net_profit:+,.2f}[/{profit_color}]")
        summary_table.add_row("🚀 Pulangan Pelaburan (ROI)", f"[{profit_color}]{roi_percent:+,.2f}%[/{profit_color}]")

        breakdown_text = (
            f"1st: {prize_counts['1st']} | 2nd: {prize_counts['2nd']} | 3rd: {prize_counts['3rd']} | "
            f"Special: {prize_counts['special']} | Consolation: {prize_counts['consolation']}"
        )
        summary_table.add_row("🎁 Pecahan Kenaan Hadiah", breakdown_text)
        console.print("\n")
        console.print(summary_table)

        if latest_payload and latest_payload.get("recommendations"):
            rec_table = Table(title=f"🔮 CADANGAN 20 NOMBOR AKHIR (Cabutan Seterusnya: {latest_payload['target_date']})", box=box.ROUNDED)
            rec_table.add_column("Rank", justify="center", style="bold yellow")
            rec_table.add_column("Nombor 4D", justify="center", style="bold bright_white")
            rec_table.add_column("Permutasi", justify="center", style="cyan")
            rec_table.add_column("Kategori Corak", style="magenta")
            rec_table.add_column("Pertaruhan", justify="center", style="green")
            rec_table.add_column("Skor", justify="right", style="dim")

            cat_map = {4: "4-Way (Triplet AAAB)", 6: "6-Way (2 Pasang AABB)", 12: "12-Way (1 Pasang AABC)", 24: "24-Way (Berbeza ABCD)"}

            for item in latest_payload["recommendations"]:
                rec_table.add_row(
                    f"{item['rank']:02d}",
                    item['number'],
                    f"{item['permutation']}-way",
                    cat_map.get(item['permutation'], "-"),
                    f"iBox RM {item['bet_amount_rm']:.2f}",
                    f"{item['score']:.4f}"
                )
            console.print(rec_table)
            console.print(f"[bold green]💾 Rekod cadangan disimpan ke:[/bold green] [underline]{TEMP_OUTPUT_FILE}[/underline]\n")
    else:
        print("\n" + "=" * 80)
        print(" RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 37 V2)")
        print("=" * 80)
        print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)} sesi")
        print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        print(f"  Jumlah Modal Dilabur    : RM {total_invested:.2f}")
        print(f"  Jumlah Hadiah Menang    : RM {total_won:.2f}")
        print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
        print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
        print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
        print("=" * 80)

if __name__ == "__main__":
    main()
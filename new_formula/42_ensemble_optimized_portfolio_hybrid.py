#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 42_ensemble_optimized_portfolio_hybrid.py
FORMULA NAME : Formula 42 - Ensemble Optimized Portfolio (F18 Tuned + Twin Overweight)
DESCRIPTION  : Penambahbaikan berasaskan analisis empirikal F39, F40, dan F41:
               1. Enjin F18: Ditala tepat pada kitaran emas 12 cabutan (1 Bulan) vs
                  42 cabutan (3 Bulan) bagi mengimbangi momentum dan kestabilan.
               2. Sub-Enjin F20, F22, F36 dikekalkan sepenuhnya bagi menyaring rejim.
               3. Pengoptimuman Portfolio Asimetrik (Tepat 25 Nombor - RM 25.00):
                  - 4 Direct RM 1 (1x AAAB, 1x AABB, 1x AABC, 1x ABCD)
                  - 21 iBox RM 1:
                    * 4x 4-Way Triplet (Dipangkas dari 7 ke 4 untuk elak pembaziran modal)
                    * 13x 6-Way Dwi-Kembar (Ditambah dari 10 ke 13 - enjin pulangan tertinggi)
                    * 2x 12-Way 1-Pasang (Perisai varians)
                    * 2x 24-Way Berbeza Penuh (Perisai varians)

PENILAIAN & OUTPUT:
  - Walk-Forward Backtesting Gelongsor 3 Bulan Terkini (42 Sesi Cabutan).
  - Penjejakan Prestasi Mengikut Hari Cabutan (Rabu, Sabtu, Ahad, Selasa).
  - Bedah Siasat Prestasi Penuh 25 Rank Nombor.
  - Suntikan rekod prestasi 3 bulan (perf_3m) & tier bajet RM10/RM15 ke dalam JSON.
  - Fail JSON disimpan ke /home/braderdin/toto4d-data-scraper/temp/
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
# KONFIGURASI DIREKTORI & LALUAN FAIL
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_42_ensemble_hybrid_direct_ibox.json")

# ==========================================
# JADUAL PEMBAYARAN RASMI TOTO 4D (BIG RM 1.00)
# ==========================================
DIRECT_BIG_PAYOUT = {
    '1st': 2500.0,
    '2nd': 1000.0,
    '3rd': 500.0,
    'special': 180.0,
    'consolation': 60.0
}

IBOX_BIG_PAYOUT = {
    '1st': {24: 105.0, 12: 209.0, 6: 417.0, 4: 625.0},
    '2nd': {24: 42.0,  12: 84.0,  6: 167.0, 4: 250.0},
    '3rd': {24: 21.0,  12: 42.0,  6: 84.0,  4: 125.0},
    'special': {24: 8.0, 12: 15.0, 6: 30.0, 4: 45.0},
    'consolation': {24: 3.0, 12: 5.0, 6: 10.0, 4: 15.0}
}

MALAY_DAYS = {
    0: "Isnin",
    1: "Selasa",
    2: "Rabu",
    3: "Khamis",
    4: "Jumaat",
    5: "Sabtu",
    6: "Ahad"
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

# ==============================================================================
# ENJIN MATEMATIK FORMULA 18 (DITALA: 12 SHORT VS 42 LONG)
# ==============================================================================
def compute_formula_18_engine(history_draws):
    """
    F18 OPTIMIZED:
    - Long Window  : Tepat 42 cabutan (~3 Bulan) sebagai penstabil taburan Dirichlet
    - Short Window : Tepat 12 cabutan (~1 Bulan) sebagai pengesan momentum pantas
    """
    total_draws = len(history_draws)
    f18_context = history_draws[-42:] if total_draws >= 42 else history_draws
    ctx_len = len(f18_context)

    short_len = min(12, ctx_len)
    short_history = f18_context[-short_len:]
    long_history = f18_context

    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(4)]
    for draw in long_history:
        items = [
            (draw.get('1st_prize'), 4.5),
            (draw.get('2nd_prize'), 3.2),
            (draw.get('3rd_prize'), 2.2)
        ]
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
        rec_boost = 1.0 + (idx / max(len(short_history), 1)) * 1.2
        items = [
            (draw.get('1st_prize'), 5.0),
            (draw.get('2nd_prize'), 3.5),
            (draw.get('3rd_prize'), 2.5)
        ]
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

# ==============================================================================
# ENJIN F20, F22, F36 (DIKEKALKAN SEPENUHNYA)
# ==============================================================================
def compute_formula_20_engine(history_draws):
    """F20: Dynamic Regime-Switching Gate"""
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

# ==============================================================================
# PENJANAAN 25 NOMBOR HIBRID OPTIMUM FORMULA 42
# ==============================================================================
def generate_formula_42_recommendations(history_draws):
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

    # -------------------------------------------------------------
    # A. PILIH 4 NOMBOR DIRECT (TOP 1 DARI SETIAP CORAK)
    # -------------------------------------------------------------
    direct_selected = []
    cat_titles = {
        4: "4-Way (Triplet AAAB)",
        6: "6-Way (Dwi-Kembar AABB)",
        12: "12-Way (1-Pasang AABC)",
        24: "24-Way (Berbeza Penuh ABCD)"
    }

    for perm in (4, 6, 12, 24):
        if candidates_by_perm[perm]:
            top_score, top_num = candidates_by_perm[perm][0]
            direct_selected.append({
                "number": top_num,
                "permutation": perm,
                "score": round(top_score, 4),
                "bet_type": "Direct",
                "category": cat_titles[perm],
                "bet_amount_rm": 1.0
            })

    # -------------------------------------------------------------
    # B. PILIH 21 NOMBOR IBOX DENGAN PENYUSUNAN SEMULA KUOTA OPTIMUM
    # -------------------------------------------------------------
    seen_canonical_ibox = set()
    ibox_selected = []

    # 1. 4x 4-Way Triplet (Dipangkas dari 7 ke 4 bagi menjimatkan pembaziran modal)
    triplet_ibox = []
    used_triplet_digits = set()
    for score, num in candidates_by_perm[4]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_ibox:
            continue
        cnt = Counter(num)
        triplet_digit = [d for d, c in cnt.items() if c == 3][0]
        if triplet_digit in used_triplet_digits and len(triplet_ibox) < 4:
            continue

        used_triplet_digits.add(triplet_digit)
        seen_canonical_ibox.add(c_box)
        triplet_ibox.append({
            "number": num, "permutation": 4, "score": round(score, 4),
            "bet_type": "iBox", "category": cat_titles[4], "bet_amount_rm": 1.0
        })
        if len(triplet_ibox) == 4:
            break

    if len(triplet_ibox) < 4:
        for score, num in candidates_by_perm[4]:
            c_box = get_canonical_box(num)
            if c_box not in seen_canonical_ibox:
                seen_canonical_ibox.add(c_box)
                triplet_ibox.append({
                    "number": num, "permutation": 4, "score": round(score, 4),
                    "bet_type": "iBox", "category": cat_titles[4], "bet_amount_rm": 1.0
                })
            if len(triplet_ibox) == 4:
                break
    ibox_selected.extend(triplet_ibox)

    # 2. 13x 6-Way Dwi-Kembar (Ditingkatkan dari 10 ke 13 nombor - Enjin Pulangan Utama)
    twin_ibox = []
    twin_digit_usage = Counter()
    for score, num in candidates_by_perm[6]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_ibox:
            continue
        cnt = Counter(num)
        pair_digits = tuple(sorted(cnt.keys()))
        if max(twin_digit_usage[d] for d in pair_digits) >= 4 and len(twin_ibox) < 10:
            continue

        for d in pair_digits:
            twin_digit_usage[d] += 1
        seen_canonical_ibox.add(c_box)
        twin_ibox.append({
            "number": num, "permutation": 6, "score": round(score, 4),
            "bet_type": "iBox", "category": cat_titles[6], "bet_amount_rm": 1.0
        })
        if len(twin_ibox) == 13:
            break

    if len(twin_ibox) < 13:
        for score, num in candidates_by_perm[6]:
            c_box = get_canonical_box(num)
            if c_box not in seen_canonical_ibox:
                seen_canonical_ibox.add(c_box)
                twin_ibox.append({
                    "number": num, "permutation": 6, "score": round(score, 4),
                    "bet_type": "iBox", "category": cat_titles[6], "bet_amount_rm": 1.0
                })
            if len(twin_ibox) == 13:
                break
    ibox_selected.extend(twin_ibox)

    # 3. 2x 12-Way 1-Pasang (AABC)
    twelve_ibox = []
    for score, num in candidates_by_perm[12]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_ibox:
            continue
        seen_canonical_ibox.add(c_box)
        twelve_ibox.append({
            "number": num, "permutation": 12, "score": round(score, 4),
            "bet_type": "iBox", "category": cat_titles[12], "bet_amount_rm": 1.0
        })
        if len(twelve_ibox) == 2:
            break
    ibox_selected.extend(twelve_ibox)

    # 4. 2x 24-Way Berbeza Penuh (ABCD)
    twentyfour_ibox = []
    for score, num in candidates_by_perm[24]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_ibox:
            continue
        seen_canonical_ibox.add(c_box)
        twentyfour_ibox.append({
            "number": num, "permutation": 24, "score": round(score, 4),
            "bet_type": "iBox", "category": cat_titles[24], "bet_amount_rm": 1.0
        })
        if len(twentyfour_ibox) == 2:
            break
    ibox_selected.extend(twentyfour_ibox)

    total_recommendations = direct_selected + ibox_selected
    for idx, item in enumerate(total_recommendations):
        item["rank"] = idx + 1

    meta_info = {
        "twin_ratio": round(twin_ratio, 3),
        "dominant_digit_power": round(dominant_pwr, 4),
        "entropy_f18": round(f18_H, 2),
        "entropy_f36": round(f36_H, 2),
        "regime_status": "TWIN-DOMINANT" if is_twin_regime else "EXPONENTIAL-BALANCED"
    }

    return total_recommendations, meta_info

# ==============================================================================
# PENILAIAN CABUTAN (DIRECT & IBOX BIG + PENJEJAKAN RANK)
# ==============================================================================
def evaluate_draw_hybrid(recommendations, actual_draw):
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
    rank_payouts = defaultdict(float)
    hit_logs = []

    for item in recommendations:
        num = item['number']
        perm = item['permutation']
        rank = item['rank']
        b_type = item['bet_type']

        if b_type == 'Direct':
            if num == p1:
                win = DIRECT_BIG_PAYOUT['1st']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT JACKPOT] Rank {rank:02d} [{num}] TEPAT 1st Prize ({p1}) -> +RM {win:,.2f}")
            elif num == p2:
                win = DIRECT_BIG_PAYOUT['2nd']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT] Rank {rank:02d} [{num}] TEPAT 2nd Prize ({p2}) -> +RM {win:,.2f}")
            elif num == p3:
                win = DIRECT_BIG_PAYOUT['3rd']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT] Rank {rank:02d} [{num}] TEPAT 3rd Prize ({p3}) -> +RM {win:,.2f}")
            elif num in specials:
                win = DIRECT_BIG_PAYOUT['special']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"⭐ [DIRECT] Rank {rank:02d} [{num}] TEPAT Special ({num}) -> +RM {win:,.2f}")
            elif num in consolations:
                win = DIRECT_BIG_PAYOUT['consolation']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🎖️  [DIRECT] Rank {rank:02d} [{num}] TEPAT Consolation ({num}) -> +RM {win:,.2f}")

        elif b_type == 'iBox':
            c_num = get_canonical_box(num)
            if c_num == c_p1:
                win = IBOX_BIG_PAYOUT['1st'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥇 [iBox {perm}-Way] Rank {rank:02d} [{num}] KENA 1st Prize ({p1}) -> +RM {win:.2f}")
            if c_num == c_p2:
                win = IBOX_BIG_PAYOUT['2nd'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥈 [iBox {perm}-Way] Rank {rank:02d} [{num}] KENA 2nd Prize ({p2}) -> +RM {win:.2f}")
            if c_num == c_p3:
                win = IBOX_BIG_PAYOUT['3rd'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥉 [iBox {perm}-Way] Rank {rank:02d} [{num}] KENA 3rd Prize ({p3}) -> +RM {win:.2f}")
            for idx_sp, sp_box in enumerate(c_specials):
                if c_num == sp_box:
                    win = IBOX_BIG_PAYOUT['special'][perm]
                    total_winnings += win
                    rank_payouts[rank] += win
                    hit_logs.append(f"⭐ [iBox {perm}-Way] Rank {rank:02d} [{num}] KENA Special ({specials[idx_sp]}) -> +RM {win:.2f}")
                    break
            for idx_cs, cs_box in enumerate(c_consolations):
                if c_num == cs_box:
                    win = IBOX_BIG_PAYOUT['consolation'][perm]
                    total_winnings += win
                    rank_payouts[rank] += win
                    hit_logs.append(f"🎖️  [iBox {perm}-Way] Rank {rank:02d} [{num}] KENA Consolation ({consolations[idx_cs]}) -> +RM {win:.2f}")
                    break

    return total_winnings, rank_payouts, hit_logs

# ==============================================================================
# ENJIN UTAMA & SIMULASI GELONGSOR
# ==============================================================================
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
        print("[AMARAN] Data cabutan tidak mencukupi.")
        return

    latest_date = parse_date(draws[-1].get('date', ''))
    test_cutoff_date = latest_date - timedelta(days=92)

    split_index = None
    for idx, d in enumerate(draws):
        if parse_date(d.get('date', '')) >= test_cutoff_date:
            split_index = idx
            break

    if split_index is None or split_index < 20:
        split_index = int(total_records * 0.75)

    test_start_date = parse_date(draws[split_index].get('date', ''))
    train_cutoff_date = test_start_date - timedelta(days=275)

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
        panel_text.append("🚀 FORMULA 42: ENSEMBLE OPTIMIZED HYBRID MASTER (TWIN OVERWEIGHT)\n", style="bold yellow")
        panel_text.append("Simulasi Gelongsor: Tepat 9 Bulan Konteks ➔ Diuji ke atas 3 Bulan Terkini\n", style="cyan")
        panel_text.append(f"📁 Konteks Analisis (9 Bulan) : {len(initial_training_draws)} Sesi ({start_train_str} -> {end_train_str})\n", style="white")
        panel_text.append(f"🎯 Fasa Ujian Sebenar (3 Bulan): {len(testing_draws)} Cabutan ({start_test_str} -> {end_test_str})\n", style="white")
        panel_text.append("⚡ Sub-Enjin F18 Terkalibrasi  : Tetingkap Emas 12 Short vs 42 Long\n", style="bright_cyan")
        panel_text.append("💰 Konfigurasi Pertaruhan     : 25 Nombor (RM 25.00 / Sesi)\n", style="bold green")
        panel_text.append("   ├─ Direct RM 1.00 : 4 Nombor (Top 1 AAAB, Top 1 AABB, Top 1 AABC, Top 1 ABCD)\n", style="bold magenta")
        panel_text.append("   └─ iBox RM 1.00   : 21 Nombor (4x 4-Way, 13x 6-Way, 2x 12-Way, 2x 24-Way)", style="green")
        console.print(Panel(panel_text, box=box.ROUNDED, border_style="bright_blue"))
    else:
        print("=" * 80)
        print(" FORMULA 42: ENSEMBLE OPTIMIZED HYBRID MASTER (TWIN OVERWEIGHT)")
        print(f" Konteks Latihan : {len(initial_training_draws)} sesi ({start_train_str} -> {end_train_str})")
        print(f" Ujian 3 Bulan   : {len(testing_draws)} sesi ({start_test_str} -> {end_test_str})")
        print(" Modal : RM 25.00 / Cabutan (4 Direct + 21 iBox: 4x 4W, 13x 6W, 2x 12W, 2x 24W)")
        print("=" * 80)

    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    direct_hits_count = 0
    prize_counts = Counter()
    latest_payload = None

    day_performance = defaultdict(lambda: {"sessions": 0, "hits": 0, "invested": 0.0, "won": 0.0})
    rank_profit_loss = defaultdict(lambda: {
        "cost": 0.0,
        "won": 0.0,
        "hits": 0,
        "bet_type": "",
        "category": "",
        "perm": 0
    })

    # Walk-Forward Backtesting
    for i, current_draw in enumerate(testing_draws):
        curr_test_date = parse_date(current_draw.get('date', ''))
        draw_no = current_draw.get('draw_no', 'N/A')
        target_date = current_draw.get('date', 'N/A')
        day_name = MALAY_DAYS.get(curr_test_date.weekday(), "N/A")

        window_start_date = curr_test_date - timedelta(days=275)
        rolling_context = [d for d in draws[:split_index + i] if parse_date(d.get('date', '')) >= window_start_date]

        recs, meta = generate_formula_42_recommendations(rolling_context)

        cost_this_draw = sum(item['bet_amount_rm'] for item in recs)
        winnings, rank_payouts, hit_logs = evaluate_draw_hybrid(recs, current_draw)

        total_invested += cost_this_draw
        total_won += winnings
        net_draw = winnings - cost_this_draw

        day_performance[day_name]["sessions"] += 1
        day_performance[day_name]["invested"] += cost_this_draw
        day_performance[day_name]["won"] += winnings

        for r_item in recs:
            r_no = r_item['rank']
            rank_profit_loss[r_no]["cost"] += r_item['bet_amount_rm']
            payout = rank_payouts.get(r_no, 0.0)
            rank_profit_loss[r_no]["won"] += payout
            if payout > 0:
                rank_profit_loss[r_no]["hits"] += 1
            rank_profit_loss[r_no]["bet_type"] = r_item['bet_type']
            rank_profit_loss[r_no]["category"] = r_item['category']
            rank_profit_loss[r_no]["perm"] = r_item['permutation']

        had_direct_hit = False
        if winnings > 0:
            hits_count += 1
            day_performance[day_name]["hits"] += 1
            for l in hit_logs:
                if "[DIRECT" in l:
                    had_direct_hit = True
                    direct_hits_count += 1
                if "1st Prize" in l: prize_counts['1st'] += 1
                elif "2nd Prize" in l: prize_counts['2nd'] += 1
                elif "3rd Prize" in l: prize_counts['3rd'] += 1
                elif "Special" in l: prize_counts['special'] += 1
                elif "Consolation" in l: prize_counts['consolation'] += 1

        latest_payload = {
            "formula_id": "42_ensemble_optimized_portfolio_hybrid",
            "formula_name": "Formula 42 - Ensemble Optimized Portfolio (F18 Tuned + Twin Overweight)",
            "target_date": target_date,
            "draw_no": draw_no,
            "meta_signals": meta,
            "budget_rm": cost_this_draw,
            "quota_breakdown": {
                "direct_rm1": {"perm_4": 1, "perm_6": 1, "perm_12": 1, "perm_24": 1, "subtotal_rm": 4.0},
                "ibox_rm1": {"perm_4": 4, "perm_6": 13, "perm_12": 2, "perm_24": 2, "subtotal_rm": 21.0},
                "total_numbers": 25,
                "total_cost_rm": 25.0
            },
            "recommendations": recs
        }

        prefix = f"[{i+1:02d}/{len(testing_draws)}] {target_date} ({day_name:<6}) (#{draw_no})"
        if winnings > 0:
            direct_flag = " 🎯 [DIRECT STRIKE!]" if had_direct_hit else ""
            status_str = f"🎉 MENANG RM {winnings:7.2f} (Untung: +RM {net_draw:7.2f}){direct_flag}"
            if HAS_RICH:
                line_color = "bold bright_green" if had_direct_hit else "bold green"
                console.print(f"[{line_color}]{prefix} | {meta['regime_status'][:12]} | {status_str}[/{line_color}]")
                for h in hit_logs:
                    c_style = "bold bright_yellow" if "DIRECT" in h else "yellow"
                    console.print(f"     └─ {h}", style=c_style)
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

    # ==============================================================================
    # SUNTIK REKOD PRESTASI 3 BULAN & TIER BAJET KE DALAM PAYLOAD JSON
    # ==============================================================================
    if latest_payload and latest_payload.get("recommendations"):
        # Susun rank mengikut keuntungan bersih dan kekerapan mengena (3 bulan)
        rank_scoring = []
        for r_item in latest_payload["recommendations"]:
            r_no = r_item["rank"]
            r_stats = rank_profit_loss[r_no]
            diff = r_stats["won"] - r_stats["cost"]
            roi_val = (diff / r_stats["cost"] * 100) if r_stats["cost"] > 0 else 0.0

            # Masukkan data prestasi 3 bulan ke dalam setiap item nombor
            r_item["perf_3m"] = {
                "hits": r_stats["hits"],
                "cost_rm": r_stats["cost"],
                "won_rm": r_stats["won"],
                "pnl_rm": round(diff, 2),
                "roi_pct": round(roi_val, 1)
            }
            rank_scoring.append((r_no, diff, r_stats["hits"]))

        # Susun dari paling untung & kerap kena
        rank_scoring.sort(key=lambda x: (x[1], x[2]), reverse=True)
        top_10_ranks = [x[0] for x in rank_scoring[:10]]
        top_15_ranks = [x[0] for x in rank_scoring[:15]]

        latest_payload["budget_picks"] = {
            "tier_rm10_ranks": top_10_ranks,
            "tier_rm15_ranks": top_15_ranks
        }

    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_payload, f, indent=4)

    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0

    # ==============================================================================
    # JADUAL RINGKASAN PRESTASI
    # ==============================================================================
    if HAS_RICH:
        summary_table = Table(title="📊 RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 42)", box=box.HEAVY_EDGE, header_style="bold magenta")
        summary_table.add_column("Metrik Prestasi", style="bold cyan")
        summary_table.add_column("Nilai Sebenar", justify="right", style="bold white")

        summary_table.add_row("🗓️ Jumlah Cabutan Diuji", f"{len(testing_draws)} sesi")
        summary_table.add_row("🎯 Cabutan Mengena (Hit Rate)", f"{hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        summary_table.add_row("🎯 Kenaan Hadiah Direct Tepat", f"{direct_hits_count} kali")
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

        # ==============================================================================
        # JADUAL ANALISIS HARI CABUTAN
        # ==============================================================================
        day_table = Table(title="📅 ANALISIS PRESTASI MENGIKUT HARI CABUTAN (3 Bulan Terkini)", box=box.ROUNDED)
        day_table.add_column("Hari Cabutan", style="bold yellow")
        day_table.add_column("Kekerapan Sesi", justify="center")
        day_table.add_column("Kenaan (Hits)", justify="center", style="green")
        day_table.add_column("Kadar Kenaan", justify="right")
        day_table.add_column("Modal Dilabur", justify="right")
        day_table.add_column("Pulangan Hadiah", justify="right", style="bright_yellow")
        day_table.add_column("Untung / Rugi", justify="right")
        day_table.add_column("ROI Hari", justify="right")

        for d_name in ["Rabu", "Sabtu", "Ahad", "Selasa"]:
            d_data = day_performance.get(d_name, None)
            if d_data and d_data['sessions'] > 0:
                d_net = d_data['won'] - d_data['invested']
                d_roi = (d_net / d_data['invested'] * 100) if d_data['invested'] > 0 else 0.0
                d_rate = (d_data['hits'] / d_data['sessions'] * 100)
                d_color = "bold green" if d_net >= 0 else "bold red"

                day_table.add_row(
                    d_name,
                    f"{d_data['sessions']} sesi",
                    f"{d_data['hits']} kali",
                    f"{d_rate:.1f}%",
                    f"RM {d_data['invested']:,.2f}",
                    f"RM {d_data['won']:,.2f}",
                    f"[{d_color}]RM {d_net:+,.2f}[/{d_color}]",
                    f"[{d_color}]{d_roi:+,.1f}%[/{d_color}]"
                )
        console.print("\n")
        console.print(day_table)

        # ==============================================================================
        # JADUAL BEDAH SIASAT LENGKAP 25 RANK NOMBOR (RANK 01 - 25)
        # ==============================================================================
        rank_data_list = []
        for r_no in range(1, 26):
            r_info = rank_profit_loss[r_no]
            c = r_info['cost']
            w = r_info['won']
            h = r_info['hits']
            diff = w - c
            roi_r = (diff / c * 100) if c > 0 else 0.0
            hit_pct = (h / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
            rank_data_list.append({
                "rank": r_no,
                "bet_type": r_info.get("bet_type", "N/A"),
                "category": r_info.get("category", "N/A"),
                "perm": r_info.get("perm", 0),
                "cost": c,
                "won": w,
                "diff": diff,
                "roi": roi_r,
                "hits": h,
                "hit_pct": hit_pct
            })

        max_hits = max(x["hits"] for x in rank_data_list)
        max_profit = max(x["diff"] for x in rank_data_list)
        min_profit = min(x["diff"] for x in rank_data_list)

        rank_table = Table(
            title=f"🎯 BEDAH SIASAT LENGKAP 25 RANK NOMBOR ({len(testing_draws)} Sesi Ujian)",
            box=box.HEAVY_EDGE,
            header_style="bold magenta"
        )
        rank_table.add_column("Rank", justify="center", style="bold yellow")
        rank_table.add_column("Jenis Bet & Kategori Corak", style="white")
        rank_table.add_column("Kekerapan Mengena (Hits)", justify="center")
        rank_table.add_column("Modal Dilabur", justify="right", style="dim")
        rank_table.add_column("Pulangan Hadiah", justify="right", style="bright_yellow")
        rank_table.add_column("Untung Bersih (PnL)", justify="right")
        rank_table.add_column("ROI (%)", justify="right")
        rank_table.add_column("Status & Catatan", style="bold")

        for item in rank_data_list:
            r_no = item["rank"]
            b_type = item["bet_type"]
            cat = item["category"]
            perm = item["perm"]
            diff = item["diff"]
            roi_val = item["roi"]
            hits = item["hits"]
            hit_pct = item["hit_pct"]

            b_color = "bright_cyan" if b_type == "Direct" else "green"
            bet_desc = f"[{b_color}]{b_type}[/{b_color}] {cat} ({perm}W)"

            badges = []
            if diff == max_profit and diff > 0:
                badges.append("[bold bright_yellow]👑 RAJA PROFIT[/bold bright_yellow]")
            elif diff > 0:
                badges.append("[bold green]🚀 UNTUNG[/bold green]")
            elif diff == 0:
                badges.append("[yellow]⚖️ PULANG MODAL[/yellow]")
            elif diff == min_profit:
                badges.append("[bold red]🔻 PALING RUGI[/bold red]")
            else:
                badges.append("[red]❌ RUGI MODAL[/red]")

            if hits == max_hits and max_hits > 0:
                badges.append("[bold bright_magenta]🎯 TOP HIT[/bold bright_magenta]")

            badge_str = " ".join(badges)
            pnl_color = "bold bright_green" if diff > 0 else ("yellow" if diff == 0 else "bold red")
            hit_color = "bold bright_cyan" if hits >= 3 else ("bright_white" if hits > 0 else "dim")

            rank_table.add_row(
                f"Rank {r_no:02d}",
                bet_desc,
                f"[{hit_color}]{hits}x ({hit_pct:.1f}%)[/{hit_color}]",
                f"RM {item['cost']:.2f}",
                f"RM {item['won']:,.2f}",
                f"[{pnl_color}]RM {diff:+,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{roi_val:+,.1f}%[/{pnl_color}]",
                badge_str
            )

            # Pemisah seksyen portfolio
            if r_no in (4, 8, 21, 23):
                rank_table.add_section()

        console.print("\n")
        console.print(rank_table)

        # ==============================================================================
        # JADUAL 25 NOMBOR CADANGAN AKHIR
        # ==============================================================================
        if latest_payload and latest_payload.get("recommendations"):
            rec_table = Table(title=f"🔮 CADANGAN 25 NOMBOR AKHIR (Cabutan Seterusnya: {latest_payload['target_date']})", box=box.ROUNDED)
            rec_table.add_column("Rank", justify="center", style="bold yellow")
            rec_table.add_column("Nombor 4D", justify="center", style="bold bright_white")
            rec_table.add_column("Jenis Bet", justify="center", style="bold green")
            rec_table.add_column("Kategori Corak", style="magenta")
            rec_table.add_column("Harga", justify="center", style="cyan")
            rec_table.add_column("Skor Ensembel", justify="right", style="dim")

            for item in latest_payload["recommendations"]:
                b_color = "bold bright_yellow" if item['bet_type'] == "Direct" else "green"
                rec_table.add_row(
                    f"{item['rank']:02d}",
                    item['number'],
                    f"[{b_color}]{item['bet_type']}[/{b_color}]",
                    f"{item['category']} ({item['permutation']}-Way)",
                    f"RM {item['bet_amount_rm']:.2f}",
                    f"{item['score']:.4f}"
                )
            console.print("\n")
            console.print(rec_table)
            console.print(f"[bold green]💾 Rekod cadangan disimpan ke:[/bold green] [underline]{TEMP_OUTPUT_FILE}[/underline]\n")
    else:
        print("\n" + "=" * 80)
        print(" RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 42)")
        print("=" * 80)
        print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)} sesi")
        print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        print(f"  Kenaan Hadiah Direct    : {direct_hits_count} kali")
        print(f"  Jumlah Modal Dilabur    : RM {total_invested:.2f}")
        print(f"  Jumlah Hadiah Menang    : RM {total_won:.2f}")
        print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
        print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
        print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
        print("=" * 80)

if __name__ == "__main__":
    main()
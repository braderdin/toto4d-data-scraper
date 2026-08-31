#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & PREDICTION PIPELINE
MODULE       : 36_tuned_dynamic_ema_gate.py
FORMULA NAME : Tuned Dynamic Exponential Decay Gate (EMA + Balanced Entropy)
DESCRIPTION  : Penalaan lanjutan berasaskan susutan masa eksponen EMA (lambda=0.08)
               dengan penapis Entropi Shannon seimbang (ambang 9.17):
               - Mod Keyakinan Tinggi (Entropi Rendah) : RM 18.00 (12 Nombor)
               - Mod Defensif Seimbang (Entropi Tinggi) : RM 10.00 (7 Nombor)
OUTPUT PATH  : live_engine/temp/36_tuned_dynamic_ema_gate.json
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import json
import math
from datetime import datetime
from collections import defaultdict, Counter

# ==========================================
# KONFIGURASI DIREKTORI & LALUAN FAIL
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "live_engine", "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "36_tuned_dynamic_ema_gate.json")

# ==========================================
# STRUKTUR PEMBAYARAN TOTO 4D (BIG FORECAST)
# ==========================================
DIRECT_PAYOUT = {
    '1st': 2500.0,
    '2nd': 1000.0,
    '3rd': 490.0,
    'special': 180.0,
    'consolation': 60.0
}

def parse_date(date_str):
    """Menukar rentetan tarikh kepada objek datetime."""
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def get_permutation_count(num_str):
    """Mengira bilangan permutasi unik (iBox divisor)."""
    counts = Counter(str(num_str)).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def generate_tuned_dynamic_ema_recs(history_draws):
    """
    FORMULA 36: Tuned Dynamic Exponential Decay Gate
    Mengira taburan kebarangkalian EMA, Entropi Shannon, dan menetapkan mod RM10 vs RM18.
    """
    total_draws = len(history_draws)
    if total_draws == 0:
        return [], 0.0, "DEFENSIVE (RM10)"
        
    decay_lambda = 0.08  # Kadar susutan eksponen teras Formula 05
    
    pos_ema_weights = [defaultdict(float) for _ in range(4)]
    pair_ema_weights = defaultdict(float)
    double_scores = defaultdict(float)
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.2,
        'consolation': 0.8
    }
    
    for idx, draw in enumerate(history_draws):
        delta_t = total_draws - 1 - idx
        time_factor = math.exp(-decay_lambda * delta_t)
        
        items = []
        if draw.get('1st_prize'): items.append((draw['1st_prize'], TIER_WEIGHTS['1st']))
        if draw.get('2nd_prize'): items.append((draw['2nd_prize'], TIER_WEIGHTS['2nd']))
        if draw.get('3rd_prize'): items.append((draw['3rd_prize'], TIER_WEIGHTS['3rd']))
        for sp in draw.get('special_prizes', []): items.append((sp, TIER_WEIGHTS['special']))
        for cs in draw.get('consolation_prizes', []): items.append((cs, TIER_WEIGHTS['consolation']))
        
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                combined_weight = tier_w * time_factor
                cnt = Counter(num_str)
                for d_val, freq in cnt.items():
                    if freq >= 2:
                        double_scores[int(d_val)] += combined_weight * freq
                        
                for pos in range(4):
                    d = int(num_str[pos])
                    pos_ema_weights[pos][d] += combined_weight
                    
                pair_ema_weights[(int(num_str[0]), int(num_str[1]))] += combined_weight
                pair_ema_weights[(int(num_str[2]), int(num_str[3]))] += combined_weight

    # 1. Taburan Posisi & Entropi Shannon
    pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for pos in range(4):
        total_w = sum(pos_ema_weights[pos].values()) or 1.0
        for d in range(10):
            prob = (pos_ema_weights[pos][d] + 0.05) / (total_w + 0.5)
            pos_probs[pos][d] = prob
            if prob > 0:
                shannon_entropy -= prob * math.log(prob)
                
    total_pair_w = sum(pair_ema_weights.values()) or 1.0
    tot_double_score = sum(double_scores.values()) or 1.0
    
    # 2. Penjanaan Skor Calon
    general_candidates = []
    twin_candidates = []
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pair_front_w = (pair_ema_weights.get((d0, d1), 0.0) + 0.01) / (total_pair_w + 1.0)
                    pair_back_w = (pair_ema_weights.get((d2, d3), 0.0) + 0.01) / (total_pair_w + 1.0)
                    
                    score = (
                        pos_probs[0][d0] * 
                        pos_probs[1][d1] * 
                        pos_probs[2][d2] * 
                        pos_probs[3][d3] * 
                        (pair_front_w ** 0.35) * 
                        (pair_back_w ** 0.35)
                    )
                    general_candidates.append((score, num_str))
                    
                    if perms in (12, 6):
                        d_boost = sum(double_scores.get(d, 0.0) / tot_double_score for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        twin_yield_score = score * (24.0 / perms) * (1.0 + 0.4 * d_boost)
                        twin_candidates.append((twin_yield_score, num_str))
                        
    general_candidates.sort(key=lambda x: x[0], reverse=True)
    twin_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 3. Pintu Ambang Entropi Seimbang: 9.17
    is_high_confidence = shannon_entropy < 9.17
    mode_name = "HIGH-CONFIDENCE (RM18)" if is_high_confidence else "DEFENSIVE (RM10)"
    
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # MOD RM18.00 (12 Nombor)
        # Top 6 Am     : Direct RM1 + iBox RM1 = RM 12.00
        # Top 6 Kembar : iBox RM1              = RM  6.00
        for _, num in general_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 6:
                break
        for _, num in twin_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 12:
                break
    else:
        # MOD RM10.00 (7 Nombor)
        # Top 3 Am     : Direct RM1 + iBox RM1 = RM 6.00
        # Top 4 Kembar : iBox RM1              = RM 4.00
        for _, num in general_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 3:
                break
        for _, num in twin_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 7:
                break
                
    return recommendations, shannon_entropy, mode_name

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        print(f"[-] Ralat: Fail data tidak dijumpai di: {DATA_FILE}")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 15:
        print(f"[-] Amaran: Data tidak mencukupi ({total_records} rekod). Diperlukan sekurang-kurangnya 15 rekod.")
        return
        
    latest_draw = draws[-1]
    latest_date = latest_draw.get('date', 'N/A')
    latest_draw_no = latest_draw.get('draw_no', 'N/A')
    
    print("=" * 80)
    print(" 🚀 MENJANA CADANGAN FORMULA 36: Tuned Dynamic Exponential Decay Gate")
    print(f" 📅 Data Sejarah Digunakan: {total_records} Cabutan (Terkini: {latest_date} | Draw: {latest_draw_no})")
    print("=" * 80)
    
    recs, entropy_val, mode_name = generate_tuned_dynamic_ema_recs(draws)
    cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
    
    output_payload = {
        "formula_id": "36_tuned_dynamic_ema_gate",
        "formula_name": "Tuned Dynamic Exponential Decay Gate",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_draw_date": latest_date,
        "last_draw_no": latest_draw_no,
        "mode": mode_name,
        "entropy": round(entropy_val, 4),
        "budget_total_rm": cost_per_draw,
        "total_historical_draws_used": total_records,
        "recommendations": recs
    }
    
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_payload, f, indent=4, ensure_ascii=False)
        
    print(f"[+] Status Mod        : {mode_name} (Entropi: {entropy_val:.4f})")
    print(f"[+] Bajet Dicadangkan : RM {cost_per_draw:.2f}")
    print(f"[+] Jumlah Nombor     : {len(recs)} Nombor")
    print(f"[+] Fail Disimpan Ke  : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
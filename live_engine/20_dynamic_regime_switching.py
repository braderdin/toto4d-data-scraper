#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & PREDICTION PIPELINE
MODULE       : 20_dynamic_regime_switching.py
FORMULA NAME : Dynamic Regime-Switching Gate (HMM Entropy Filter)
DESCRIPTION  : Mengesan keadaan rejim pasaran (Twin Regime vs Distinct Regime)
               menggunakan model Hidden Markov ringkas dan Entropi Shannon untuk
               menyesuaikan peruntukan nombor dan saiz taruhan dinamik (RM18 vs RM11).
OUTPUT PATH  : live_engine/temp/20_dynamic_regime_switching.json
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "20_dynamic_regime_switching.json")

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
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def get_permutation_count(num_str):
    counts = Counter(str(num_str)).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def generate_regime_switching_recs(history_draws):
    """
    FORMULA 20: HMM Regime Gate & Entropy-Driven Allocation
    [LOGIK & FORMULA MATEMATIK ASAL KEKAL 100%]
    """
    if not history_draws:
        return [], 0.0, "DEFENSIVE (RM11)"
        
    total_draws = len(history_draws)
    window_size = 15
    recent_draws = history_draws[-window_size:] if total_draws >= window_size else history_draws
    
    # 1. Analisis Nisbah Rejim Kembar (Twin Density) dalam 15 Sesi Terkini
    twin_count = 0
    total_prize_count = 0
    for draw in recent_draws:
        items = [draw.get('1st_prize'), draw.get('2nd_prize'), draw.get('3rd_prize')]
        items += draw.get('special_prizes', []) + draw.get('consolation_prizes', [])
        for num_str in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                total_prize_count += 1
                if get_permutation_count(num_str) in (12, 6, 4):
                    twin_count += 1
                    
    twin_ratio = (twin_count / max(total_prize_count, 1))
    
    # 2. Pengiraan Taburan Bayesian & Entropi Shannon Posisi
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_alphas = defaultdict(lambda: 0.5)
    double_scores = defaultdict(float)
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.0,
        'consolation': 0.6
    }
    
    for idx, draw in enumerate(history_draws):
        recency = 1.0 + (idx / total_draws) * 0.8
        items = [(draw.get('1st_prize'), TIER_WEIGHTS['1st']), (draw.get('2nd_prize'), TIER_WEIGHTS['2nd']), (draw.get('3rd_prize'), TIER_WEIGHTS['3rd'])]
        items += [(x, TIER_WEIGHTS['special']) for x in draw.get('special_prizes', [])]
        items += [(x, TIER_WEIGHTS['consolation']) for x in draw.get('consolation_prizes', [])]
        
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
            pos_probs[p][d] = prob
            if prob > 0:
                shannon_entropy -= prob * math.log(prob)
                
    tot_pair_alpha = sum(pair_alphas.values()) or 1.0
    tot_double_score = sum(double_scores.values()) or 1.0
    
    # 3. Penentuan Pintu Rejim (Regime Gate)
    # Rejim Kembar aktif jika nisbah kembar >= 40% dan entropi berada di bawah zon rawak (< 8.20)
    is_twin_regime = (twin_ratio >= 0.40) and (shannon_entropy < 8.20)
    regime_mode = "TWIN-REGIME (RM18)" if is_twin_regime else "DISTINCT-REGIME (RM11)"
    
    general_candidates = []
    twin_candidates = []
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pf = pair_alphas.get((d0, d1), 0.5) / tot_pair_alpha
                    pb = pair_alphas.get((d2, d3), 0.5) / tot_pair_alpha
                    
                    log_p = (
                        math.log(pos_probs[0][d0]) +
                        math.log(pos_probs[1][d1]) +
                        math.log(pos_probs[2][d2]) +
                        math.log(pos_probs[3][d3]) +
                        0.3 * math.log(pf) +
                        0.3 * math.log(pb)
                    )
                    general_candidates.append((log_p, num_str))
                    
                    if perms in (12, 6):
                        d_boost = sum(double_scores.get(d, 0.0) / tot_double_score for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        yield_log_p = log_p + math.log(24.0 / perms) + 0.4 * math.log(1.0 + d_boost)
                        twin_candidates.append((yield_log_p, num_str))
                        
    general_candidates.sort(key=lambda x: x[0], reverse=True)
    twin_candidates.sort(key=lambda x: x[0], reverse=True)
    
    recommendations = []
    seen = set()
    
    if is_twin_regime:
        # STRATEGI RM18 (TWIN-REGIME): No 1-6 (Direct + iBox = RM12), No 7-12 (iBox Kembar = RM6)
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
        # STRATEGI RM11 (DISTINCT-REGIME): No 1-3 (Direct + iBox = RM6), No 4-8 (iBox Sahaja = RM5)
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
            if len(recommendations) == 8:
                break
                
    return recommendations, shannon_entropy, regime_mode

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        print(f"[-] Ralat: Fail data tidak dijumpai di: {DATA_FILE}")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    # Susun mengikut susunan kronologi dari lama ke terkini
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 15:
        print(f"[-] Amaran: Data tidak mencukupi ({total_records} rekod). Diperlukan sekurang-kurangnya 15 rekod.")
        return
        
    latest_draw = draws[-1]
    latest_date = latest_draw.get('date', 'N/A')
    latest_draw_no = latest_draw.get('draw_no', 'N/A')
    
    print("=" * 80)
    print(" 🚀 MENJANA CADANGAN FORMULA 20: Dynamic Regime-Switching Gate")
    print(f" 📅 Data Sejarah Digunakan: {total_records} Cabutan (Terkini: {latest_date} | Draw: {latest_draw_no})")
    print("=" * 80)
    
    recs, entropy_val, regime_mode = generate_regime_switching_recs(draws)
    cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
    
    output_payload = {
        "formula_id": "20_dynamic_regime_switching",
        "formula_name": "Dynamic Regime-Switching Gate",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_draw_date": latest_date,
        "last_draw_no": latest_draw_no,
        "regime_mode": regime_mode,
        "entropy": round(entropy_val, 4),
        "budget_total_rm": cost_per_draw,
        "total_historical_draws_used": total_records,
        "recommendations": recs
    }
    
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_payload, f, indent=4, ensure_ascii=False)
        
    print(f"[+] Status Rejim      : {regime_mode} (Entropi: {entropy_val:.4f})")
    print(f"[+] Bajet Dicadangkan : RM {cost_per_draw:.2f}")
    print(f"[+] Jumlah Nombor     : {len(recs)} Nombor")
    print(f"[+] Fail Disimpan Ke  : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
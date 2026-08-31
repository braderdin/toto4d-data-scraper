#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 35_dynamic_ema_decay_gate.py
FORMULA NAME : Dynamic Exponential Decay Gate (EMA + Shannon Entropy)
DESCRIPTION  : Menggabungkan kejituan susutan masa eksponen w(t) = exp(-lambda * delta_t)
               daripada Formula 05 dengan penapis Entropi Shannon untuk pelarasan
               saiz taruhan dinamik dwi-mod:
               - Mod Keyakinan Tinggi (Entropi Rendah) : RM 18.00 (12 Nombor)
               - Mod Defensif / Perlindungan Modal     : RM  8.00 (6 Nombor)
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
BASE_DIR = "/home/braderdin/toto4d-data-scraper"
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_35_dynamic_ema_decay_gate.json")

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

def generate_dynamic_ema_recs(history_draws):
    """
    FORMULA 35: Dynamic Exponential Decay Gate
    Mengira taburan kebarangkalian EMA, Entropi Shannon, dan menetapkan mod RM8 vs RM18.
    """
    total_draws = len(history_draws)
    if total_draws == 0:
        return [], 0.0, "DEFENSIVE (RM8)"
        
    decay_lambda = 0.08  # Kadar susutan eksponen Formula 05 asal
    
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

    # 1. Kiraan Kebarangkalian Posisi & Entropi Shannon
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
    
    # 2. Penjanaan Skor Calon Am & Calon Kembar Berpotensi
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
    
    # 3. Pintu Keyakinan Dinamik (Ambang Entropi: 9.15)
    is_high_confidence = shannon_entropy < 9.15
    mode_name = "HIGH-CONFIDENCE (RM18)" if is_high_confidence else "DEFENSIVE (RM8)"
    
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # STRATEGI RM18.00 (12 Nombor):
        # No 1 - 6  : Direct RM1 + iBox RM1 = RM12.00
        # No 7 - 12 : iBox Kembar Sahaja    = RM 6.00
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
        # STRATEGI RM8.00 (6 Nombor):
        # No 1 - 2  : Direct RM1 + iBox RM1 = RM 4.00
        # No 3 - 6  : iBox Kembar/Pelindung = RM 4.00
        for _, num in general_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 2:
                break
        for _, num in twin_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 6:
                break
                
    return recommendations, shannon_entropy, mode_name

def evaluate_draw_results(recommendations, actual_draw):
    """Menilai kemenangan Direct dan iBox berdasarkan keputusan sebenar."""
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]
    
    total_winnings = 0.0
    hit_logs = []
    
    for item in recommendations:
        rank = item['rank']
        num = item['number']
        bet_direct = item['bet_direct_rm']
        bet_ibox = item['bet_ibox_rm']
        perms = get_permutation_count(num)
        sorted_num = "".join(sorted(num))
        
        # 1. Semakan Direct
        if bet_direct > 0:
            if num == p1:
                win = DIRECT_PAYOUT['1st'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num}) KENA Direct Big 1st Prize (+RM{win:.2f})")
            elif num == p2:
                win = DIRECT_PAYOUT['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num}) KENA Direct Big 2nd Prize (+RM{win:.2f})")
            elif num == p3:
                win = DIRECT_PAYOUT['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num}) KENA Direct Big 3rd Prize (+RM{win:.2f})")
            elif num in specials:
                win = DIRECT_PAYOUT['special'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num}) KENA Direct Big Special (+RM{win:.2f})")
            elif num in consolations:
                win = DIRECT_PAYOUT['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num}) KENA Direct Big Consolation (+RM{win:.2f})")
                
        # 2. Semakan iBox
        if bet_ibox > 0 and perms > 0:
            if "".join(sorted(p1)) == sorted_num:
                win = (DIRECT_PAYOUT['1st'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} [{perms}-way]) KENA iBox 1st Prize ({p1}) (+RM{win:.2f})")
            if "".join(sorted(p2)) == sorted_num:
                win = (DIRECT_PAYOUT['2nd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} [{perms}-way]) KENA iBox 2nd Prize ({p2}) (+RM{win:.2f})")
            if "".join(sorted(p3)) == sorted_num:
                win = (DIRECT_PAYOUT['3rd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} [{perms}-way]) KENA iBox 3rd Prize ({p3}) (+RM{win:.2f})")
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = (DIRECT_PAYOUT['special'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank:02d} ({num} [{perms}-way]) KENA iBox Special ({sp}) (+RM{win:.2f})")
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = (DIRECT_PAYOUT['consolation'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank:02d} ({num} [{perms}-way]) KENA iBox Consolation ({cs}) (+RM{win:.2f})")
                    
    return total_winnings, hit_logs

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data tidak dijumpai di: {DATA_FILE}")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 20:
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod). Perlu sekurang-kurangnya 20 rekod.")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 35: Dynamic Exponential Decay Gate (EMA + Entropy)")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Mod Taruhan Dinamik: Keyakinan Tinggi (RM18.00) vs Defensif (RM8.00)")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    high_conf_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs, entropy_val, mode_name = generate_dynamic_ema_recs(historical_window)
        
        cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
        if "HIGH" in mode_name:
            high_conf_count += 1
            
        latest_recs_payload = {
            "formula_id": "35_dynamic_ema_decay_gate",
            "formula_name": "Dynamic Exponential Decay Gate",
            "target_date": target_date,
            "draw_no": draw_no,
            "mode": mode_name,
            "entropy": round(entropy_val, 4),
            "budget_total_rm": cost_per_draw,
            "recommendations": recs
        }
        
        winnings, hit_logs = evaluate_draw_results(recs, current_draw)
        
        total_invested += cost_per_draw
        total_won += winnings
        net_draw = winnings - cost_per_draw
        
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net_draw:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost_per_draw:8.2f}"
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | {mode_name} (H={entropy_val:.2f}) | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 35)")
    print("=" * 80)
    print(f"  Jumlah Cabutan Diuji     : {len(testing_draws)}")
    print(f"  Sesi Keyakinan Tinggi    : {high_conf_count}/{len(testing_draws)} cabutan")
    print(f"  Jumlah Modal Dikeluarkan : RM {total_invested:.2f}")
    print(f"  Jumlah Pulangan Menang   : RM {total_won:.2f}")
    print(f"  Untung / Rugi Bersih     : RM {net_profit:+.2f}")
    print(f"  Pulangan Modal (ROI)     : {roi_percent:+.2f}%")
    print(f"  Kadar Kenaan (Hit Rate)  : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)} cabutan)")
    print(f"  Fail Cadangan Disimpan   : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
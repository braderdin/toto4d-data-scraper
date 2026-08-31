#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 16_bayesian_position_hybrid.py
FORMULA NAME : Bayesian-Position Co-Occurrence Hybrid
DESCRIPTION  : Model hibrid menggabungkan posterior Dirichlet Bayesian dengan
               matriks korelasi bigram kedudukan digit (Formula 01 + Formula 11).
STRATEGI BET : No 1-5 (RM1 Direct Big + RM1 iBox), No 6-10 (RM1 iBox).
               Total: RM15 / Cabutan.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_16_bayesian_position_hybrid.json")

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

def generate_bayesian_position_hybrid_recs(history_draws, top_n=10):
    """
    FORMULA 16: Bayesian Posterior Likelihood + Positional Bigram Hybrid
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    
    # 1. Parameter Bukti Bayesian Dirichlet
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    
    # 2. Parameter Bigram Matrix (Formula 01)
    bigram_weights = [defaultdict(float) for _ in range(3)]
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.2,
        'consolation': 0.8
    }
    
    for idx, draw in enumerate(history_draws):
        recency_factor = 1.0 + (idx / total_draws) * 0.75
        
        items = []
        if draw.get('1st_prize'): items.append((draw['1st_prize'], TIER_WEIGHTS['1st']))
        if draw.get('2nd_prize'): items.append((draw['2nd_prize'], TIER_WEIGHTS['2nd']))
        if draw.get('3rd_prize'): items.append((draw['3rd_prize'], TIER_WEIGHTS['3rd']))
        for sp in draw.get('special_prizes', []): items.append((sp, TIER_WEIGHTS['special']))
        for cs in draw.get('consolation_prizes', []): items.append((cs, TIER_WEIGHTS['consolation']))
        
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * recency_factor
                for pos in range(4):
                    d = int(num_str[pos])
                    pos_alphas[pos][d] += w
                    
                for bg_pos in range(3):
                    pair = (int(num_str[bg_pos]), int(num_str[bg_pos+1]))
                    bigram_weights[bg_pos][pair] += w
                    
    # Posterior Probabilities
    posterior_probs = [{} for _ in range(4)]
    for pos in range(4):
        total_alpha = sum(pos_alphas[pos].values())
        for d in range(10):
            posterior_probs[pos][d] = pos_alphas[pos][d] / total_alpha
            
    # Bigram Laplace Probabilities
    bigram_probs = [{} for _ in range(3)]
    for bg_pos in range(3):
        total_bg = sum(bigram_weights[bg_pos].values()) or 1.0
        for d1 in range(10):
            for d2 in range(10):
                pair = (d1, d2)
                bigram_probs[bg_pos][pair] = (bigram_weights[bg_pos][pair] + 0.01) / (total_bg + 1.0)
                
    candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    # Gabungan Bayesian Posterior & Bigram Continuity
                    score = (
                        posterior_probs[0][d0] * 
                        posterior_probs[1][d1] * 
                        posterior_probs[2][d2] * 
                        posterior_probs[3][d3] *
                        (bigram_probs[0].get((d0, d1), 0.001) ** 0.45) *
                        (bigram_probs[1].get((d1, d2), 0.001) ** 0.45) *
                        (bigram_probs[2].get((d2, d3), 0.001) ** 0.45)
                    )
                    candidates.append((score, f"{d0}{d1}{d2}{d3}"))
                    
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    top_numbers = []
    seen = set()
    for _, num in candidates:
        if num not in seen:
            seen.add(num)
            top_numbers.append(num)
        if len(top_numbers) == top_n:
            break
            
    # Skema Taruhan Baru: No 1-5 (Direct + iBox), No 6-10 (iBox sahaja)
    recommendations = []
    for rank, num in enumerate(top_numbers, start=1):
        if rank <= 5:
            recommendations.append({
                "rank": rank,
                "number": num,
                "bet_direct_rm": 1,
                "bet_ibox_rm": 1
            })
        else:
            recommendations.append({
                "rank": rank,
                "number": num,
                "bet_direct_rm": 0,
                "bet_ibox_rm": 1
            })
            
    return recommendations

def evaluate_draw_results(recommendations, actual_draw):
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
        
        # Semakan Direct Big
        if bet_direct > 0:
            if num == p1:
                win = DIRECT_PAYOUT['1st'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Big 1st Prize (+RM{win:.2f})")
            elif num == p2:
                win = DIRECT_PAYOUT['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Big 2nd Prize (+RM{win:.2f})")
            elif num == p3:
                win = DIRECT_PAYOUT['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Big 3rd Prize (+RM{win:.2f})")
            elif num in specials:
                win = DIRECT_PAYOUT['special'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Big Special (+RM{win:.2f})")
            elif num in consolations:
                win = DIRECT_PAYOUT['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Big Consolation (+RM{win:.2f})")
                
        # Semakan iBox
        if bet_ibox > 0 and perms > 0:
            if "".join(sorted(p1)) == sorted_num:
                win = (DIRECT_PAYOUT['1st'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num} [{perms}-way]) KENA iBox 1st Prize ({p1}) (+RM{win:.2f})")
            if "".join(sorted(p2)) == sorted_num:
                win = (DIRECT_PAYOUT['2nd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num} [{perms}-way]) KENA iBox 2nd Prize ({p2}) (+RM{win:.2f})")
            if "".join(sorted(p3)) == sorted_num:
                win = (DIRECT_PAYOUT['3rd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num} [{perms}-way]) KENA iBox 3rd Prize ({p3}) (+RM{win:.2f})")
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = (DIRECT_PAYOUT['special'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num} [{perms}-way]) KENA iBox Special ({sp}) (+RM{win:.2f})")
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = (DIRECT_PAYOUT['consolation'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num} [{perms}-way]) KENA iBox Consolation ({cs}) (+RM{win:.2f})")
                    
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
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 16: Bayesian-Position Co-Occurrence Hybrid")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Skema Taruhan: No 1-5 (RM2 Direct Big+iBox) | No 6-10 (RM1 iBox) = RM15.00/Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_bayesian_position_hybrid_recs(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "16_bayesian_position_hybrid",
            "formula_name": "Bayesian-Position Co-Occurrence Hybrid",
            "target_date": target_date,
            "draw_no": draw_no,
            "budget_total_rm": 15,
            "recommendations": recs
        }
        
        cost_per_draw = 15.0
        winnings, hit_logs = evaluate_draw_results(recs, current_draw)
        
        total_invested += cost_per_draw
        total_won += winnings
        net_draw = winnings - cost_per_draw
        
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net_draw:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost_per_draw:8.2f}"
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | Draw: {draw_no} | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 16)")
    print("=" * 80)
    print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)}")
    print(f"  Jumlah Modal Dikeluarkan: RM {total_invested:.2f}")
    print(f"  Jumlah Pulangan Menang  : RM {total_won:.2f}")
    print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
    print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
    print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)} cabutan)")
    print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 09_lag_autocorrelation.py
FORMULA NAME : Autocorrelation Lag Series
DESCRIPTION  : Menganalisis korelasi siri masa kitaran lag-1 hingga lag-4 untuk
               mengesan resapan ulangan digit (cross-tier leakage) dari hadiah
               Special dan Consolation ke cabutan berikutnya.
AUTHO/USER   : braderdin
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_09_lag_autocorrelation.json")

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
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def get_permutation_count(num_str):
    """Mengira bilangan permutasi unik (iBox divisor)."""
    counts = Counter(num_str).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def generate_lag_autocorr_recommendations(history_draws, top_n=10):
    """
    FORMULA 09: Autocorrelation Lag Series
    Menjana 10 nombor berasaskan korelasi lag-1 hingga lag-4 cabutan terdahulu.
    """
    total_draws = len(history_draws)
    if total_draws < 5:
        return []
        
    # Pemberat susutan mengikut sela Lag
    LAG_WEIGHTS = {1: 0.45, 2: 0.28, 3: 0.17, 4: 0.10}
    
    pos_lag_scores = [defaultdict(float) for _ in range(4)]
    pair_lag_scores = defaultdict(float)
    pool_repeat_scores = defaultdict(float)
    
    for lag, lag_w in LAG_WEIGHTS.items():
        if total_draws > lag:
            ref_draw = history_draws[-lag]
            
            # Kumpul nombor dari cabutan rujukan pada jarak lag
            all_lag_nums = []
            if ref_draw.get('1st_prize'): all_lag_nums.append((ref_draw['1st_prize'], 2.5))
            if ref_draw.get('2nd_prize'): all_lag_nums.append((ref_draw['2nd_prize'], 2.0))
            if ref_draw.get('3rd_prize'): all_lag_nums.append((ref_draw['3rd_prize'], 1.5))
            for sp in ref_draw.get('special_prizes', []): all_lag_nums.append((sp, 1.2))
            for cs in ref_draw.get('consolation_prizes', []): all_lag_nums.append((cs, 1.0))
            
            for num_str, tier_w in all_lag_nums:
                num_str = str(num_str).strip()
                if len(num_str) == 4 and num_str.isdigit():
                    pool_repeat_scores[num_str] += lag_w * tier_w
                    for pos in range(4):
                        d = int(num_str[pos])
                        pos_lag_scores[pos][d] += lag_w * tier_w
                        
                    # Pasangan 2-digit bersekutu
                    pair_lag_scores[(int(num_str[0]), int(num_str[1]))] += lag_w * tier_w
                    pair_lag_scores[(int(num_str[2]), int(num_str[3]))] += lag_w * tier_w
                    
    # Normalisasi Laplace
    pos_probs = [{} for _ in range(4)]
    for pos in range(4):
        total_w = sum(pos_lag_scores[pos].values()) or 1.0
        for d in range(10):
            pos_probs[pos][d] = (pos_lag_scores[pos][d] + 0.1) / (total_w + 1.0)
            
    total_pair_w = sum(pair_lag_scores.values()) or 1.0
    
    candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    pair_f_w = (pair_lag_scores.get((d0, d1), 0.0) + 0.01) / (total_pair_w + 1.0)
                    pair_b_w = (pair_lag_scores.get((d2, d3), 0.0) + 0.01) / (total_pair_w + 1.0)
                    direct_repeat_boost = pool_repeat_scores.get(num_str, 0.0)
                    
                    base_prob = (
                        pos_probs[0][d0] * 
                        pos_probs[1][d1] * 
                        pos_probs[2][d2] * 
                        pos_probs[3][d3] * 
                        (pair_f_w ** 0.3) * 
                        (pair_b_w ** 0.3)
                    )
                    
                    score = base_prob * (1.0 + direct_repeat_boost * 1.5)
                    candidates.append((score, num_str))
                    
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    top_numbers = []
    seen = set()
    for _, num in candidates:
        if num not in seen:
            seen.add(num)
            top_numbers.append(num)
        if len(top_numbers) == top_n:
            break
            
    recommendations = []
    for rank, num in enumerate(top_numbers, start=1):
        if rank <= 3:
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
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 1st Prize (+RM{win:.2f})")
            elif num == p2:
                win = DIRECT_PAYOUT['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 2nd Prize (+RM{win:.2f})")
            elif num == p3:
                win = DIRECT_PAYOUT['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 3rd Prize (+RM{win:.2f})")
            elif num in specials:
                win = DIRECT_PAYOUT['special'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Special (+RM{win:.2f})")
            elif num in consolations:
                win = DIRECT_PAYOUT['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Consolation (+RM{win:.2f})")
                
        # 2. Semakan iBox
        if bet_ibox > 0 and perms > 0:
            if "".join(sorted(p1)) == sorted_num:
                win = (DIRECT_PAYOUT['1st'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 1st Prize ({p1}) (+RM{win:.2f})")
            if "".join(sorted(p2)) == sorted_num:
                win = (DIRECT_PAYOUT['2nd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 2nd Prize ({p2}) (+RM{win:.2f})")
            if "".join(sorted(p3)) == sorted_num:
                win = (DIRECT_PAYOUT['3rd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 3rd Prize ({p3}) (+RM{win:.2f})")
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = (DIRECT_PAYOUT['special'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num}) KENA iBox Special ({sp}) (+RM{win:.2f})")
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = (DIRECT_PAYOUT['consolation'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num}) KENA iBox Consolation ({cs}) (+RM{win:.2f})")
                    
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
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod). Perlu lebih banyak data.")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 09: Autocorrelation Lag Series")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Kos Pertaruhan Per Cabutan: RM13.00 (No 1-3: RM2, No 4-10: RM1)")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_lag_autocorr_recommendations(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "09_lag_autocorrelation",
            "formula_name": "Autocorrelation Lag Series",
            "target_date": target_date,
            "draw_no": draw_no,
            "budget_total_rm": 13,
            "recommendations": recs
        }
        
        cost_per_draw = 13.0
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
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 09)")
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
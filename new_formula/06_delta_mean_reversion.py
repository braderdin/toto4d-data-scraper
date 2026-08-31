#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 06_delta_mean_reversion.py
FORMULA NAME : Delta Vector Reversion
DESCRIPTION  : Mengira anjakan vektor perbezaan (absolute deltas) dan pembalikan
               min modulo 10,000 antara hadiah utama untuk menjana titik unjuran 4D.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_06_delta_mean_reversion.json")

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

def generate_delta_reversion_recommendations(history_draws, top_n=10):
    """
    FORMULA 06: Delta Vector Reversion
    Mengunjur 10 nombor berasaskan pembalikan beza nilai modular antara hadiah.
    """
    if len(history_draws) < 3:
        return []
        
    delta_hist = []
    vector_shift_hist = [defaultdict(int) for _ in range(4)]
    
    for draw in history_draws:
        p1 = draw.get('1st_prize', '')
        p2 = draw.get('2nd_prize', '')
        p3 = draw.get('3rd_prize', '')
        
        valid_nums = []
        for p in (p1, p2, p3):
            p = str(p).strip()
            if len(p) == 4 and p.isdigit():
                valid_nums.append(int(p))
                
        if len(valid_nums) >= 2:
            d12 = abs(valid_nums[0] - valid_nums[1])
            delta_hist.append(d12)
            if len(valid_nums) == 3:
                d23 = abs(valid_nums[1] - valid_nums[2])
                d13 = abs(valid_nums[0] - valid_nums[2])
                delta_hist.extend([d23, d13])
                
    # Kira anjakan vektor antara cabutan berturutan
    for i in range(1, len(history_draws)):
        prev_p1 = str(history_draws[i-1].get('1st_prize', '')).strip()
        curr_p1 = str(history_draws[i].get('1st_prize', '')).strip()
        if len(prev_p1) == 4 and prev_p1.isdigit() and len(curr_p1) == 4 and curr_p1.isdigit():
            for pos in range(4):
                shift = (int(curr_p1[pos]) - int(prev_p1[pos])) % 10
                vector_shift_hist[pos][shift] += 1
                
    # Dapatkan min delta
    avg_delta = int(sum(delta_hist) / len(delta_hist)) if delta_hist else 1250
    median_delta = sorted(delta_hist)[len(delta_hist)//2] if delta_hist else 1000
    
    # Rujukan daripada cabutan terkini
    last_draw = history_draws[-1]
    base_seeds = []
    for k in ('1st_prize', '2nd_prize', '3rd_prize'):
        val = str(last_draw.get(k, '')).strip()
        if len(val) == 4 and val.isdigit():
            base_seeds.append(int(val))
            
    if not base_seeds:
        base_seeds = [1234, 5678, 9012]
        
    candidates = []
    
    # 1. Anjakan Delta Linear Modulo 10,000
    for seed in base_seeds:
        candidates.append((seed + avg_delta) % 10000)
        candidates.append((seed - avg_delta) % 10000)
        candidates.append((seed + median_delta) % 10000)
        candidates.append((seed - median_delta) % 10000)
        candidates.append((seed + (avg_delta // 2)) % 10000)
        candidates.append((seed - (avg_delta // 2)) % 10000)
        
    # 2. Anjakan Vektor Digit Modulo 10 mengikut mod anjakan tertinggi
    primary_seed_str = f"{base_seeds[0]:04d}"
    best_shifts = []
    for pos in range(4):
        sorted_shifts = sorted(vector_shift_hist[pos].items(), key=lambda x: x[1], reverse=True)
        top_shift = sorted_shifts[0][0] if sorted_shifts else 1
        best_shifts.append(top_shift)
        
    # Vektor anjakan positif & songsang
    vec_cand_1 = "".join(str((int(primary_seed_str[pos]) + best_shifts[pos]) % 10) for pos in range(4))
    vec_cand_2 = "".join(str((int(primary_seed_str[pos]) - best_shifts[pos]) % 10) for pos in range(4))
    vec_cand_3 = "".join(str((int(primary_seed_str[pos]) + 5) % 10) for pos in range(4)) # Anjakan separuh skala
    
    candidate_strings = [f"{c:04d}" for c in candidates] + [vec_cand_1, vec_cand_2, vec_cand_3]
    
    # Saring 10 nombor unik
    top_numbers = []
    seen = set()
    for num_str in candidate_strings:
        if num_str not in seen:
            seen.add(num_str)
            top_numbers.append(num_str)
        if len(top_numbers) == top_n:
            break
            
    # Jika masih kurang dari 10, lengkapkan dengan anjakan modular
    counter = 1
    while len(top_numbers) < top_n:
        fill_num = f"{(base_seeds[0] + counter * 333) % 10000:04d}"
        if fill_num not in seen:
            seen.add(fill_num)
            top_numbers.append(fill_num)
        counter += 1
        
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
    print(f" SIMULASI FORMULA 06: Delta Vector Reversion")
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
        recs = generate_delta_reversion_recommendations(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "06_delta_mean_reversion",
            "formula_name": "Delta Vector Reversion",
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
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 06)")
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
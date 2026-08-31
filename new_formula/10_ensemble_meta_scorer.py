#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 10_ensemble_meta_scorer.py
FORMULA NAME : Ensemble Meta Consensus
DESCRIPTION  : Model hibrid ensemble peringkat tinggi yang menggabungkan dan
               menimbang markah konsensus daripada keseluruhan 9 formula matematik
               terdahulu bagi menyaring 10 nombor pilihan paling optimum.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_10_ensemble_meta_scorer.json")

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

def get_digital_root(n):
    if n == 0: return 0
    return 1 + ((n - 1) % 9)

def generate_ensemble_meta_recommendations(history_draws, top_n=10):
    """
    FORMULA 10: Ensemble Meta Consensus
    Mengumpulkan skor komposit berwajaran daripada kesemua dimensi analitik.
    """
    total_draws = len(history_draws)
    if total_draws < 5:
        return []
        
    candidate_scores = defaultdict(float)
    
    # 1. Komponen Posisi & Frekuensi (Hot Matrix & EMA)
    pos_weights = [defaultdict(float) for _ in range(4)]
    decay_lambda = 0.07
    
    for idx, draw in enumerate(history_draws):
        delta_t = total_draws - 1 - idx
        t_factor = math.exp(-decay_lambda * delta_t)
        
        items = []
        if draw.get('1st_prize'): items.append((draw['1st_prize'], 3.5))
        if draw.get('2nd_prize'): items.append((draw['2nd_prize'], 2.5))
        if draw.get('3rd_prize'): items.append((draw['3rd_prize'], 2.0))
        for sp in draw.get('special_prizes', []): items.append((sp, 1.0))
        for cs in draw.get('consolation_prizes', []): items.append((cs, 0.8))
        
        for num_str, w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                for pos in range(4):
                    pos_weights[pos][int(num_str[pos])] += w * t_factor
                    
    pos_probs = [{} for _ in range(4)]
    for pos in range(4):
        tot_w = sum(pos_weights[pos].values()) or 1.0
        for d in range(10):
            pos_probs[pos][d] = (pos_weights[pos][d] + 0.1) / (tot_w + 1.0)
            
    # 2. Komponen Rujukan & Transformasi Delta / Pantulan Simetri
    last_draw = history_draws[-1]
    top3_seeds = []
    for k in ('1st_prize', '2nd_prize', '3rd_prize'):
        v = str(last_draw.get(k, '')).strip()
        if len(v) == 4 and v.isdigit():
            top3_seeds.append(v)
            
    if not top3_seeds:
        top3_seeds = ["1234", "5678", "9012"]
        
    # Anjakan delta & pantulan
    heuristic_pool = set()
    for s in top3_seeds:
        # Pantulan
        m_num = "".join(str((10 - int(c)) % 10) for c in s)
        heuristic_pool.add(m_num)
        
        # Delta shift
        val = int(s)
        heuristic_pool.add(f"{(val + 1111) % 10000:04d}")
        heuristic_pool.add(f"{(val - 1111) % 10000:04d}")
        heuristic_pool.add(f"{(val + 3333) % 10000:04d}")
        heuristic_pool.add(f"{(val - 3333) % 10000:04d}")
        
    # 3. Penilaian Komprehensif Ruang 0000-9999
    mean_sum = 18.0
    std_sum = 5.67
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    digits = [d0, d1, d2, d3]
                    
                    # Skor Posisi & EMA
                    p_score = pos_probs[0][d0] * pos_probs[1][d1] * pos_probs[2][d2] * pos_probs[3][d3]
                    
                    # Skor Bell Curve
                    curr_sum = d0 + d1 + d2 + d3
                    gauss_factor = math.exp(- ((curr_sum - mean_sum) ** 2) / (2 * (std_sum ** 2)))
                    
                    # Skor Keseimbangan Pariti (2O2E) & Skala (2L2H)
                    odd_c = sum(1 for d in digits if d % 2 != 0)
                    low_c = sum(1 for d in digits if d < 5)
                    balance_mult = 1.0
                    if odd_c == 2: balance_mult *= 1.25
                    if low_c == 2: balance_mult *= 1.25
                    
                    # Bonus Konsensus Heuristik (Mirror / Delta)
                    heur_bonus = 1.4 if num_str in heuristic_pool else 1.0
                    
                    final_score = p_score * gauss_factor * balance_mult * heur_bonus
                    candidate_scores[num_str] = final_score
                    
    sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    
    top_numbers = [item[0] for item in sorted_candidates[:top_n]]
    
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
    print(f" SIMULASI FORMULA 10: Ensemble Meta Consensus")
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
        recs = generate_ensemble_meta_recommendations(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "10_ensemble_meta_scorer",
            "formula_name": "Ensemble Meta Consensus",
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
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 10)")
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
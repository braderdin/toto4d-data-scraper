#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 17_bayesian_pair_yield.py
FORMULA NAME : Bayesian Double-Yield Optimizer
DESCRIPTION  : Memanfaatkan taburan posterior Bayesian, di mana No 1-5 diberi
               keutamaan kebarangkalian umum tertinggi dan No 6-10 ditapis khas
               hanya untuk famili 12-way & 6-way (double digits) demi pulangan iBox tinggi.
STRATEGI BET : No 1-5 (RM1 Direct Big + RM1 iBox), No 6-10 (RM1 iBox Kembar).
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_17_bayesian_pair_yield.json")

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

def generate_bayesian_pair_yield_recs(history_draws, top_n=10):
    """
    FORMULA 17: Bayesian Posterior + 12-way / 6-way Yield Targeting
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_alphas = defaultdict(lambda: 0.5)
    double_counts = defaultdict(float)
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.0,
        'consolation': 0.6
    }
    
    for idx, draw in enumerate(history_draws):
        recency_factor = 1.0 + (idx / total_draws) * 0.8
        
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
                cnt = Counter(num_str)
                for d_val, freq in cnt.items():
                    if freq >= 2:
                        double_counts[int(d_val)] += w * freq
                        
                for pos in range(4):
                    pos_alphas[pos][int(num_str[pos])] += w
                    
                pair_alphas[(int(num_str[0]), int(num_str[1]))] += w * 0.5
                pair_alphas[(int(num_str[2]), int(num_str[3]))] += w * 0.5
                
    posterior_probs = [{} for _ in range(4)]
    for pos in range(4):
        total_alpha = sum(pos_alphas[pos].values())
        for d in range(10):
            posterior_probs[pos][d] = pos_alphas[pos][d] / total_alpha
            
    total_pair_alpha = sum(pair_alphas.values()) or 1.0
    total_double_w = sum(double_counts.values()) or 1.0
    
    all_candidates = []
    double_candidates = []
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pair_f = pair_alphas.get((d0, d1), 0.5) / total_pair_alpha
                    pair_b = pair_alphas.get((d2, d3), 0.5) / total_pair_alpha
                    
                    base_log_p = (
                        math.log(posterior_probs[0][d0]) +
                        math.log(posterior_probs[1][d1]) +
                        math.log(posterior_probs[2][d2]) +
                        math.log(posterior_probs[3][d3]) +
                        0.3 * math.log(pair_f) +
                        0.3 * math.log(pair_b)
                    )
                    
                    all_candidates.append((base_log_p, num_str))
                    
                    # Saring khusus untuk 12-way dan 6-way
                    if perms in (12, 6):
                        d_bonus = sum(double_counts.get(d, 0.0) / total_double_w for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        yield_log_p = base_log_p + math.log(24.0 / perms) + 0.5 * math.log(1.0 + d_bonus)
                        double_candidates.append((yield_log_p, num_str))
                        
    all_candidates.sort(key=lambda x: x[0], reverse=True)
    double_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Pilih 5 Nombor Utama (Top 1 - 5)
    selected_top5 = []
    seen = set()
    for _, num in all_candidates:
        if num not in seen:
            seen.add(num)
            selected_top5.append(num)
        if len(selected_top5) == 5:
            break
            
    # Pilih 5 Nombor Kembar 12-way / 6-way (Top 6 - 10)
    selected_top6_10 = []
    for _, num in double_candidates:
        if num not in seen:
            seen.add(num)
            selected_top6_10.append(num)
        if len(selected_top6_10) == 5:
            break
            
    # Susun senarai rekomendasi
    recommendations = []
    for rank, num in enumerate(selected_top5, start=1):
        recommendations.append({
            "rank": rank,
            "number": num,
            "bet_direct_rm": 1,
            "bet_ibox_rm": 1
        })
        
    for rank, num in enumerate(selected_top6_10, start=6):
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
    print(f" SIMULASI FORMULA 17: Bayesian Double-Yield Optimizer")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Skema Taruhan: No 1-5 (RM2 Direct Big+iBox) | No 6-10 (RM1 iBox Kembar) = RM15.00/Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_bayesian_pair_yield_recs(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "17_bayesian_pair_yield",
            "formula_name": "Bayesian Double-Yield Optimizer",
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
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 17)")
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
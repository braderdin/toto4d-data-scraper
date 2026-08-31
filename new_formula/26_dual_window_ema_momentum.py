#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 26_dual_window_ema_momentum.py
FORMULA NAME : Dual-Window EMA Momentum Sizer (Formula 05 + Formula 18 Hybrid)
DESCRIPTION  : Menggabungkan keupayaan susutan masa eksponen (Fast EMA vs Slow EMA)
               dengan penapis Entropi Shannon dan strategi pertaruhan dinamik
               asimetrik (RM18.00 Keyakinan Tinggi vs RM11.00 Defensif).
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_26_dual_window_ema_momentum.json")

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

def generate_dual_ema_recs(history_draws):
    """
    FORMULA 26: Dual-Window EMA Momentum + Dynamic Bet Sizing
    """
    if not history_draws:
        return [], 0.0, "DEFENSIVE (RM11)"
        
    total_draws = len(history_draws)
    short_window_size = 15
    long_window_size = 60
    
    short_history = history_draws[-short_window_size:] if total_draws >= short_window_size else history_draws
    long_history = history_draws[-long_window_size:] if total_draws >= long_window_size else history_draws
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.2,
        'consolation': 0.8
    }
    
    # 1. Slow EMA (Long Window - Baseline Stability: lambda = 0.04)
    lambda_slow = 0.04
    pos_ema_slow = [defaultdict(float) for _ in range(4)]
    for idx, draw in enumerate(long_history):
        delta_t = len(long_history) - 1 - idx
        t_factor = math.exp(-lambda_slow * delta_t)
        items = [(draw.get('1st_prize'), TIER_WEIGHTS['1st']), (draw.get('2nd_prize'), TIER_WEIGHTS['2nd']), (draw.get('3rd_prize'), TIER_WEIGHTS['3rd'])]
        items += [(x, TIER_WEIGHTS['special']) for x in draw.get('special_prizes', [])]
        items += [(x, TIER_WEIGHTS['consolation']) for x in draw.get('consolation_prizes', [])]
        for s, tier_w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tier_w * t_factor
                for p in range(4):
                    pos_ema_slow[p][int(s[p])] += w
                    
    # 2. Fast EMA (Short Window - Recent Momentum: lambda = 0.12)
    lambda_fast = 0.12
    pos_ema_fast = [defaultdict(float) for _ in range(4)]
    pair_ema_fast = defaultdict(float)
    double_freq_fast = defaultdict(float)
    
    for idx, draw in enumerate(short_history):
        delta_t = len(short_history) - 1 - idx
        t_factor = math.exp(-lambda_fast * delta_t)
        items = [(draw.get('1st_prize'), TIER_WEIGHTS['1st']), (draw.get('2nd_prize'), TIER_WEIGHTS['2nd']), (draw.get('3rd_prize'), TIER_WEIGHTS['3rd'])]
        items += [(x, TIER_WEIGHTS['special']) for x in draw.get('special_prizes', [])]
        items += [(x, TIER_WEIGHTS['consolation']) for x in draw.get('consolation_prizes', [])]
        for s, tier_w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tier_w * t_factor
                for d_val, freq in Counter(s).items():
                    if freq >= 2:
                        double_freq_fast[int(d_val)] += w * freq
                for p in range(4):
                    pos_ema_fast[p][int(s[p])] += w
                pair_ema_fast[(int(s[0]), int(s[1]))] += w
                pair_ema_fast[(int(s[2]), int(s[3]))] += w
                
    # 3. Gabungan Taburan Posisi (65% Fast EMA + 35% Slow EMA) & Kira Entropi Shannon
    combined_pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    
    for p in range(4):
        tot_slow = sum(pos_ema_slow[p].values()) or 1.0
        tot_fast = sum(pos_ema_fast[p].values()) or 1.0
        for d in range(10):
            p_slow = (pos_ema_slow[p][d] + 0.05) / (tot_slow + 0.5)
            p_fast = (pos_ema_fast[p][d] + 0.05) / (tot_fast + 0.5)
            prob = (0.65 * p_fast) + (0.35 * p_slow)
            combined_pos_probs[p][d] = prob
            if prob > 0:
                shannon_entropy -= prob * math.log(prob)
                
    tot_pair_fast = sum(pair_ema_fast.values()) or 1.0
    tot_double_fast = sum(double_freq_fast.values()) or 1.0
    
    # 4. Skor Kombinasi 4D & Calon Kembar Asimetrik
    all_candidates = []
    twin_candidates = []
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pf = (pair_ema_fast.get((d0, d1), 0.0) + 0.01) / (tot_pair_fast + 1.0)
                    pb = (pair_ema_fast.get((d2, d3), 0.0) + 0.01) / (tot_pair_fast + 1.0)
                    
                    joint_prob = (
                        combined_pos_probs[0][d0] * 
                        combined_pos_probs[1][d1] * 
                        combined_pos_probs[2][d2] * 
                        combined_pos_probs[3][d3] * 
                        (pf ** 0.35) * 
                        (pb ** 0.35)
                    )
                    all_candidates.append((joint_prob, num_str))
                    
                    if perms in (12, 6, 4):
                        db = sum(double_freq_fast.get(d, 0.0) / tot_double_fast for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        yield_score = joint_prob * (24.0 / perms) * (1.0 + db * 1.5)
                        twin_candidates.append((yield_score, num_str))
                        
    all_candidates.sort(key=lambda x: x[0], reverse=True)
    twin_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 5. Penentuan Rejim Keyakinan Dinamik (Ambang Entropi H = 8.15)
    is_high_confidence = shannon_entropy < 8.15
    conf_tier = "HIGH (RM18)" if is_high_confidence else "LOW (RM11)"
    
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # Mod RM18: No 1-6 (Direct Big + iBox = RM12), No 7-12 (iBox Kembar = RM6)
        for _, num in all_candidates:
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
        # Mod RM11: No 1-3 (Direct Big + iBox = RM6), No 4-8 (iBox Kembar/Teras = RM5)
        for _, num in all_candidates:
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
                
    return recommendations, shannon_entropy, conf_tier

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
        
        # Direct Big
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
                
        # iBox
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
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 26: Dual-Window EMA Momentum Sizer")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Taruhan Dinamik: Keyakinan Tinggi = RM18.00 | Keyakinan Rendah = RM11.00")
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
        recs, entropy_val, conf_tier = generate_dual_ema_recs(historical_window)
        
        cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
        if "HIGH" in conf_tier:
            high_conf_count += 1
            
        latest_recs_payload = {
            "formula_id": "26_dual_window_ema_momentum",
            "formula_name": "Dual-Window EMA Momentum Sizer",
            "target_date": target_date,
            "draw_no": draw_no,
            "confidence_tier": conf_tier,
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
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | {conf_tier} (H={entropy_val:.2f}) | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 26)")
    print("=" * 80)
    print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)}")
    print(f"  Sesi Keyakinan Tinggi   : {high_conf_count}/{len(testing_draws)} cabutan")
    print(f"  Jumlah Modal Dikeluarkan: RM {total_invested:.2f}")
    print(f"  Jumlah Pulangan Menang  : RM {total_won:.2f}")
    print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
    print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
    print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)} cabutan)")
    print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
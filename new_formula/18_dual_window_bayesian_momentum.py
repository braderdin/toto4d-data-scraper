#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 18_dual_window_bayesian_momentum.py
FORMULA NAME : Dual-Window Bayesian Momentum
DESCRIPTION  : Model Bayesian dwi-tetingkap masa (12 cabutan pantas vs 60 cabutan asas)
               dengan pelarasan saiz taruhan dinamik berasaskan Entropi Shannon:
               - Keyakinan Tinggi (Entropi Rendah) : RM 18.00 (12 Nombor)
               - Keyakinan Rendah (Entropi Tinggi) : RM 11.00 (8 Nombor)
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_18_dual_window_bayesian_momentum.json")

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

def generate_dual_window_bayesian_recs(history_draws):
    """
    FORMULA 18: Dual-Window Bayesian Momentum + Dynamic Bet Sizing
    """
    if not history_draws:
        return [], 0.0, "LOW"
        
    total_draws = len(history_draws)
    short_window_size = 12
    long_window_size = 60
    
    short_history = history_draws[-short_window_size:] if total_draws >= short_window_size else history_draws
    long_history = history_draws[-long_window_size:] if total_draws >= long_window_size else history_draws
    
    # 1. Kiraan Dirichlet untuk Tetingkap Panjang (Asas Kestabilan)
    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(4)]
    for draw in long_history:
        items = [(draw.get('1st_prize'), 3.5), (draw.get('2nd_prize'), 2.5), (draw.get('3rd_prize'), 2.0)]
        items += [(x, 1.0) for x in draw.get('special_prizes', [])]
        items += [(x, 0.6) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4):
                    pos_alphas_long[p][int(s[p])] += w
                    
    # 2. Kiraan Dirichlet untuk Tetingkap Pendek (Momentum Panas Terkini)
    pos_alphas_short = [{d: 0.5 for d in range(10)} for _ in range(4)]
    pair_alphas_short = defaultdict(lambda: 0.2)
    for idx, draw in enumerate(short_history):
        rec_boost = 1.0 + (idx / len(short_history)) * 1.0
        items = [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 3.0), (draw.get('3rd_prize'), 2.0)]
        items += [(x, 1.2) for x in draw.get('special_prizes', [])]
        items += [(x, 0.8) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                wb = w * rec_boost
                for p in range(4):
                    pos_alphas_short[p][int(s[p])] += wb
                pair_alphas_short[(int(s[0]), int(s[1]))] += wb * 0.5
                pair_alphas_short[(int(s[2]), int(s[3]))] += wb * 0.5

    # 3. Gabungan Parameter Posterior Berwajar: 35% Long + 65% Short Momentum
    combined_pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    
    for p in range(4):
        tot_l = sum(pos_alphas_long[p].values())
        tot_s = sum(pos_alphas_short[p].values())
        for d in range(10):
            p_long = pos_alphas_long[p][d] / tot_l
            p_short = pos_alphas_short[p][d] / tot_s
            combined_prob = (0.35 * p_long) + (0.65 * p_short)
            combined_pos_probs[p][d] = combined_prob
            if combined_prob > 0:
                shannon_entropy -= combined_prob * math.log(combined_prob)
                
    tot_pair_alpha = sum(pair_alphas_short.values()) or 1.0
    
    # Skor semua kombinasi 4D
    candidates = []
    double_candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pf = (pair_alphas_short.get((d0, d1), 0.2)) / tot_pair_alpha
                    pb = (pair_alphas_short.get((d2, d3), 0.2)) / tot_pair_alpha
                    
                    log_p = (
                        math.log(combined_pos_probs[0][d0]) +
                        math.log(combined_pos_probs[1][d1]) +
                        math.log(combined_pos_probs[2][d2]) +
                        math.log(combined_pos_probs[3][d3]) +
                        0.35 * math.log(pf) +
                        0.35 * math.log(pb)
                    )
                    candidates.append((log_p, num_str))
                    
                    if perms in (12, 6):
                        yield_log_p = log_p + math.log(24.0 / perms)
                        double_candidates.append((yield_log_p, num_str))
                        
    candidates.sort(key=lambda x: x[0], reverse=True)
    double_candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 4. Penentuan Rejim Keyakinan Berdasarkan Entropi Shannon (Ambang: 8.15)
    is_high_confidence = shannon_entropy < 8.15
    confidence_tier = "HIGH (RM18)" if is_high_confidence else "LOW (RM11)"
    
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # STRATEGI RM18: No 1-6 (Direct + iBox = RM12), No 7-12 (iBox Kembar = RM6)
        # Top 6 Umum
        for _, num in candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 6:
                break
        # Top 7-12 Kembar
        for _, num in double_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 12:
                break
    else:
        # STRATEGI RM11: No 1-3 (Direct + iBox = RM6), No 4-8 (iBox Sahaja = RM5)
        # Top 3 Umum
        for _, num in candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 3:
                break
        # Top 4-8 Pelindung
        for _, num in double_candidates:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 8:
                break
                
    return recommendations, shannon_entropy, confidence_tier

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
    print(f" SIMULASI FORMULA 18: Dual-Window Bayesian Momentum")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Strategi Taruhan Dinamik: Keyakinan Tinggi = RM18.00 | Keyakinan Rendah = RM11.00")
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
        recs, entropy_val, conf_tier = generate_dual_window_bayesian_recs(historical_window)
        
        cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
        if "HIGH" in conf_tier:
            high_conf_count += 1
            
        latest_recs_payload = {
            "formula_id": "18_dual_window_bayesian_momentum",
            "formula_name": "Dual-Window Bayesian Momentum",
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
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 18)")
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
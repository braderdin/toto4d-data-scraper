#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 21_draw_day_conditional_priors.py
FORMULA NAME : Draw-Day Conditional Priors
DESCRIPTION  : Model Bayesian Berperingkat (Hierarchical Bayes) yang mengasingkan
               dan mengemas kini taburan kebarangkalian posterior bersyarat mengikut
               hari cabutan (Rabu, Sabtu, Ahad, Selasa Khas) dengan saiz taruhan dinamik.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_21_draw_day_conditional_priors.json")

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

DAY_NAMES_MY = {
    0: "Isnin",
    1: "Selasa (Khas)",
    2: "Rabu",
    3: "Khamis",
    4: "Jumaat",
    5: "Sabtu",
    6: "Ahad"
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

def generate_day_conditional_recs(history_draws, target_date_str):
    """
    FORMULA 21: Hierarchical Day-of-Week Bayesian Conditioning
    """
    if not history_draws:
        return [], "DEFENSIVE (RM11)", "Unknown"
        
    target_dt = parse_date(target_date_str)
    target_weekday = target_dt.weekday()
    day_label = DAY_NAMES_MY.get(target_weekday, "Lain-lain")
    
    total_draws = len(history_draws)
    
    # 1. Parameter Global dan Parameter Khusus Hari
    global_pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    day_pos_alphas = [{d: 0.5 for d in range(10)} for _ in range(4)]
    day_pair_alphas = defaultdict(lambda: 0.2)
    day_double_scores = defaultdict(float)
    
    day_draw_count = 0
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.8,
        '3rd': 2.0,
        'special': 1.0,
        'consolation': 0.6
    }
    
    for idx, draw in enumerate(history_draws):
        d_date = parse_date(draw.get('date', ''))
        is_same_day = (d_date.weekday() == target_weekday)
        if is_same_day:
            day_draw_count += 1
            
        recency = 1.0 + (idx / total_draws) * 0.75
        items = [(draw.get('1st_prize'), TIER_WEIGHTS['1st']), (draw.get('2nd_prize'), TIER_WEIGHTS['2nd']), (draw.get('3rd_prize'), TIER_WEIGHTS['3rd'])]
        items += [(x, TIER_WEIGHTS['special']) for x in draw.get('special_prizes', [])]
        items += [(x, TIER_WEIGHTS['consolation']) for x in draw.get('consolation_prizes', [])]
        
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * recency
                for p in range(4):
                    global_pos_alphas[p][int(num_str[p])] += w
                    
                if is_same_day:
                    for p in range(4):
                        day_pos_alphas[p][int(num_str[p])] += w * 1.5
                    day_pair_alphas[(int(num_str[0]), int(num_str[1]))] += w * 0.6
                    day_pair_alphas[(int(num_str[2]), int(num_str[3]))] += w * 0.6
                    
                    cnt = Counter(num_str)
                    for d_val, freq in cnt.items():
                        if freq >= 2:
                            day_double_scores[int(d_val)] += w * freq
                            
    # 2. Bayesian Shrinkage (Penyusutan Bersyarat)
    # 70% Berat Hari + 30% Berat Global
    final_pos_probs = [{} for _ in range(4)]
    for p in range(4):
        tot_global = sum(global_pos_alphas[p].values())
        tot_day = sum(day_pos_alphas[p].values())
        for d in range(10):
            p_glob = global_pos_alphas[p][d] / tot_global
            p_day = day_pos_alphas[p][d] / tot_day
            final_pos_probs[p][d] = (0.70 * p_day) + (0.30 * p_glob)
            
    tot_pair_alpha = sum(day_pair_alphas.values()) or 1.0
    tot_double_w = sum(day_double_scores.values()) or 1.0
    
    # 3. Penentuan Tahap Keyakinan Berdasarkan Kepadatan Sampel Hari (Min 10 Cabutan)
    is_high_confidence = (day_draw_count >= 10) and (target_weekday in (2, 5, 6)) # Rabu, Sabtu, Ahad
    conf_tier = f"HIGH-DAY (RM18) [{day_label}]" if is_high_confidence else f"LOW-DAY (RM11) [{day_label}]"
    
    general_candidates = []
    twin_candidates = []
    
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    
                    pf = day_pair_alphas.get((d0, d1), 0.2) / tot_pair_alpha
                    pb = day_pair_alphas.get((d2, d3), 0.2) / tot_pair_alpha
                    
                    log_p = (
                        math.log(final_pos_probs[0][d0]) +
                        math.log(final_pos_probs[1][d1]) +
                        math.log(final_pos_probs[2][d2]) +
                        math.log(final_pos_probs[3][d3]) +
                        0.35 * math.log(pf) +
                        0.35 * math.log(pb)
                    )
                    general_candidates.append((log_p, num_str))
                    
                    if perms in (12, 6):
                        d_boost = sum(day_double_scores.get(d, 0.0) / tot_double_w for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        yield_log_p = log_p + math.log(24.0 / perms) + 0.45 * math.log(1.0 + d_boost)
                        twin_candidates.append((yield_log_p, num_str))
                        
    general_candidates.sort(key=lambda x: x[0], reverse=True)
    twin_candidates.sort(key=lambda x: x[0], reverse=True)
    
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # STRATEGI RM18: No 1-6 (Direct + iBox = RM12), No 7-12 (iBox Kembar = RM6)
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
        # STRATEGI RM11: No 1-3 (Direct + iBox = RM6), No 4-8 (iBox Sahaja = RM5)
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
                
    return recommendations, conf_tier, day_label

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
    print(f" SIMULASI FORMULA 21: Draw-Day Conditional Priors (Hierarchical Bayes)")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Taruhan Dinamik Bersyarat Hari: RM18.00 (Utama) vs RM11.00 (Khas/Kecil)")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    high_day_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs, conf_tier, day_label = generate_day_conditional_recs(historical_window, target_date)
        
        cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
        if "HIGH" in conf_tier:
            high_day_count += 1
            
        latest_recs_payload = {
            "formula_id": "21_draw_day_conditional_priors",
            "formula_name": "Draw-Day Conditional Priors",
            "target_date": target_date,
            "draw_no": draw_no,
            "day_label": day_label,
            "confidence_tier": conf_tier,
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
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} ({day_label}) | {conf_tier} | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 21)")
    print("=" * 80)
    print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)}")
    print(f"  Sesi Taruhan Utama      : {high_day_count}/{len(testing_draws)} cabutan")
    print(f"  Jumlah Modal Dikeluarkan: RM {total_invested:.2f}")
    print(f"  Jumlah Pulangan Menang  : RM {total_won:.2f}")
    print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
    print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
    print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)} cabutan)")
    print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
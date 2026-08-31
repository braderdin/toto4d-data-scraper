#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 19_twin_box_permutation_stacking.py
FORMULA NAME : Twin-Box Permutation Stacking
DESCRIPTION  : Mengenalpasti famili kembar terkuat (dominant 6-way/12-way clusters)
               dan menyusun pelbagai variasi permutasi famili tersebut secara
               bertingkat (Cross-Rank Stacking) untuk mencetuskan double/triple hits.
STRATEGI BET : Dinamik RM18.00 (High Cluster Density) vs RM11.00 (Low Cluster Density).
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import json
import math
import itertools
from datetime import datetime
from collections import defaultdict, Counter

# ==========================================
# KONFIGURASI DIREKTORI & LALUAN FAIL
# ==========================================
BASE_DIR = "/home/braderdin/toto4d-data-scraper"
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_19_twin_box_permutation_stacking.json")

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

def get_unique_permutations(num_str):
    """Menghasilkan senarai susunan unik bagi sesuatu nombor."""
    return sorted(list(set("".join(p) for p in itertools.permutations(num_str))))

def generate_twin_stacking_recs(history_draws):
    """
    FORMULA 19: Twin-Box Permutation Stacking + Dynamic Bet Sizing
    """
    if not history_draws:
        return [], 0.0, "LOW"
        
    total_draws = len(history_draws)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_cluster_scores = defaultdict(float)
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 3.0,
        '3rd': 2.0,
        'special': 1.2,
        'consolation': 0.8
    }
    
    for idx, draw in enumerate(history_draws):
        rec_f = 1.0 + (idx / total_draws) * 0.8
        items = [(draw.get('1st_prize'), TIER_WEIGHTS['1st']), (draw.get('2nd_prize'), TIER_WEIGHTS['2nd']), (draw.get('3rd_prize'), TIER_WEIGHTS['3rd'])]
        items += [(x, TIER_WEIGHTS['special']) for x in draw.get('special_prizes', [])]
        items += [(x, TIER_WEIGHTS['consolation']) for x in draw.get('consolation_prizes', [])]
        
        for num_str, tier_w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * rec_f
                for pos in range(4):
                    pos_alphas[pos][int(num_str[pos])] += w
                    
                # Skor famili kembar (Box signature sorted)
                box_sig = "".join(sorted(num_str))
                cnt = Counter(num_str)
                if any(v >= 2 for v in cnt.values()):
                    pair_cluster_scores[box_sig] += w
                    
    posterior_probs = [{} for _ in range(4)]
    for pos in range(4):
        tot_a = sum(pos_alphas[pos].values())
        for d in range(10):
            posterior_probs[pos][d] = pos_alphas[pos][d] / tot_a
            
    # Cari famili kembar paling dominan
    sorted_twin_families = sorted(pair_cluster_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Pengiraan Ketumpatan Kluster (Cluster Dominance Score)
    top_cluster_score = sorted_twin_families[0][1] if sorted_twin_families else 0.0
    avg_cluster_score = (sum(v for _, v in sorted_twin_families[:10]) / 10.0) if sorted_twin_families else 1.0
    cluster_dominance = top_cluster_score / max(avg_cluster_score, 1.0)
    
    is_high_confidence = cluster_dominance >= 1.35
    conf_tier = "HIGH (RM18)" if is_high_confidence else "LOW (RM11)"
    
    # Kumpul dan susun permutasi daripada famili teratas
    stacked_direct_pool = []
    stacked_ibox_pool = []
    
    for box_sig, score in sorted_twin_families[:6]:
        all_perms = get_unique_permutations(box_sig)
        # Nilaikan setiap permutasi mengikut kebarangkalian posisi sebenar
        scored_perms = []
        for p_str in all_perms:
            p_score = (
                posterior_probs[0][int(p_str[0])] *
                posterior_probs[1][int(p_str[1])] *
                posterior_probs[2][int(p_str[2])] *
                posterior_probs[3][int(p_str[3])]
            )
            scored_perms.append((p_score, p_str))
            
        scored_perms.sort(key=lambda x: x[0], reverse=True)
        # Ambil permutasi terbaik untuk Direct dan selebihnya untuk iBox Stacking
        for p_sc, p_num in scored_perms:
            if p_num not in stacked_direct_pool:
                stacked_direct_pool.append(p_num)
        if scored_perms and scored_perms[0][1] not in stacked_ibox_pool:
            stacked_ibox_pool.append(scored_perms[0][1])
            
    recommendations = []
    seen = set()
    
    if is_high_confidence:
        # STRATEGI RM18: No 1-6 (Direct + iBox = RM12), No 7-12 (iBox Sahaja = RM6)
        # Susun 6 variasi Direct terbaik
        for num in stacked_direct_pool:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 6:
                break
        # Susun 6 sokongan iBox famili pelengkap
        for box_sig, _ in sorted_twin_families[2:15]:
            best_p = get_unique_permutations(box_sig)[0]
            if best_p not in seen:
                seen.add(best_p)
                recommendations.append({"rank": len(recommendations) + 1, "number": best_p, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 12:
                break
    else:
        # STRATEGI RM11: No 1-3 (Direct + iBox = RM6), No 4-8 (iBox Sahaja = RM5)
        for num in stacked_direct_pool:
            if num not in seen:
                seen.add(num)
                recommendations.append({"rank": len(recommendations) + 1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recommendations) == 3:
                break
        for box_sig, _ in sorted_twin_families[1:10]:
            best_p = get_unique_permutations(box_sig)[0]
            if best_p not in seen:
                seen.add(best_p)
                recommendations.append({"rank": len(recommendations) + 1, "number": best_p, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recommendations) == 8:
                break
                
    return recommendations, cluster_dominance, conf_tier

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
    print(f" SIMULASI FORMULA 19: Twin-Box Permutation Stacking")
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
        recs, cluster_score, conf_tier = generate_twin_stacking_recs(historical_window)
        
        cost_per_draw = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
        if "HIGH" in conf_tier:
            high_conf_count += 1
            
        latest_recs_payload = {
            "formula_id": "19_twin_box_permutation_stacking",
            "formula_name": "Twin-Box Permutation Stacking",
            "target_date": target_date,
            "draw_no": draw_no,
            "confidence_tier": conf_tier,
            "cluster_dominance": round(cluster_score, 4),
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
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | {conf_tier} (C={cluster_score:.2f}) | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 19)")
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
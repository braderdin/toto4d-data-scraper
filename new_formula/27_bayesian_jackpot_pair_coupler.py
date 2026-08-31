#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 27_bayesian_jackpot_pair_coupler.py
FORMULA NAME : Bayesian Jackpot Pair-Coupler
DESCRIPTION  : Mengekstrak output 8 nombor teratas dari Formula 18 dan menyusun
               6 hingga 10 pasangan tiket (Jackpot couplets) bernilai jangkaan
               tertinggi bagi sasaran 4D Jackpot.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_27_bayesian_jackpot_pair_coupler.json")

# ==========================================
# STRUKTUR PEMBAYARAN TOTO 4D JACKPOT (RM2)
# ==========================================
JACKPOT_PAYOUT = {
    '1st_2nd': 2000000.0, # Minimum Jackpot 1
    '1st_3rd': 2000000.0,
    '2nd_3rd': 2000000.0,
    '1st_sp': 100000.0,   # Minimum Jackpot 2
    '2nd_sp': 100000.0,
    '3rd_sp': 100000.0,
    'top3_only': 168.0,   # 3rd Prize Jackpot Category
    'sp_only': 68.0,      # 4th Prize Jackpot Category
    'cs_only': 28.0       # 5th Prize Jackpot Category
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def generate_jackpot_pairs(history_draws):
    """
    FORMULA 27: Bayesian Jackpot Pair-Coupler
    """
    if not history_draws:
        return [], 0.0, "DEFENSIVE (RM12)"
        
    total_draws = len(history_draws)
    short_window_size = 12
    long_window_size = 60
    
    short_history = history_draws[-short_window_size:] if total_draws >= short_window_size else history_draws
    long_history = history_draws[-long_window_size:] if total_draws >= long_window_size else history_draws
    
    # Base prior from long window
    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(4)]
    for draw in long_history:
        for s, w in [(draw.get('1st_prize'), 3.5), (draw.get('2nd_prize'), 2.5), (draw.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_alphas_long[p][int(s[p])] += w
                    
    # Momentum from short window
    pos_alphas_short = [{d: 0.5 for d in range(10)} for _ in range(4)]
    for idx, draw in enumerate(short_history):
        wb = 1.0 + (idx / len(short_history)) * 1.0
        for s, w in [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 3.0), (draw.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_alphas_short[p][int(s[p])] += w * wb

    # Calculate probabilities
    combined_pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        tot_l, tot_s = sum(pos_alphas_long[p].values()), sum(pos_alphas_short[p].values())
        for d in range(10):
            prob = (0.35 * (pos_alphas_long[p][d] / tot_l)) + (0.65 * (pos_alphas_short[p][d] / tot_s))
            combined_pos_probs[p][d] = prob
            if prob > 0: shannon_entropy -= prob * math.log(prob)
            
    # Generate Top Candidates
    candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    p_score = combined_pos_probs[0][d0] * combined_pos_probs[1][d1] * combined_pos_probs[2][d2] * combined_pos_probs[3][d3]
                    candidates.append((p_score, f"{d0}{d1}{d2}{d3}"))
                    
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_8_pool = [c for c in candidates[:8]]
    
    # Generate Pairs
    pairs = list(itertools.combinations(top_8_pool, 2))
    scored_pairs = []
    for (p1_score, num1), (p2_score, num2) in pairs:
        joint_score = p1_score * p2_score
        scored_pairs.append((joint_score, num1, num2))
        
    scored_pairs.sort(key=lambda x: x[0], reverse=True)
    
    is_high_confidence = shannon_entropy < 8.15
    conf_tier = "HIGH-JACKPOT (RM20)" if is_high_confidence else "LOW-JACKPOT (RM12)"
    max_pairs = 10 if is_high_confidence else 6
    
    recommendations = []
    for rank, (_, n1, n2) in enumerate(scored_pairs[:max_pairs], start=1):
        recommendations.append({
            "rank": rank,
            "pair": f"{n1} + {n2}",
            "bet_jackpot_rm": 2
        })
        
    return recommendations, shannon_entropy, conf_tier

def evaluate_jackpot_draw(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]
    
    top3 = {p1, p2, p3} - {''}
    sp_set = set(specials)
    cs_set = set(consolations)
    
    total_winnings = 0.0
    hit_logs = []
    
    for item in recommendations:
        rank = item['rank']
        n1, n2 = item['pair'].split(" + ")
        bet = item['bet_jackpot_rm']
        
        hit_top3 = sum(1 for n in [n1, n2] if n in top3)
        hit_sp = sum(1 for n in [n1, n2] if n in sp_set)
        hit_cs = sum(1 for n in [n1, n2] if n in cs_set)
        
        # Check Jackpot 1 (Two Top 3)
        if hit_top3 == 2:
            win = JACKPOT_PAYOUT['1st_2nd'] * (bet / 2.0)
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({n1}+{n2}) KENA JACKPOT 1 (+RM{win:,.2f})")
        # Check Jackpot 2 (One Top 3 + One SP)
        elif hit_top3 == 1 and hit_sp == 1:
            win = JACKPOT_PAYOUT['1st_sp'] * (bet / 2.0)
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({n1}+{n2}) KENA JACKPOT 2 (+RM{win:,.2f})")
        # Check 3rd Category (One Top 3 only)
        elif hit_top3 == 1 and hit_sp == 0:
            win = JACKPOT_PAYOUT['top3_only'] * (bet / 2.0)
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({n1}+{n2}) KENA J-3rd Prize (+RM{win:.2f})")
        # Check 4th Category (One SP only)
        elif hit_top3 == 0 and hit_sp == 1:
            win = JACKPOT_PAYOUT['sp_only'] * (bet / 2.0)
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({n1}+{n2}) KENA J-4th Prize (+RM{win:.2f})")
        # Check 5th Category (One Consolation only)
        elif hit_top3 == 0 and hit_cs == 1:
            win = JACKPOT_PAYOUT['cs_only'] * (bet / 2.0)
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({n1}+{n2}) KENA J-5th Prize (+RM{win:.2f})")
            
    return total_winnings, hit_logs

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE): return
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    
    split_index = len(draws) // 2
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(" SIMULASI FORMULA 27: Bayesian Jackpot Pair-Coupler")
    print("=" * 80)
    
    total_invested, total_won, hits_count = 0.0, 0.0, 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        historical_window = draws[:split_index + i]
        recs, entropy, tier = generate_jackpot_pairs(historical_window)
        
        cost = sum(item['bet_jackpot_rm'] for item in recs)
        winnings, logs = evaluate_jackpot_draw(recs, current_draw)
        
        total_invested += cost
        total_won += winnings
        net = winnings - cost
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost:8.2f}"
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | {tier} | {status}")
        for log in logs: print(f"     └─ {log}")
            
    print("=" * 80)
    print(f" KEPUTUSAN FORMULA 27: Modal: RM{total_invested:.2f} | Menang: RM{total_won:.2f} | Untung: RM{total_won-total_invested:+.2f}")
    print("=" * 80)

if __name__ == "__main__": main()
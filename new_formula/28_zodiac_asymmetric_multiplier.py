#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 28_zodiac_asymmetric_multiplier.py
FORMULA NAME : Zodiac Asymmetric Multiplier
DESCRIPTION  : Menjana 5 nombor kembar (Twin Regime) digandingkan dengan 2 lambang 
               Zodiak dominan untuk memburu pengganda asimetrik i-Perm Zodiac.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_28_zodiac_asymmetric_multiplier.json")

# ZODIAC INDEX MAP (0-11)
ZODIACS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Boar"]

# ZODIAC I-PERM PAYOUT (Based on RM1 bet)
ZODIAC_IPERM_PAYOUT = {
    '1st_24w': 750.0, '1st_12w': 1500.0, '1st_6w': 3000.0, '1st_4w': 4500.0,
    '2nd_24w': 250.0, '2nd_12w': 500.0,  '2nd_6w': 1000.0, '2nd_4w': 1500.0,
    '3rd_24w': 125.0, '3rd_12w': 250.0,  '3rd_6w': 500.0,  '3rd_4w': 750.0,
    'sp_24w': 38.0,   'sp_12w': 75.0,    'sp_6w': 150.0,   'sp_4w': 225.0,
    'cs_24w': 12.0,   'cs_12w': 25.0,    'cs_6w': 50.0,    'cs_4w': 75.0,
    'any_24w': 3.0,   'any_12w': 5.0,    'any_6w': 10.0,   'any_4w': 15.0
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

def generate_zodiac_recs(history_draws):
    """
    FORMULA 28: Zodiac Twin Regime Hybrid
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    double_scores = defaultdict(float)
    
    # Mock Zodiac Tracker (Simulated transition for backtesting)
    zodiac_counts = defaultdict(float)
    
    for idx, draw in enumerate(history_draws):
        recency = 1.0 + (idx / total_draws) * 0.8
        items = [draw.get('1st_prize'), draw.get('2nd_prize'), draw.get('3rd_prize')]
        for s in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = 1.0 * recency
                cnt = Counter(s)
                for d_val, freq in cnt.items():
                    if freq >= 2: double_scores[int(d_val)] += w * freq
                for p in range(4): pos_alphas[p][int(s[p])] += w
                
        # Simulate previous draw Zodiac pseudo-randomly based on draw number to build Markov transition
        d_no_val = int(str(draw.get('draw_no', '0')).split('-')[0]) if str(draw.get('draw_no', '0')).split('-')[0].isdigit() else idx
        pseudo_zodiac = ZODIACS[d_no_val % 12]
        zodiac_counts[pseudo_zodiac] += recency

    pos_probs = [{} for _ in range(4)]
    for p in range(4):
        ta = sum(pos_alphas[p].values())
        for d in range(10): pos_probs[p][d] = pos_alphas[p][d] / ta
            
    tot_double_score = sum(double_scores.values()) or 1.0
    
    twin_candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    if perms in (12, 6):
                        log_p = math.log(pos_probs[0][d0]) + math.log(pos_probs[1][d1]) + math.log(pos_probs[2][d2]) + math.log(pos_probs[3][d3])
                        db = sum(double_scores.get(d, 0.0) / tot_double_score for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        twin_candidates.append((log_p + 0.5 * math.log(1.0 + db), num_str))
                        
    twin_candidates.sort(key=lambda x: x[0], reverse=True)
    top_zodiacs = sorted(zodiac_counts.items(), key=lambda x: x[1], reverse=True)
    target_zodiacs = [z[0] for z in top_zodiacs[:2]] if top_zodiacs else [ZODIACS[0], ZODIACS[1]]
    
    recommendations = []
    seen = set()
    for _, num in twin_candidates:
        if num not in seen:
            seen.add(num)
            for z in target_zodiacs:
                recommendations.append({
                    "rank": len(seen),
                    "number": num,
                    "zodiac": z,
                    "bet_iperm_rm": 1
                })
        if len(seen) == 5:
            break
            
    return recommendations

def evaluate_zodiac_draw(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]
    
    # Since historical data doesn't have Zodiac, we simulate the winning Zodiac using pseudo-random draw_no
    d_no_val = int(str(actual_draw.get('draw_no', '0')).split('-')[0]) if str(actual_draw.get('draw_no', '0')).split('-')[0].isdigit() else 0
    winning_zodiac = ZODIACS[d_no_val % 12]
    
    total_winnings = 0.0
    hit_logs = []
    
    for item in recommendations:
        rank = item['rank']
        num = item['number']
        bet_zodiac = item['zodiac']
        bet = item['bet_iperm_rm']
        perms = get_permutation_count(num)
        sorted_num = "".join(sorted(num))
        
        is_zodiac_match = (bet_zodiac == winning_zodiac)
        p_key = f"{perms}w"
        
        hit_any_4d = False
        if "".join(sorted(p1)) == sorted_num:
            hit_any_4d = True
            if is_zodiac_match:
                win = ZODIAC_IPERM_PAYOUT[f'1st_{p_key}'] * bet
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-1st Prize (+RM{win:.2f})")
        elif "".join(sorted(p2)) == sorted_num:
            hit_any_4d = True
            if is_zodiac_match:
                win = ZODIAC_IPERM_PAYOUT[f'2nd_{p_key}'] * bet
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-2nd Prize (+RM{win:.2f})")
        elif "".join(sorted(p3)) == sorted_num:
            hit_any_4d = True
            if is_zodiac_match:
                win = ZODIAC_IPERM_PAYOUT[f'3rd_{p_key}'] * bet
                total_winnings += win
                hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-3rd Prize (+RM{win:.2f})")
        else:
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    hit_any_4d = True
                    if is_zodiac_match:
                        win = ZODIAC_IPERM_PAYOUT[f'sp_{p_key}'] * bet
                        total_winnings += win
                        hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-Special (+RM{win:.2f})")
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    hit_any_4d = True
                    if is_zodiac_match:
                        win = ZODIAC_IPERM_PAYOUT[f'cs_{p_key}'] * bet
                        total_winnings += win
                        hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-Consolation (+RM{win:.2f})")
                        
        if hit_any_4d and not is_zodiac_match:
            win = ZODIAC_IPERM_PAYOUT[f'any_{p_key}'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num} {bet_zodiac}) KENA Z-6th Prize (4D Only) (+RM{win:.2f})")
            
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
    print(" SIMULASI FORMULA 28: Zodiac Asymmetric Multiplier")
    print("=" * 80)
    
    total_invested, total_won, hits_count = 0.0, 0.0, 0
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        historical_window = draws[:split_index + i]
        recs = generate_zodiac_recs(historical_window)
        
        cost = sum(item['bet_iperm_rm'] for item in recs)
        winnings, logs = evaluate_zodiac_draw(recs, current_draw)
        
        total_invested += cost
        total_won += winnings
        net = winnings - cost
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost:8.2f}"
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | {status}")
        for log in logs: print(f"     └─ {log}")
            
    print("=" * 80)
    print(f" KEPUTUSAN FORMULA 28: Modal: RM{total_invested:.2f} | Menang: RM{total_won:.2f} | Untung: RM{total_won-total_invested:+.2f}")
    print("=" * 80)

if __name__ == "__main__": main()
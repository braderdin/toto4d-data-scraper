#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 29_fireball_entropy_wildcard.py
FORMULA NAME : Fireball Entropy Wildcard Targeter
DESCRIPTION  : Mengenalpasti kedudukan digit paling stabil, dan menyerahkan 1 digit
               yang paling bervolati tinggi kepada fungsi Wildcard 4D Fireball.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_29_fireball_entropy_wildcard.json")

# 4D FIREBALL PAYOUT (Based on RM1 cover)
FIREBALL_PAYOUT = {
    '1st': 500.0,
    '2nd': 200.0,
    '3rd': 100.0,
    'special': 30.0,
    'consolation': 10.0
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def generate_fireball_recs(history_draws):
    """
    FORMULA 29: Fireball Wildcard Targeting
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    
    for idx, draw in enumerate(history_draws):
        recency = 1.0 + (idx / total_draws) * 0.8
        for s, tier_w in [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 2.8), (draw.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tier_w * recency
                for p in range(4): pos_alphas[p][int(s[p])] += w

    pos_probs = [{} for _ in range(4)]
    pos_entropy = [0.0 for _ in range(4)]
    
    for p in range(4):
        ta = sum(pos_alphas[p].values())
        for d in range(10):
            prob = pos_alphas[p][d] / ta
            pos_probs[p][d] = prob
            if prob > 0: pos_entropy[p] -= prob * math.log(prob)
            
    # Find the most volatile position (Highest Entropy) to be covered by Fireball
    volatile_pos = pos_entropy.index(max(pos_entropy))
    
    candidates = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    probs = [pos_probs[0][d0], pos_probs[1][d1], pos_probs[2][d2], pos_probs[3][d3]]
                    probs[volatile_pos] = 1.0 # Give wildcard a full score
                    score = probs[0] * probs[1] * probs[2] * probs[3]
                    candidates.append((score, f"{d0}{d1}{d2}{d3}"))
                    
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    recommendations = []
    seen = set()
    for _, num in candidates:
        if num not in seen:
            seen.add(num)
            recommendations.append({
                "rank": len(seen),
                "number": num,
                "wildcard_pos": volatile_pos,
                "bet_fireball_rm": 1
            })
        if len(seen) == 10:
            break
            
    return recommendations

def evaluate_fireball_draw(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]
    
    # Simulate Fireball digit pseudo-randomly
    d_no_val = int(str(actual_draw.get('draw_no', '0')).split('-')[0]) if str(actual_draw.get('draw_no', '0')).split('-')[0].isdigit() else 0
    fb_digit = str(d_no_val % 10)
    
    total_winnings = 0.0
    hit_logs = []
    
    for item in recommendations:
        rank = item['rank']
        num = item['number']
        w_pos = item['wildcard_pos']
        bet = item['bet_fireball_rm']
        
        # Construct combinations that match this Fireball logic
        fb_combo = num[:w_pos] + fb_digit + num[w_pos+1:]
        
        if fb_combo == p1:
            win = FIREBALL_PAYOUT['1st'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num}) KENA Fireball 1st Prize (+RM{win:.2f})")
        elif fb_combo == p2:
            win = FIREBALL_PAYOUT['2nd'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num}) KENA Fireball 2nd Prize (+RM{win:.2f})")
        elif fb_combo == p3:
            win = FIREBALL_PAYOUT['3rd'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num}) KENA Fireball 3rd Prize (+RM{win:.2f})")
        elif fb_combo in specials:
            win = FIREBALL_PAYOUT['special'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num}) KENA Fireball Special (+RM{win:.2f})")
        elif fb_combo in consolations:
            win = FIREBALL_PAYOUT['consolation'] * bet
            total_winnings += win
            hit_logs.append(f"Rank {rank:02d} ({num}) KENA Fireball Consolation (+RM{win:.2f})")
            
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
    print(" SIMULASI FORMULA 29: Fireball Entropy Wildcard Targeter")
    print("=" * 80)
    
    total_invested, total_won, hits_count = 0.0, 0.0, 0
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        historical_window = draws[:split_index + i]
        recs = generate_fireball_recs(historical_window)
        
        cost = sum(item['bet_fireball_rm'] for item in recs)
        winnings, logs = evaluate_fireball_draw(recs, current_draw)
        
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
    print(f" KEPUTUSAN FORMULA 29: Modal: RM{total_invested:.2f} | Menang: RM{total_won:.2f} | Untung: RM{total_won-total_invested:+.2f}")
    print("=" * 80)

if __name__ == "__main__": main()
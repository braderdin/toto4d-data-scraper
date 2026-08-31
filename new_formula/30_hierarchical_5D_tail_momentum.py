#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 5D PREDICTION & BACKTESTING ENGINE
MODULE       : 30_hierarchical_5D_tail_momentum.py
FORMULA NAME : Hierarchical 5D Tail-Anchored Bayesian Momentum
DESCRIPTION  : Enjin ramalan Toto 5D piramid 3-peringkat:
               - Peringkat 1: Kunci Ekor 2D (D3, D4) momentum tinggi (Sasaran Hadiah 6).
               - Peringkat 2: Kunci Trigram 3D (D2, D3, D4) Bayesian bersyarat (Hadiah 5).
               - Peringkat 3: Variasi Kepala 2D (D0, D1) dwi-tetingkap (Hadiah 1-4).
STRATEGI BET : 5 Nombor @ RM1.00 = RM5.00 / Cabutan.
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
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_5d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_30_hierarchical_5D_tail_momentum.json")

# ==========================================
# STRUKTUR PEMBAYARAN TOTO 5D (PER RM1 BET)
# ==========================================
PAYOUT_5D = {
    '1st': 15000.0, # Padan 5 digit Hadiah Pertama
    '2nd': 5000.0,  # Padan 5 digit Hadiah Kedua
    '3rd': 3000.0,  # Padan 5 digit Hadiah Ketiga
    '4th': 500.0,   # 4 Digit Terakhir Hadiah Pertama
    '5th': 20.0,    # 3 Digit Terakhir Hadiah Pertama
    '6th': 5.0      # 2 Digit Terakhir Hadiah Pertama
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def generate_hierarchical_5d_recs(history_draws, top_n=5):
    """
    FORMULA 30: 5D Hierarchical Tail-Anchored Bayesian Momentum
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    short_window_size = 12
    long_window_size = 50
    
    short_history = history_draws[-short_window_size:] if total_draws >= short_window_size else history_draws
    long_history = history_draws[-long_window_size:] if total_draws >= long_window_size else history_draws
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.5,
        '3rd': 1.8
    }
    
    # 1. Parameter Posisi Asas (Long-Window Dirichlet Prior: 5 Posisi)
    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(5)]
    for draw in long_history:
        for prize_key, tier_w in [('1st_prize', TIER_WEIGHTS['1st']), ('2nd_prize', TIER_WEIGHTS['2nd']), ('3rd_prize', TIER_WEIGHTS['3rd'])]:
            s = str(draw.get(prize_key, '')).strip()
            if len(s) == 5 and s.isdigit():
                for p in range(5):
                    pos_alphas_long[p][int(s[p])] += tier_w

    # 2. Momentum Ekor & Pasangan (Short-Window Recency: Focus Tail D3, D4)
    pos_alphas_short = [{d: 0.5 for d in range(10)} for _ in range(5)]
    tail_pair_weights = defaultdict(float)    # Pasangan Ekor (D3, D4)
    mid_trigram_weights = defaultdict(float)  # Trigram Tengah-Ekor (D2, D3, D4)
    front_pair_weights = defaultdict(float)   # Pasangan Kepala (D0, D1)
    
    for idx, draw in enumerate(short_history):
        rec_boost = 1.0 + (idx / len(short_history)) * 1.0
        for prize_key, tier_w in [('1st_prize', TIER_WEIGHTS['1st']), ('2nd_prize', TIER_WEIGHTS['2nd']), ('3rd_prize', TIER_WEIGHTS['3rd'])]:
            s = str(draw.get(prize_key, '')).strip()
            if len(s) == 5 and s.isdigit():
                w = tier_w * rec_boost
                d = [int(c) for c in s]
                for p in range(5):
                    pos_alphas_short[p][d[p]] += w
                
                # Hadiah Pertama diberi keutamaan ekor yang lebih tinggi
                tail_multiplier = 2.0 if prize_key == '1st_prize' else 1.0
                tail_pair_weights[(d[3], d[4])] += w * tail_multiplier
                mid_trigram_weights[(d[2], d[3], d[4])] += w * tail_multiplier
                front_pair_weights[(d[0], d[1])] += w * 0.7

    # 3. Gabungan Kebarangkalian Posisi Posterior (35% Long + 65% Short)
    combined_pos_probs = [{} for _ in range(5)]
    for p in range(5):
        tot_l = sum(pos_alphas_long[p].values())
        tot_s = sum(pos_alphas_short[p].values())
        for digit in range(10):
            p_long = pos_alphas_long[p][digit] / tot_l
            p_short = pos_alphas_short[p][digit] / tot_s
            combined_pos_probs[p][digit] = (0.35 * p_long) + (0.65 * p_short)
            
    tot_tail_w = sum(tail_pair_weights.values()) or 1.0
    tot_tri_w = sum(mid_trigram_weights.values()) or 1.0
    tot_front_w = sum(front_pair_weights.values()) or 1.0
    
    # 4. Pengiraan Skor 100,000 Kombinasi 5D (Hierarchical Scoring)
    candidates = []
    
    for d0 in range(10):
        p0 = combined_pos_probs[0][d0]
        for d1 in range(10):
            p1 = combined_pos_probs[1][d1]
            front_score = (front_pair_weights.get((d0, d1), 0.1) / tot_front_w) ** 0.35
            
            for d2 in range(10):
                p2 = combined_pos_probs[2][d2]
                
                for d3 in range(10):
                    p3 = combined_pos_probs[3][d3]
                    for d4 in range(10):
                        p4 = combined_pos_probs[4][d4]
                        
                        tail_score = (tail_pair_weights.get((d3, d4), 0.1) / tot_tail_w) ** 0.55
                        tri_score = (mid_trigram_weights.get((d2, d3, d4), 0.05) / tot_tri_w) ** 0.40
                        
                        # Gabungan Log-Likelihood Berwajaran
                        log_prob = (
                            math.log(p0) + math.log(p1) + math.log(p2) + math.log(p3) + math.log(p4) +
                            math.log(front_score) +
                            math.log(tail_score) +
                            math.log(tri_score)
                        )
                        
                        candidates.append((log_prob, f"{d0}{d1}{d2}{d3}{d4}"))
                        
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 5. Pilih 5 Nombor Terbaik (Top 5 Unik)
    recommendations = []
    seen = set()
    for _, num_str in candidates:
        if num_str not in seen:
            seen.add(num_str)
            recommendations.append({
                "rank": len(recommendations) + 1,
                "number": num_str,
                "tail_2d": num_str[3:],
                "tail_3d": num_str[2:],
                "bet_rm": 1
            })
        if len(recommendations) == top_n:
            break
            
    return recommendations

def evaluate_5d_draw(recommendations, actual_draw):
    """Menilai kemenangan 5D mengikut peraturan rasmi (Hadiah tertinggi sahaja bagi setiap tiket)."""
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    
    total_winnings = 0.0
    hit_logs = []
    
    for item in recommendations:
        rank = item['rank']
        num = str(item['number']).strip()
        bet = item['bet_rm']
        
        if len(num) != 5:
            continue
            
        win = 0.0
        log_msg = ""
        
        # 1. Hadiah Pertama (Padan 5 Digit Penuh)[cite: 1]
        if len(p1) == 5 and num == p1:
            win = PAYOUT_5D['1st'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 1st Prize (+RM{win:,.2f})[cite: 1]"
        # 2. Hadiah Kedua (Padan 5 Digit Penuh)[cite: 1]
        elif len(p2) == 5 and num == p2:
            win = PAYOUT_5D['2nd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 2nd Prize (+RM{win:,.2f})[cite: 1]"
        # 3. Hadiah Ketiga (Padan 5 Digit Penuh)[cite: 1]
        elif len(p3) == 5 and num == p3:
            win = PAYOUT_5D['3rd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 3rd Prize (+RM{win:,.2f})[cite: 1]"
        # 4. Hadiah Ke-4 (Padan 4 Digit Terakhir Hadiah 1)[cite: 1]
        elif len(p1) == 5 and num[1:] == p1[1:]:
            win = PAYOUT_5D['4th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 4th Prize (Ekor 4D: {p1[1:]}) (+RM{win:.2f})[cite: 1]"
        # 5. Hadiah Ke-5 (Padan 3 Digit Terakhir Hadiah 1)[cite: 1]
        elif len(p1) == 5 and num[2:] == p1[2:]:
            win = PAYOUT_5D['5th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 5th Prize (Ekor 3D: {p1[2:]}) (+RM{win:.2f})[cite: 1]"
        # 6. Hadiah Ke-6 (Padan 2 Digit Terakhir Hadiah 1)[cite: 1]
        elif len(p1) == 5 and num[3:] == p1[3:]:
            win = PAYOUT_5D['6th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 6th Prize (Ekor 2D: {p1[3:]}) (+RM{win:.2f})[cite: 1]"
            
        if win > 0:
            total_winnings += win
            hit_logs.append(log_msg)
            
    return total_winnings, hit_logs

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data 5D tidak dijumpai di: {DATA_FILE}")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    # Susun dari tarikh lama -> baru
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 20:
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 30: Hierarchical 5D Tail-Anchored Bayesian Momentum")
    print(f" Jumlah Data: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Strategi Taruhan: 5 Nombor @ RM1.00 = RM5.00 / Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_hierarchical_5d_recs(historical_window, top_n=5)
        
        cost_per_draw = sum(item['bet_rm'] for item in recs)
        winnings, hit_logs = evaluate_5d_draw(recs, current_draw)
        
        total_invested += cost_per_draw
        total_won += winnings
        net_draw = winnings - cost_per_draw
        
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net_draw:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost_per_draw:8.2f}"
            
        latest_recs_payload = {
            "formula_id": "30_hierarchical_5D_tail_momentum",
            "formula_name": "Hierarchical 5D Tail-Anchored Bayesian Momentum",
            "target_date": target_date,
            "draw_no": draw_no,
            "budget_total_rm": cost_per_draw,
            "recommendations": recs
        }
        
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | Draw: {draw_no} | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN TOTO 5D (FORMULA 30)")
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
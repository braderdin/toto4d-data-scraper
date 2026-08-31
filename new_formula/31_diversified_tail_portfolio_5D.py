#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 5D PREDICTION & BACKTESTING ENGINE
MODULE       : 31_diversified_tail_portfolio_5D.py
FORMULA NAME : Diversified Tail Portfolio & Multi-Tier Bayesian 5D
DESCRIPTION  : Model portfolio Toto 5D yang mempelbagaikan 5 ekor 2D (D3, D4)
               berasingan untuk memaksimumkan peluang menang Hadiah Ke-6 (RM5)
               dan Ke-5 (RM20), disokong momentum Bayesian kepala (D0, D1).
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_31_diversified_tail_portfolio_5D.json")

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

def generate_diversified_5d_portfolio(history_draws, top_n=5):
    """
    FORMULA 31: Diversified 5-Tail Bayesian Portfolio
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    short_window_size = 15
    long_window_size = 60
    
    short_history = history_draws[-short_window_size:] if total_draws >= short_window_size else history_draws
    long_history = history_draws[-long_window_size:] if total_draws >= long_window_size else history_draws
    
    TIER_WEIGHTS = {
        '1st': 4.5,
        '2nd': 2.5,
        '3rd': 1.8
    }
    
    # 1. Analisis Matriks Kedudukan Posisi Kepala (D0, D1) & Tengah (D2)
    pos_weights = [defaultdict(float) for _ in range(5)]
    for idx, draw in enumerate(long_history):
        recency = 1.0 + (idx / len(long_history)) * 0.75
        for prize_key, tier_w in [('1st_prize', TIER_WEIGHTS['1st']), ('2nd_prize', TIER_WEIGHTS['2nd']), ('3rd_prize', TIER_WEIGHTS['3rd'])]:
            s = str(draw.get(prize_key, '')).strip()
            if len(s) == 5 and s.isdigit():
                w = tier_w * recency
                for p in range(5):
                    pos_weights[p][int(s[p])] += w
                    
    pos_probs = [{} for _ in range(5)]
    for p in range(5):
        tot_w = sum(pos_weights[p].values()) or 1.0
        for d in range(10):
            pos_probs[p][d] = (pos_weights[p][d] + 0.1) / (tot_w + 1.0)

    # 2. Analisis Momentum Ekor 2D (D3, D4) & Trigram (D2, D3, D4) dari Hadiah Pertama
    tail_2d_scores = defaultdict(float)
    trigram_conditioned = defaultdict(lambda: defaultdict(float))
    
    for idx, draw in enumerate(short_history):
        # Hadiah Pertama diberi keutamaan mutlak untuk ekor
        decay_factor = math.exp(-0.06 * (len(short_history) - 1 - idx))
        
        # 1st prize tail analysis
        p1 = str(draw.get('1st_prize', '')).strip()
        if len(p1) == 5 and p1.isdigit():
            d = [int(c) for c in p1]
            tail_pair = (d[3], d[4])
            tail_2d_scores[tail_pair] += 4.0 * decay_factor
            trigram_conditioned[tail_pair][d[2]] += 4.0 * decay_factor
            
        # Top 2 & 3 tails as secondary signals
        for pk in ('2nd_prize', '3rd_prize'):
            ps = str(draw.get(pk, '')).strip()
            if len(ps) == 5 and ps.isdigit():
                d = [int(c) for c in ps]
                tail_pair = (d[3], d[4])
                tail_2d_scores[tail_pair] += 1.5 * decay_factor
                trigram_conditioned[tail_pair][d[2]] += 1.5 * decay_factor

    # Saring 5 Ekor 2D Paling Panas yang Unik
    sorted_tails = sorted(tail_2d_scores.items(), key=lambda x: x[1], reverse=True)
    selected_5_tails = [t[0] for t in sorted_tails[:top_n]]
    
    # Lengkapkan sekiranya sampel awal kurang daripada 5
    d_idx = 0
    while len(selected_5_tails) < top_n:
        fallback_tail = (d_idx % 10, (d_idx * 3) % 10)
        if fallback_tail not in selected_5_tails:
            selected_5_tails.append(fallback_tail)
        d_idx += 1

    # 3. Penjanaan Pasangan Kepala (D0, D1) Terbaik
    head_candidates = []
    for d0 in range(10):
        for d1 in range(10):
            score_head = pos_probs[0][d0] * pos_probs[1][d1]
            head_candidates.append((score_head, d0, d1))
    head_candidates.sort(key=lambda x: x[0], reverse=True)

    # 4. Bina 5 Tiket dengan 5 Ekor Berbeza (Portfolio Diversification)
    recommendations = []
    
    for rank, tail_pair in enumerate(selected_5_tails, start=1):
        d3, d4 = tail_pair
        
        # Tentukan D2 terbaik bagi ekor ini
        mid_options = trigram_conditioned[tail_pair]
        if mid_options:
            best_d2 = max(mid_options.items(), key=lambda x: x[1])[0]
        else:
            best_d2 = max(pos_probs[2].items(), key=lambda x: x[1])[0]
            
        # Pilih pasangan kepala (D0, D1) mengikut giliran kualiti
        _, best_d0, best_d1 = head_candidates[(rank - 1) % len(head_candidates)]
        
        full_5d_number = f"{best_d0}{best_d1}{best_d2}{d3}{d4}"
        
        recommendations.append({
            "rank": rank,
            "number": full_5d_number,
            "tail_2d": f"{d3}{d4}",
            "tail_3d": f"{best_d2}{d3}{d4}",
            "bet_rm": 1
        })
        
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
        
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 20:
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(" SIMULASI FORMULA 31: Diversified Tail Portfolio & Multi-Tier Bayesian 5D")
    print(f" Jumlah Data: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(" Strategi Taruhan: 5 Nombor dengan 5 Ekor Unik @ RM1.00 = RM5.00 / Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_diversified_5d_portfolio(historical_window, top_n=5)
        
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
            "formula_id": "31_diversified_tail_portfolio_5D",
            "formula_name": "Diversified Tail Portfolio & Multi-Tier Bayesian 5D",
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
    print(" KEPUTUSAN PRESTASI PELABURAN TOTO 5D (FORMULA 31)")
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
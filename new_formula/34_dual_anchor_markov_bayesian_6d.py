#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 6D PREDICTION & BACKTESTING ENGINE
MODULE       : 34_dual_anchor_markov_bayesian_6d.py
FORMULA NAME : Dual-Anchor Markov-Bayesian Beam Hunter (6D)
DESCRIPTION  : Model Bayesian 6D berasaskan pengoptimuman dwi-sauh (Head & Tail):
               - Menganalisis kebarangkalian kedudukan 6 posisi (D0 hingga D5).
               - Membina rantai peralihan Markov 5 peringkat (T01 -> T12 -> T23 -> T34 -> T45).
               - Memaksimumkan nilai jangkaan (EV) untuk padanan Hadiah Depan & Hadiah Belakang.
STRATEGI BET : 3 Nombor @ RM1.00 = RM3.00 / Cabutan.
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
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_6d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_34_dual_anchor_markov_bayesian_6d.json")

# ==========================================
# STRUKTUR PEMBAYARAN TOTO 6D (PER RM1 BET)
# ==========================================
PAYOUT_6D = {
    '1st': 100000.0, # 6 Digit Penuh
    '2nd': 3000.0,   # 5 Digit Awal / 5 Digit Akhir
    '3rd': 300.0,    # 4 Digit Awal / 4 Digit Akhir
    '4th': 30.0,     # 3 Digit Awal / 3 Digit Akhir
    '5th': 4.0       # 2 Digit Awal / 2 Digit Akhir
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def generate_6d_recommendations(history_draws, top_n=3):
    """
    FORMULA 34: Dual-Anchor Markov-Bayesian Beam Search
    """
    if not history_draws:
        return []

    total_draws = len(history_draws)
    
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(6)]
    transition_alphas = [defaultdict(lambda: 0.2) for _ in range(5)] # T01, T12, T23, T34, T45
    
    head_2d_weights = defaultdict(float) # D0, D1
    head_3d_weights = defaultdict(float) # D0, D1, D2
    tail_2d_weights = defaultdict(float) # D4, D5
    tail_3d_weights = defaultdict(float) # D3, D4, D5
    
    for idx, draw in enumerate(history_draws):
        # Pembobotan susutan masa eksponen
        recency = math.exp(-0.02 * (total_draws - 1 - idx))
        
        p1 = str(draw.get('1st_prize', '')).strip()
        if len(p1) == 6 and p1.isdigit():
            d = [int(c) for c in p1]
            
            for p in range(6):
                pos_alphas[p][d[p]] += recency
                
            for t in range(5):
                transition_alphas[t][(d[t], d[t+1])] += recency
                
            head_2d_weights[(d[0], d[1])] += recency * 2.0
            head_3d_weights[(d[0], d[1], d[2])] += recency * 2.5
            tail_2d_weights[(d[4], d[5])] += recency * 2.0
            tail_3d_weights[(d[3], d[4], d[5])] += recency * 2.5

    # 1. Kebarangkalian Posisi Posterior
    pos_probs = [{} for _ in range(6)]
    for p in range(6):
        tot_p = sum(pos_alphas[p].values())
        for digit in range(10):
            pos_probs[p][digit] = pos_alphas[p][digit] / tot_p

    # 2. Kebarangkalian Peralihan Rantai
    trans_probs = [{} for _ in range(5)]
    for t in range(5):
        tot_t = sum(transition_alphas[t].values()) or 1.0
        for pair, val in transition_alphas[t].items():
            trans_probs[t][pair] = (val + 0.05) / (tot_t + 0.5)

    tot_h2 = sum(head_2d_weights.values()) or 1.0
    tot_h3 = sum(head_3d_weights.values()) or 1.0
    tot_t2 = sum(tail_2d_weights.values()) or 1.0
    tot_t3 = sum(tail_3d_weights.values()) or 1.0

# 3. Beam Search 6 Posisi (Pencarian Ruang 1 Juta Kombinasi Berkecekapan Tinggi)
    beam = [(math.log(pos_probs[0][d0]), str(d0)) for d0 in range(10)]
    
    # Kembangkan rantai digit demi digit
    for step in range(1, 6):
        new_beam = []
        for current_score, path_str in beam:
            prev_digit = int(path_str[-1])
            for next_digit in range(10):
                p_next = pos_probs[step][next_digit]
                t_trans = trans_probs[step-1].get((prev_digit, next_digit), 0.001)
                
                step_score = current_score + math.log(p_next) + 0.35 * math.log(t_trans)
                new_beam.append((step_score, path_str + str(next_digit)))
                
        # Kekalkan calon terbaik (Beam Pruning)
        new_beam.sort(key=lambda x: x[0], reverse=True)
        beam = new_beam[:250]

# 4. Penilaian Akhir Bersama Sauh Depan & Sauh Belakang
    scored_candidates = []
    for base_score, num_str in beam:
        d = [int(c) for c in num_str]
        d0, d1, d2, d3, d4, d5 = d[0], d[1], d[2], d[3], d[4], d[5]
        
        h2_boost = (head_2d_weights.get((d0, d1), 0.01) / tot_h2) ** 0.40
        h3_boost = (head_3d_weights.get((d0, d1, d2), 0.005) / tot_h3) ** 0.35
        t2_boost = (tail_2d_weights.get((d4, d5), 0.01) / tot_t2) ** 0.40
        t3_boost = (tail_3d_weights.get((d3, d4, d5), 0.005) / tot_t3) ** 0.35
        
        final_log_score = (
            base_score +
            math.log(h2_boost) +
            math.log(h3_boost) +
            math.log(t2_boost) +
            math.log(t3_boost)
        )
        scored_candidates.append((final_log_score, num_str, f"{d0}{d1}", f"{d4}{d5}"))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    # 5. Saring Top 3 Calon Berbeza
    recommendations = []
    seen = set()
    for _, num_str, h2, t2 in scored_candidates:
        if num_str not in seen:
            seen.add(num_str)
            recommendations.append({
                "rank": len(recommendations) + 1,
                "number": num_str,
                "head_2d": h2,
                "tail_2d": t2,
                "bet_rm": 1
            })
        if len(recommendations) == top_n:
            break

    return recommendations

def evaluate_6d_draw(recommendations, actual_draw):
    """
    Menilai kemenangan 6D mengikut peraturan rasmi (Hadiah tertinggi bagi setiap tiket).
    """
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    
    total_winnings = 0.0
    hit_logs = []
    
    if len(p1) != 6 or not p1.isdigit():
        return 0.0, []
        
    for item in recommendations:
        rank = item['rank']
        num = str(item['number']).strip()
        bet = item['bet_rm']
        
        if len(num) != 6:
            continue
            
        win = 0.0
        log_msg = ""
        
        # 1. Hadiah Pertama: 6 Digit Tepat
        if num == p1:
            win = PAYOUT_6D['1st'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 1st Prize (+RM{win:,.2f})"
        # 2. Hadiah Kedua: 5 Digit Pertama ATAU 5 Digit Terakhir
        elif num[:5] == p1[:5]:
            win = PAYOUT_6D['2nd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 2nd Prize (Head-5: {p1[:5]}) (+RM{win:,.2f})"
        elif num[1:] == p1[1:]:
            win = PAYOUT_6D['2nd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 2nd Prize (Tail-5: {p1[1:]}) (+RM{win:,.2f})"
        # 3. Hadiah Ketiga: 4 Digit Pertama ATAU 4 Digit Terakhir
        elif num[:4] == p1[:4]:
            win = PAYOUT_6D['3rd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 3rd Prize (Head-4: {p1[:4]}) (+RM{win:.2f})"
        elif num[2:] == p1[2:]:
            win = PAYOUT_6D['3rd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 3rd Prize (Tail-4: {p1[2:]}) (+RM{win:.2f})"
        # 4. Hadiah Ke-4: 3 Digit Pertama ATAU 3 Digit Terakhir
        elif num[:3] == p1[:3]:
            win = PAYOUT_6D['4th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 4th Prize (Head-3: {p1[:3]}) (+RM{win:.2f})"
        elif num[3:] == p1[3:]:
            win = PAYOUT_6D['4th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 4th Prize (Tail-3: {p1[3:]}) (+RM{win:.2f})"
        # 5. Hadiah Ke-5: 2 Digit Pertama ATAU 2 Digit Terakhir
        elif num[:2] == p1[:2]:
            win = PAYOUT_6D['5th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 5th Prize (Head-2: {p1[:2]}) (+RM{win:.2f})"
        elif num[4:] == p1[4:]:
            win = PAYOUT_6D['5th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 5th Prize (Tail-2: {p1[4:]}) (+RM{win:.2f})"
            
        if win > 0:
            total_winnings += win
            hit_logs.append(log_msg)
            
    return total_winnings, hit_logs

def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data 6D tidak dijumpai di: {DATA_FILE}")
        return
        
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    # Susun dari tarikh lama -> baru
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 30:
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    # Pecahan: 1 Tahun Latihan (~50%) | 1 Tahun Ujian Terkini (~50%)
    split_index = int(total_records * 0.50)
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(" SIMULASI FORMULA 34: Dual-Anchor Markov-Bayesian Beam Hunter (6D)")
    print(f" Jumlah Data Sejarah    : {total_records} sesi cabutan (2 Tahun)")
    print(f" Fasa Latihan (1 Tahun) : {len(training_draws)} sesi ({training_draws[0].get('date')} -> {training_draws[-1].get('date')})")
    print(f" Fasa Ujian (1 Tahun)   : {len(testing_draws)} sesi ({testing_draws[0].get('date')} -> {testing_draws[-1].get('date')})")
    print(" Strategi Taruhan       : 3 Nombor @ RM1.00 = RM3.00 / Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_6d_recommendations(historical_window, top_n=3)
        
        cost_per_draw = sum(item['bet_rm'] for item in recs)
        winnings, hit_logs = evaluate_6d_draw(recs, current_draw)
        
        total_invested += cost_per_draw
        total_won += winnings
        net_draw = winnings - cost_per_draw
        
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net_draw:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost_per_draw:8.2f}"
            
        latest_recs_payload = {
            "formula_id": "34_dual_anchor_markov_bayesian_6d",
            "formula_name": "Dual-Anchor Markov-Bayesian Beam Hunter (6D)",
            "target_date": target_date,
            "draw_no": draw_no,
            "budget_total_rm": cost_per_draw,
            "recommendations": recs
        }
        
        print(f"[{i+1:03d}/{len(testing_draws)}] Tarikh: {target_date} | Draw: {draw_no} | {status}")
        for log in hit_logs:
            print(f"      └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN TOTO 6D (FORMULA 34)")
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
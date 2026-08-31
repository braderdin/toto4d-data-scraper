#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 5D PREDICTION & BACKTESTING ENGINE
MODULE       : 32_deep_warmup_5d_bayesian_hunter.py
FORMULA NAME : Deep-Warmup Bayesian 1st-Prize Tail Transition Hunter (5D)
DESCRIPTION  : Model Bayesian 5D berasaskan latihan mendalam 1.5 tahun:
               - Memberikan pemberat tinggi kepada Hadiah Pertama (asas hadiah ekor 2D/3D/4D).
               - Membina rantai kebarangkalian peralihan digit (D0 -> D1 -> D2 -> D3 -> D4).
               - Menjana 5 nombor berbeza bernilai jangkaan (EV) tertinggi.
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_32_deep_warmup_5d_bayesian_hunter.json")

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

def generate_deep_warmup_5d_recs(history_draws, top_n=5):
    """
    FORMULA 32: Deep Warmup 1st-Prize Tail Transition Hunter
    """
    if not history_draws:
        return []
        
    total_draws = len(history_draws)
    
    # Pemberat: Hadiah 1 diberi keutamaan mutlak kerana menentukan hadiah 4th, 5th, 6th
    TIER_WEIGHTS = {
        '1st_prize': 6.0,
        '2nd_prize': 1.5,
        '3rd_prize': 1.0
    }
    
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(5)]
    transition_alphas = [defaultdict(lambda: 0.2) for _ in range(4)]  # T01, T12, T23, T34
    tail_2d_weights = defaultdict(float)                              # Ekor 2D (D3, D4)
    tail_3d_weights = defaultdict(float)                              # Ekor 3D (D2, D3, D4)
    
    for idx, draw in enumerate(history_draws):
        # Pembobotan susutan masa eksponen
        recency = 1.0 + (idx / total_draws) * 1.2
        
        for prize_key, tier_w in TIER_WEIGHTS.items():
            s = str(draw.get(prize_key, '')).strip()
            if len(s) == 5 and s.isdigit():
                w = tier_w * recency
                d = [int(c) for c in s]
                
                for p in range(5):
                    pos_alphas[p][d[p]] += w
                    
                for t in range(4):
                    transition_alphas[t][(d[t], d[t+1])] += w
                    
                if prize_key == '1st_prize':
                    tail_2d_weights[(d[3], d[4])] += w * 2.0
                    tail_3d_weights[(d[2], d[3], d[4])] += w * 2.5

    # 1. Kira Kebarangkalian Posisi Posterior
    pos_probs = [{} for _ in range(5)]
    for p in range(5):
        tot_p = sum(pos_alphas[p].values())
        for digit in range(10):
            pos_probs[p][digit] = pos_alphas[p][digit] / tot_p

    # 2. Kira Kebarangkalian Peralihan Rantai (Markov-Bayesian Chains)
    trans_probs = [{} for _ in range(4)]
    for t in range(4):
        tot_t = sum(transition_alphas[t].values()) or 1.0
        for pair, val in transition_alphas[t].items():
            trans_probs[t][pair] = (val + 0.05) / (tot_t + 0.5)

    tot_tail_2d = sum(tail_2d_weights.values()) or 1.0
    tot_tail_3d = sum(tail_3d_weights.values()) or 1.0

    # 3. Pengiraan Log-Posterior Bersama untuk Semua 100,000 Kombinasi
    candidates = []
    
    for d0 in range(10):
        p0 = pos_probs[0][d0]
        for d1 in range(10):
            p1 = pos_probs[1][d1]
            t01 = trans_probs[0].get((d0, d1), 0.001)
            
            for d2 in range(10):
                p2 = pos_probs[2][d2]
                t12 = trans_probs[1].get((d1, d2), 0.001)
                
                for d3 in range(10):
                    p3 = pos_probs[3][d3]
                    t23 = trans_probs[2].get((d2, d3), 0.001)
                    
                    for d4 in range(10):
                        p4 = pos_probs[4][d4]
                        t34 = trans_probs[3].get((d3, d4), 0.001)
                        
                        tail_2d_boost = (tail_2d_weights.get((d3, d4), 0.01) / tot_tail_2d) ** 0.45
                        tail_3d_boost = (tail_3d_weights.get((d2, d3, d4), 0.005) / tot_tail_3d) ** 0.40
                        
                        log_prob = (
                            math.log(p0) + math.log(p1) + math.log(p2) + math.log(p3) + math.log(p4) +
                            0.4 * (math.log(t01) + math.log(t12) + math.log(t23) + math.log(t34)) +
                            math.log(tail_2d_boost) +
                            math.log(tail_3d_boost)
                        )
                        
                        candidates.append((log_prob, f"{d0}{d1}{d2}{d3}{d4}", f"{d3}{d4}"))

    candidates.sort(key=lambda x: x[0], reverse=True)

    # 4. Pilih 5 Nombor Terbaik dengan Memastikan Ekor 2D Dipelbagaikan
    recommendations = []
    seen_numbers = set()
    seen_tails = set()
    
    # Pusingan 1: Cari calon dengan ekor 2D berbeza
    for _, num_str, tail_2d in candidates:
        if num_str not in seen_numbers and tail_2d not in seen_tails:
            seen_numbers.add(num_str)
            seen_tails.add(tail_2d)
            recommendations.append({
                "rank": len(recommendations) + 1,
                "number": num_str,
                "tail_2d": tail_2d,
                "tail_3d": num_str[2:],
                "bet_rm": 1
            })
        if len(recommendations) == top_n:
            break
            
    # Pusingan 2: Penuhkan baki sekiranya calon belum mencukupi 5
    if len(recommendations) < top_n:
        for _, num_str, tail_2d in candidates:
            if num_str not in seen_numbers:
                seen_numbers.add(num_str)
                recommendations.append({
                    "rank": len(recommendations) + 1,
                    "number": num_str,
                    "tail_2d": tail_2d,
                    "tail_3d": num_str[2:],
                    "bet_rm": 1
                })
            if len(recommendations) == top_n:
                break
                
    return recommendations

def evaluate_5d_draw(recommendations, actual_draw):
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
        
        # Hadiah Pertama (Padan 5 Digit Penuh)[cite: 1]
        if len(p1) == 5 and num == p1:
            win = PAYOUT_5D['1st'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 1st Prize (+RM{win:,.2f})[cite: 1]"
        # Hadiah Kedua (Padan 5 Digit Penuh)[cite: 1]
        elif len(p2) == 5 and num == p2:
            win = PAYOUT_5D['2nd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 2nd Prize (+RM{win:,.2f})[cite: 1]"
        # Hadiah Ketiga (Padan 5 Digit Penuh)[cite: 1]
        elif len(p3) == 5 and num == p3:
            win = PAYOUT_5D['3rd'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 3rd Prize (+RM{win:,.2f})[cite: 1]"
        # Hadiah Ke-4 (Padan 4 Digit Terakhir Hadiah 1)[cite: 1]
        elif len(p1) == 5 and num[1:] == p1[1:]:
            win = PAYOUT_5D['4th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 4th Prize (Ekor 4D: {p1[1:]}) (+RM{win:.2f})[cite: 1]"
        # Hadiah Ke-5 (Padan 3 Digit Terakhir Hadiah 1)[cite: 1]
        elif len(p1) == 5 and num[2:] == p1[2:]:
            win = PAYOUT_5D['5th'] * bet
            log_msg = f"Rank {rank:02d} ({num}) KENA 5th Prize (Ekor 3D: {p1[2:]}) (+RM{win:.2f})[cite: 1]"
        # Hadiah Ke-6 (Padan 2 Digit Terakhir Hadiah 1)[cite: 1]
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
    
    if total_records < 30:
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod).")
        return
        
    # Pecahan: 1 Tahun 6 Bulan Latihan (~75%) | 6 Bulan Ujian Terkini (~25%)
    split_index = int(total_records * 0.75)
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(" SIMULASI FORMULA 32: Deep-Warmup Bayesian 1st-Prize Tail Transition Hunter (5D)")
    print(f" Jumlah Rekod Sejarah: {total_records} sesi cabutan (2 Tahun)")
    print(f" Fasa Latihan (1.5 Tahun): {len(training_draws)} sesi ({training_draws[0].get('date')} -> {training_draws[-1].get('date')})")
    print(f" Fasa Ujian (6 Bulan Terkini): {len(testing_draws)} sesi ({testing_draws[0].get('date')} -> {testing_draws[-1].get('date')})")
    print(" Strategi Taruhan: 5 Nombor @ RM1.00 = RM5.00 / Cabutan")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_deep_warmup_5d_recs(historical_window, top_n=5)
        
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
            "formula_id": "32_deep_warmup_5d_bayesian_hunter",
            "formula_name": "Deep-Warmup Bayesian 1st-Prize Tail Transition Hunter",
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
    print(" KEPUTUSAN PRESTASI PELABURAN TOTO 5D (FORMULA 32)")
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
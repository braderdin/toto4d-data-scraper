#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 07_top3_mirror_pairing.py
FORMULA NAME : Top 3 Mirror Synergy
DESCRIPTION  : Menganalisis frekuensi gandingan 2-digit (co-occurrence pairs)
               daripada kelompok 3 Hadiah Utama dan menerapkan penjelmaan pantulan
               simetri modular m(d) = (10 - d) mod 10.
AUTHO/USER   : braderdin
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
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_07_top3_mirror_pairing.json")

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
    """Menukar rentetan tarikh kepada objek datetime."""
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass
    return datetime.min

def get_permutation_count(num_str):
    """Mengira bilangan permutasi unik (iBox divisor)."""
    counts = Counter(num_str).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def get_mirror_digit(d):
    """Fungsi pantulan simetri modular: (10 - d) % 10."""
    return (10 - int(d)) % 10

def generate_mirror_pairing_recommendations(history_draws, top_n=10):
    """
    FORMULA 07: Top 3 Mirror Synergy
    Menjana 10 nombor berasaskan korelasi pasangan 2-digit & pantulan simetri.
    """
    if not history_draws:
        return []
        
    pair_front_counts = defaultdict(float)  # Posisi 0-1
    pair_back_counts = defaultdict(float)   # Posisi 2-3
    pair_any_counts = defaultdict(float)    # Mana-mana 2 digit
    
    TIER_WEIGHTS = {
        '1st': 4.0,
        '2nd': 2.5,
        '3rd': 2.0,
        'special': 0.8,
        'consolation': 0.5
    }
    
    for draw in history_draws:
        items = []
        if draw.get('1st_prize'): items.append((draw['1st_prize'], TIER_WEIGHTS['1st']))
        if draw.get('2nd_prize'): items.append((draw['2nd_prize'], TIER_WEIGHTS['2nd']))
        if draw.get('3rd_prize'): items.append((draw['3rd_prize'], TIER_WEIGHTS['3rd']))
        for sp in draw.get('special_prizes', []): items.append((sp, TIER_WEIGHTS['special']))
        for cs in draw.get('consolation_prizes', []): items.append((cs, TIER_WEIGHTS['consolation']))
        
        for num_str, w in items:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                d = [int(c) for c in num_str]
                pair_front_counts[(d[0], d[1])] += w
                pair_back_counts[(d[2], d[3])] += w
                
                # Kira pasangan tidak berurutan
                for p_a in range(4):
                    for p_b in range(p_a + 1, 4):
                        sorted_pair = tuple(sorted([d[p_a], d[p_b]]))
                        pair_any_counts[sorted_pair] += w
                        
    # Ambil rujukan 3 hadiah utama cabutan terkini untuk operasi pantulan
    last_draw = history_draws[-1]
    top3_seeds = []
    for k in ('1st_prize', '2nd_prize', '3rd_prize'):
        val = str(last_draw.get(k, '')).strip()
        if len(val) == 4 and val.isdigit():
            top3_seeds.append(val)
            
    if not top3_seeds:
        top3_seeds = ["1234", "5678", "9012"]
        
    candidates = []
    
    # 1. Transformasi Pantulan Simetri Terus (Direct Mirror of Top 3)
    for seed in top3_seeds:
        mirrored = "".join(str(get_mirror_digit(c)) for c in seed)
        candidates.append((100.0, mirrored))
        
        # Pantulan separuh (Front mirrored, Back static / sebaliknya)
        m_front = f"{get_mirror_digit(seed[0])}{get_mirror_digit(seed[1])}{seed[2]}{seed[3]}"
        m_back = f"{seed[0]}{seed[1]}{get_mirror_digit(seed[2])}{get_mirror_digit(seed[3])}"
        candidates.append((90.0, m_front))
        candidates.append((90.0, m_back))
        
    # 2. Sintesis Gandingan Pasangan Hadapan & Belakang Tertinggi
    total_f = sum(pair_front_counts.values()) or 1.0
    total_b = sum(pair_back_counts.values()) or 1.0
    
    for (f0, f1), f_w in pair_front_counts.items():
        for (b0, b1), b_w in pair_back_counts.items():
            # Skor berdasarkan sinergi pasangan + bonus simetri
            f_prob = f_w / total_f
            b_prob = b_w / total_b
            
            # Semak sama ada b0, b1 adalah pantulan simetri kepada f0, f1
            sym_bonus = 1.35 if (b0 == get_mirror_digit(f1) and b1 == get_mirror_digit(f0)) else 1.0
            
            score = (f_prob * b_prob * 1000.0) * sym_bonus
            candidates.append((score, f"{f0}{f1}{b0}{b1}"))
            
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    top_numbers = []
    seen = set()
    for _, num in candidates:
        if num not in seen:
            seen.add(num)
            top_numbers.append(num)
        if len(top_numbers) == top_n:
            break
            
    recommendations = []
    for rank, num in enumerate(top_numbers, start=1):
        if rank <= 3:
            recommendations.append({
                "rank": rank,
                "number": num,
                "bet_direct_rm": 1,
                "bet_ibox_rm": 1
            })
        else:
            recommendations.append({
                "rank": rank,
                "number": num,
                "bet_direct_rm": 0,
                "bet_ibox_rm": 1
            })
            
    return recommendations

def evaluate_draw_results(recommendations, actual_draw):
    """Menilai kemenangan Direct dan iBox berdasarkan keputusan sebenar."""
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
        
        # 1. Semakan Direct
        if bet_direct > 0:
            if num == p1:
                win = DIRECT_PAYOUT['1st'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 1st Prize (+RM{win:.2f})")
            elif num == p2:
                win = DIRECT_PAYOUT['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 2nd Prize (+RM{win:.2f})")
            elif num == p3:
                win = DIRECT_PAYOUT['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct 3rd Prize (+RM{win:.2f})")
            elif num in specials:
                win = DIRECT_PAYOUT['special'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Special (+RM{win:.2f})")
            elif num in consolations:
                win = DIRECT_PAYOUT['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA Direct Consolation (+RM{win:.2f})")
                
        # 2. Semakan iBox
        if bet_ibox > 0 and perms > 0:
            if "".join(sorted(p1)) == sorted_num:
                win = (DIRECT_PAYOUT['1st'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 1st Prize ({p1}) (+RM{win:.2f})")
            if "".join(sorted(p2)) == sorted_num:
                win = (DIRECT_PAYOUT['2nd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 2nd Prize ({p2}) (+RM{win:.2f})")
            if "".join(sorted(p3)) == sorted_num:
                win = (DIRECT_PAYOUT['3rd'] / perms) * bet_ibox
                total_winnings += win
                hit_logs.append(f"Rank {rank} ({num}) KENA iBox 3rd Prize ({p3}) (+RM{win:.2f})")
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = (DIRECT_PAYOUT['special'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num}) KENA iBox Special ({sp}) (+RM{win:.2f})")
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = (DIRECT_PAYOUT['consolation'] / perms) * bet_ibox
                    total_winnings += win
                    hit_logs.append(f"Rank {rank} ({num}) KENA iBox Consolation ({cs}) (+RM{win:.2f})")
                    
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
        print(f"[AMARAN] Data tidak mencukupi ({total_records} rekod). Perlu lebih banyak data.")
        return
        
    split_index = total_records // 2
    training_draws = draws[:split_index]
    testing_draws = draws[split_index:]
    
    print("=" * 80)
    print(f" SIMULASI FORMULA 07: Top 3 Mirror Synergy")
    print(f" Jumlah Rekod: {total_records} | Latihan: {len(training_draws)} | Ujian: {len(testing_draws)}")
    print(f" Kos Pertaruhan Per Cabutan: RM13.00 (No 1-3: RM2, No 4-10: RM1)")
    print("=" * 80)
    
    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    latest_recs_payload = None
    
    for i, current_draw in enumerate(testing_draws):
        target_date = current_draw.get('date', 'N/A')
        draw_no = current_draw.get('draw_no', 'N/A')
        
        historical_window = draws[:split_index + i]
        recs = generate_mirror_pairing_recommendations(historical_window, top_n=10)
        
        latest_recs_payload = {
            "formula_id": "07_top3_mirror_pairing",
            "formula_name": "Top 3 Mirror Synergy",
            "target_date": target_date,
            "draw_no": draw_no,
            "budget_total_rm": 13,
            "recommendations": recs
        }
        
        cost_per_draw = 13.0
        winnings, hit_logs = evaluate_draw_results(recs, current_draw)
        
        total_invested += cost_per_draw
        total_won += winnings
        net_draw = winnings - cost_per_draw
        
        if winnings > 0:
            hits_count += 1
            status = f"[MENANG] +RM{winnings:8.2f} (Untung Bersih: RM{net_draw:+.2f})"
        else:
            status = f"[KALAH ] -RM{cost_per_draw:8.2f}"
            
        print(f"[{i+1:02d}/{len(testing_draws)}] Tarikh: {target_date} | Draw: {draw_no} | {status}")
        for log in hit_logs:
            print(f"     └─ {log}")
            
    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_recs_payload, f, indent=4)
        
    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0
    
    print("=" * 80)
    print(" KEPUTUSAN PRESTASI PELABURAN 6 BULAN (FORMULA 07)")
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
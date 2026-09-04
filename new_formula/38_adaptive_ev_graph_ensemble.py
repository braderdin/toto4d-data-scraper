#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 38_adaptive_ev_graph_ensemble.py
FORMULA NAME : Full-Graph Pairwise Co-occurrence & Direct EV Ensemble (Formula 38)
DESCRIPTION  : Penambahbaikan radikal daripada Formula 37:
               1. Unordered Pairwise Graph: Menilai kesemua 6 pasangan kombinasi
                  digit C(4,2) yang menepati sifat invarian posisi taruhan iBox.
               2. Direct Mathematical Expected Value (EV): Skor ranking menggunakan
                  pengiraan nilai jangkaan tunai sebenar (RM) mengikut matriks hadiah.
               3. Poisson Exhaustion Dampener: Mengawal risiko 'cold streak' akibat
                  keletihan digit yang muncul melampau dalam 2 sesi terkini.
               4. Rolling Window 9 Bulan Latihan ➔ Ujian 3 Bulan Terkini.

STRATEGI BET : Tepat 20 Nombor (Modal Tetap RM 20.00 / Cabutan):
               - 4x Permutasi 4  (Triplet AAAB) : iBox RM1 = RM4
               - 7x Permutasi 6  (2-Pasang AABB): iBox RM1 = RM7
               - 6x Permutasi 12 (1-Pasang AABC): iBox RM1 = RM6
               - 3x Permutasi 24 (Berbeza ABCD) : iBox RM1 = RM3
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import sys
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from itertools import combinations

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

# ==========================================
# KONFIGURASI DIREKTORI & LALUAN FAIL
# ==========================================
BASE_DIR = "/home/braderdin/toto4d-data-scraper"
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMP_OUTPUT_FILE = os.path.join(TEMP_DIR, "recommendations_38_adaptive_ev_graph_ensemble.json")

# ==========================================
# JADUAL PEMBAYARAN RASMI iBOX BIG (RM 1.00)
# ==========================================
IBOX_BIG_PAYOUT = {
    '1st': {24: 105.0, 12: 209.0, 6: 417.0, 4: 625.0},
    '2nd': {24: 42.0,  12: 84.0,  6: 167.0, 4: 250.0},
    '3rd': {24: 21.0,  12: 42.0,  6: 84.0,  4: 125.0},
    'special': {24: 8.0, 12: 15.0, 6: 30.0, 4: 45.0},
    'consolation': {24: 3.0, 12: 5.0, 6: 10.0, 4: 15.0}
}

# Purata pemberat kebarangkalian kemunculan mengikut tier hadiah Toto
TIER_BASE_PROB = {
    '1st': 1.0 / 10000.0,
    '2nd': 1.0 / 10000.0,
    '3rd': 1.0 / 10000.0,
    'special': 10.0 / 10000.0,
    'consolation': 10.0 / 10000.0
}

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, TypeError):
            pass
    return datetime.min

def get_permutation_count(num_str):
    counts = Counter(str(num_str)).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom

def get_canonical_box(num_str):
    return "".join(sorted(str(num_str).strip()))

# ==========================================
# ENJIN GRAF PERKAITAN & EV (FORMULA 38)
# ==========================================
def extract_draw_prizes(draw):
    items = []
    if draw.get('1st_prize'): items.append((str(draw['1st_prize']).strip(), 5.0))
    if draw.get('2nd_prize'): items.append((str(draw['2nd_prize']).strip(), 3.5))
    if draw.get('3rd_prize'): items.append((str(draw['3rd_prize']).strip(), 2.5))
    for sp in draw.get('special_prizes', []): items.append((str(sp).strip(), 1.0))
    for cs in draw.get('consolation_prizes', []): items.append((str(cs).strip(), 0.5))
    return [(s, w) for s, w in items if len(s) == 4 and s.isdigit()]

def build_pairwise_graph_and_bayes(history_draws):
    total_draws = len(history_draws)
    decay_lambda = 0.075

    pos_weights = [defaultdict(float) for _ in range(4)]
    pair_graph = defaultdict(float)
    digit_recent_exhaustion = Counter()

    # Kumpul kekerapan 2 cabutan paling akhir untuk semakan 'exhaustion'
    for draw in history_draws[-2:]:
        for s, _ in extract_draw_prizes(draw):
            for d in s:
                digit_recent_exhaustion[int(d)] += 1

    twin_density_count = 0
    total_valid_prizes = 0

    for idx, draw in enumerate(history_draws):
        delta_t = total_draws - 1 - idx
        time_factor = math.exp(-decay_lambda * delta_t)

        prizes = extract_draw_prizes(draw)
        for num_str, tier_w in prizes:
            total_valid_prizes += 1
            perms = get_permutation_count(num_str)
            if perms in (4, 6, 12):
                twin_density_count += 1

            combined_w = tier_w * time_factor
            digits = [int(ch) for ch in num_str]

            for p in range(4):
                pos_weights[p][digits[p]] += combined_w

            # Bina graf simetri C(4, 2) = 6 pasangan tanpa mempedulikan urutan kedudukan
            for u, v in combinations(digits, 2):
                pair_key = (min(u, v), max(u, v))
                pair_graph[pair_key] += combined_w

    # Normalisasi kebarangkalian posisi & Entropi
    pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        total_p_w = sum(pos_weights[p].values()) or 1.0
        for d in range(10):
            prob = (pos_weights[p][d] + 0.08) / (total_p_w + 0.8)
            pos_probs[p][d] = prob
            if prob > 0:
                shannon_entropy -= prob * math.log(prob)

    tot_pair_w = sum(pair_graph.values()) or 1.0
    twin_ratio = twin_density_count / max(total_valid_prizes, 1)

    return pos_probs, pair_graph, tot_pair_w, shannon_entropy, twin_ratio, digit_recent_exhaustion

def calculate_direct_ev(num_str, perms, pos_probs, pair_graph, tot_pair_w, digit_exhaustion):
    digits = [int(d) for d in num_str]

    # 1. Kebarangkalian asas nombor daripada posisi
    p_pos = (pos_probs[0][digits[0]] * pos_probs[1][digits[1]] *
             pos_probs[2][digits[2]] * pos_probs[3][digits[3]])

    # 2. Pengganda sinergi graf dari semua 6 pasangan
    pair_mult = 1.0
    for u, v in combinations(digits, 2):
        pair_key = (min(u, v), max(u, v))
        pw = (pair_graph.get(pair_key, 0.0) + 0.01) / (tot_pair_w + 0.55)
        pair_mult *= (pw * 100.0)
    pair_mult = pair_mult ** (1.0 / 6.0)

    # 3. Penapis Keletihan Digit (Poisson Exhaustion)
    # Jika mana-mana digit keluar melampau banyak (> 5 kali dalam 2 cabutan lepas), redamkan sedikit
    exhaustion_penalty = 1.0
    for d in set(digits):
        excess = digit_exhaustion[d]
        if excess > 5:
            exhaustion_penalty *= math.exp(-0.12 * (excess - 5))

    p_base_estimate = p_pos * (pair_mult ** 0.65) * exhaustion_penalty

    # 4. Nilai Jangkaan Kewangan Sebenar (Expected Value - EV dalam Ringgit)
    # Kebarangkalian iBox = perms * P(base)
    # EV = Sum( P(Tier) * Payout(Tier, Perm) )
    ev_total = 0.0
    for tier in ['1st', '2nd', '3rd', 'special', 'consolation']:
        payout = IBOX_BIG_PAYOUT[tier][perms]
        tier_weight = TIER_BASE_PROB[tier] * 10000.0
        ev_tier = (p_base_estimate * perms * tier_weight) * payout
        ev_total += ev_tier

    return ev_total

def generate_formula_38_recommendations(history_draws):
    if len(history_draws) < 10:
        return [], {}

    pos_probs, pair_graph, tot_pair_w, entropy, twin_ratio, digit_exhaustion = build_pairwise_graph_and_bayes(history_draws)

    candidates_by_perm = {4: [], 6: [], 12: [], 24: []}

    # Kira EV untuk semua kombinasi
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    if perms not in candidates_by_perm:
                        continue

                    ev_val = calculate_direct_ev(num_str, perms, pos_probs, pair_graph, tot_pair_w, digit_exhaustion)
                    candidates_by_perm[perms].append((ev_val, num_str))

    for p in candidates_by_perm:
        candidates_by_perm[p].sort(key=lambda x: x[0], reverse=True)

    selected_numbers = []
    seen_canonical_boxes = set()

    # 1. Pilih 4 Nombor Permutasi 4 (Triplet) - Mutlak Digit Triplet Berbeza
    triplet_selected = []
    used_triplet_digits = set()
    for ev_val, num in candidates_by_perm[4]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        cnt = Counter(num)
        triplet_digit = [d for d, c in cnt.items() if c == 3][0]
        if triplet_digit in used_triplet_digits:
            continue

        used_triplet_digits.add(triplet_digit)
        seen_canonical_boxes.add(c_box)
        triplet_selected.append({"number": num, "permutation": 4, "ev_score": round(ev_val, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(triplet_selected) == 4:
            break
    selected_numbers.extend(triplet_selected)

    # 2. Pilih 7 Nombor Permutasi 6 (2-Pasang) - Hadkan Pertindihan Pasangan
    sixway_selected = []
    twin_pair_usage = Counter()
    for ev_val, num in candidates_by_perm[6]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        cnt = Counter(num)
        p_keys = tuple(sorted(cnt.keys()))
        if max(twin_pair_usage[d] for d in p_keys) >= 3 and len(sixway_selected) < 6:
            continue

        for d in p_keys:
            twin_pair_usage[d] += 1
        seen_canonical_boxes.add(c_box)
        sixway_selected.append({"number": num, "permutation": 6, "ev_score": round(ev_val, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(sixway_selected) == 7:
            break
    selected_numbers.extend(sixway_selected)

    # 3. Pilih 6 Nombor Permutasi 12 (1-Pasang) - Sinergi Seimbang
    twelveway_selected = []
    digit_12_usage = Counter()
    for ev_val, num in candidates_by_perm[12]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        digits = [int(d) for d in num]
        if max(digit_12_usage[d] for d in set(digits)) >= 3 and len(twelveway_selected) < 5:
            continue

        for d in set(digits):
            digit_12_usage[d] += 1
        seen_canonical_boxes.add(c_box)
        twelveway_selected.append({"number": num, "permutation": 12, "ev_score": round(ev_val, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(twelveway_selected) == 6:
            break
    selected_numbers.extend(twelveway_selected)

    # 4. Pilih 3 Nombor Permutasi 24 (Berbeza ABCD) - EV Tertinggi
    twentyfour_selected = []
    for ev_val, num in candidates_by_perm[24]:
        c_box = get_canonical_box(num)
        if c_box in seen_canonical_boxes:
            continue
        seen_canonical_boxes.add(c_box)
        twentyfour_selected.append({"number": num, "permutation": 24, "ev_score": round(ev_val, 4), "bet_type": "iBox", "bet_amount_rm": 1.0})
        if len(twentyfour_selected) == 3:
            break
    selected_numbers.extend(twentyfour_selected)

    for idx, item in enumerate(selected_numbers):
        item["rank"] = idx + 1

    meta_info = {
        "twin_ratio": round(twin_ratio, 3),
        "entropy": round(entropy, 2),
        "total_ev_projected": round(sum(it['ev_score'] for it in selected_numbers), 4)
    }

    return selected_numbers, meta_info

# ==========================================
# PENILAIAN HADIAH
# ==========================================
def evaluate_draw_ibox(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]

    c_p1 = get_canonical_box(p1)
    c_p2 = get_canonical_box(p2)
    c_p3 = get_canonical_box(p3)
    c_specials = [get_canonical_box(x) for x in specials]
    c_consolations = [get_canonical_box(x) for x in consolations]

    total_winnings = 0.0
    hit_logs = []

    for item in recommendations:
        num = item['number']
        perm = item['permutation']
        rank = item['rank']
        c_num = get_canonical_box(num)

        if c_num == c_p1:
            win = IBOX_BIG_PAYOUT['1st'][perm]
            total_winnings += win
            hit_logs.append(f"🥇 Rank {rank:02d} [{num} ({perm}-Way)] KENA 1st Prize ({p1}) -> +RM {win:.2f}")
        if c_num == c_p2:
            win = IBOX_BIG_PAYOUT['2nd'][perm]
            total_winnings += win
            hit_logs.append(f"🥈 Rank {rank:02d} [{num} ({perm}-Way)] KENA 2nd Prize ({p2}) -> +RM {win:.2f}")
        if c_num == c_p3:
            win = IBOX_BIG_PAYOUT['3rd'][perm]
            total_winnings += win
            hit_logs.append(f"🥉 Rank {rank:02d} [{num} ({perm}-Way)] KENA 3rd Prize ({p3}) -> +RM {win:.2f}")
        for idx_sp, sp_box in enumerate(c_specials):
            if c_num == sp_box:
                win = IBOX_BIG_PAYOUT['special'][perm]
                total_winnings += win
                hit_logs.append(f"⭐ Rank {rank:02d} [{num} ({perm}-Way)] KENA Special ({specials[idx_sp]}) -> +RM {win:.2f}")
                break
        for idx_cs, cs_box in enumerate(c_consolations):
            if c_num == cs_box:
                win = IBOX_BIG_PAYOUT['consolation'][perm]
                total_winnings += win
                hit_logs.append(f"🎖️  Rank {rank:02d} [{num} ({perm}-Way)] KENA Consolation ({consolations[idx_cs]}) -> +RM {win:.2f}")
                break

    return total_winnings, hit_logs

# ==========================================
# ENJIN UTAMA (MAIN)
# ==========================================
def main():
    os.makedirs(TEMP_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data tidak dijumpai di: {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)

    draws = [d for d in draws if parse_date(d.get('date', '')) != datetime.min]
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)

    if total_records < 30:
        print("[AMARAN] Data tidak mencukupi.")
        return

    # Tetingkap Ujian: 3 Bulan Terkini (~92 Hari)
    latest_date = parse_date(draws[-1].get('date', ''))
    test_cutoff_date = latest_date - timedelta(days=92)

    split_index = None
    for idx, d in enumerate(draws):
        if parse_date(d.get('date', '')) >= test_cutoff_date:
            split_index = idx
            break

    if split_index is None or split_index < 20:
        split_index = int(total_records * 0.75)

    test_start_date = parse_date(draws[split_index].get('date', ''))
    train_cutoff_date = test_start_date - timedelta(days=275)

    train_start_index = 0
    for idx, d in enumerate(draws[:split_index]):
        if parse_date(d.get('date', '')) >= train_cutoff_date:
            train_start_index = idx
            break

    testing_draws = draws[split_index:]
    initial_training_draws = draws[train_start_index:split_index]

    start_train_str = initial_training_draws[0].get('date', 'N/A')
    end_train_str = initial_training_draws[-1].get('date', 'N/A')
    start_test_str = testing_draws[0].get('date', 'N/A')
    end_test_str = testing_draws[-1].get('date', 'N/A')

    if HAS_RICH:
        panel_text = Text()
        panel_text.append("🚀 FORMULA 38: FULL-GRAPH PAIRWISE CO-OCCURRENCE & EV ENSEMBLE\n", style="bold yellow")
        panel_text.append("Model: Sinergi Graf C(4,2) + Expected Value (EV) + Saringan Keletihan Poisson\n", style="cyan")
        panel_text.append(f"📁 Konteks Gelongsor (9 Bulan) : {len(initial_training_draws)} Sesi ({start_train_str} -> {end_train_str})\n", style="white")
        panel_text.append(f"🎯 Fasa Ujian Real-Time (3 Bulan): {len(testing_draws)} Cabutan ({start_test_str} -> {end_test_str})\n", style="white")
        panel_text.append("💰 Konfigurasi Modal Tetap     : RM 20.00 / Cabutan (20 Nombor iBox RM1.00)", style="bold green")
        console.print(Panel(panel_text, box=box.ROUNDED, border_style="bright_blue"))
    else:
        print("=" * 80)
        print(" FORMULA 38: FULL-GRAPH PAIRWISE CO-OCCURRENCE & EV ENSEMBLE")
        print(f" Latihan (9 Bulan) : {len(initial_training_draws)} sesi ({start_train_str} -> {end_train_str})")
        print(f" Ujian (3 Bulan)   : {len(testing_draws)} sesi ({start_test_str} -> {end_test_str})")
        print("=" * 80)

    total_invested = 0.0
    total_won = 0.0
    hits_count = 0
    prize_counts = Counter()
    latest_payload = None

    for i, current_draw in enumerate(testing_draws):
        curr_test_date = parse_date(current_draw.get('date', ''))
        draw_no = current_draw.get('draw_no', 'N/A')
        target_date = current_draw.get('date', 'N/A')

        window_start_date = curr_test_date - timedelta(days=275)
        rolling_context = [d for d in draws[:split_index + i] if parse_date(d.get('date', '')) >= window_start_date]

        recs, meta = generate_formula_38_recommendations(rolling_context)

        cost_this_draw = sum(item['bet_amount_rm'] for item in recs)
        winnings, hit_logs = evaluate_draw_ibox(recs, current_draw)

        total_invested += cost_this_draw
        total_won += winnings
        net_draw = winnings - cost_this_draw

        if winnings > 0:
            hits_count += 1
            for l in hit_logs:
                if "1st Prize" in l: prize_counts['1st'] += 1
                elif "2nd Prize" in l: prize_counts['2nd'] += 1
                elif "3rd Prize" in l: prize_counts['3rd'] += 1
                elif "Special" in l: prize_counts['special'] += 1
                elif "Consolation" in l: prize_counts['consolation'] += 1

        latest_payload = {
            "formula_id": "38_adaptive_ev_graph_ensemble",
            "formula_name": "Full-Graph Pairwise Co-occurrence & Direct EV Ensemble",
            "target_date": target_date,
            "draw_no": draw_no,
            "meta_signals": meta,
            "budget_rm": cost_this_draw,
            "quota_breakdown": {"perm_4": 4, "perm_6": 7, "perm_12": 6, "perm_24": 3},
            "recommendations": recs
        }

        prefix = f"[{i+1:02d}/{len(testing_draws)}] {target_date} (#{draw_no})"
        if winnings > 0:
            status_str = f"🎉 MENANG RM {winnings:7.2f} (Untung: +RM {net_draw:6.2f})"
            if HAS_RICH:
                console.print(f"[bold green]{prefix} | EV={meta['total_ev_projected']:.2f} | {status_str}[/bold green]")
                for h in hit_logs:
                    console.print(f"     └─ {h}", style="yellow")
            else:
                print(f"{prefix} | EV={meta['total_ev_projected']:.2f} | {status_str}")
                for h in hit_logs:
                    print(f"     └─ {h}")
        else:
            status_str = f"❌ Kalah  -RM {cost_this_draw:5.2f}"
            if HAS_RICH:
                console.print(f"[dim]{prefix} | EV={meta['total_ev_projected']:.2f} | {status_str}[/dim]")
            else:
                print(f"{prefix} | EV={meta['total_ev_projected']:.2f} | {status_str}")

    with open(TEMP_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(latest_payload, f, indent=4)

    net_profit = total_won - total_invested
    roi_percent = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
    hit_rate = (hits_count / len(testing_draws) * 100) if len(testing_draws) > 0 else 0.0

    if HAS_RICH:
        summary_table = Table(title="📊 RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 38 EV-GRAPH)", box=box.HEAVY_EDGE, header_style="bold magenta")
        summary_table.add_column("Metrik Prestasi", style="bold cyan")
        summary_table.add_column("Nilai Sebenar", justify="right", style="bold white")

        summary_table.add_row("🗓️ Jumlah Cabutan Diuji", f"{len(testing_draws)} sesi")
        summary_table.add_row("🎯 Cabutan Mengena (Hit Rate)", f"{hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        summary_table.add_row("💵 Jumlah Modal Dilabur", f"RM {total_invested:,.2f}")
        summary_table.add_row("🏆 Jumlah Pulangan Hadiah", f"RM {total_won:,.2f}")
        
        profit_color = "bold green" if net_profit >= 0 else "bold red"
        summary_table.add_row("📈 Untung / Rugi Bersih", f"[{profit_color}]RM {net_profit:+,.2f}[/{profit_color}]")
        summary_table.add_row("🚀 Pulangan Pelaburan (ROI)", f"[{profit_color}]{roi_percent:+,.2f}%[/{profit_color}]")

        breakdown_text = (
            f"1st: {prize_counts['1st']} | 2nd: {prize_counts['2nd']} | 3rd: {prize_counts['3rd']} | "
            f"Special: {prize_counts['special']} | Consolation: {prize_counts['consolation']}"
        )
        summary_table.add_row("🎁 Pecahan Kenaan Hadiah", breakdown_text)
        console.print("\n")
        console.print(summary_table)

        if latest_payload and latest_payload.get("recommendations"):
            rec_table = Table(title=f"🔮 CADANGAN 20 NOMBOR AKHIR (Cabutan Seterusnya: {latest_payload['target_date']})", box=box.ROUNDED)
            rec_table.add_column("Rank", justify="center", style="bold yellow")
            rec_table.add_column("Nombor 4D", justify="center", style="bold bright_white")
            rec_table.add_column("Permutasi", justify="center", style="cyan")
            rec_table.add_column("Kategori Corak", style="magenta")
            rec_table.add_column("Pertaruhan", justify="center", style="green")
            rec_table.add_column("Jangkaan EV (RM)", justify="right", style="bold bright_green")

            cat_map = {4: "4-Way (Triplet AAAB)", 6: "6-Way (2 Pasang AABB)", 12: "12-Way (1 Pasang AABC)", 24: "24-Way (Berbeza ABCD)"}

            for item in latest_payload["recommendations"]:
                rec_table.add_row(
                    f"{item['rank']:02d}",
                    item['number'],
                    f"{item['permutation']}-way",
                    cat_map.get(item['permutation'], "-"),
                    f"iBox RM {item['bet_amount_rm']:.2f}",
                    f"RM {item['ev_score']:.3f}"
                )
            console.print(rec_table)
            console.print(f"[bold green]💾 Rekod cadangan disimpan ke:[/bold green] [underline]{TEMP_OUTPUT_FILE}[/underline]\n")
    else:
        print("\n" + "=" * 80)
        print(" RINGKASAN PRESTASI 3 BULAN TERKINI (FORMULA 38 EV-GRAPH)")
        print("=" * 80)
        print(f"  Jumlah Cabutan Diuji    : {len(testing_draws)} sesi")
        print(f"  Kadar Kenaan (Hit Rate) : {hit_rate:.2f}% ({hits_count}/{len(testing_draws)})")
        print(f"  Jumlah Modal Dilabur    : RM {total_invested:.2f}")
        print(f"  Jumlah Hadiah Menang    : RM {total_won:.2f}")
        print(f"  Untung / Rugi Bersih    : RM {net_profit:+.2f}")
        print(f"  Pulangan Modal (ROI)    : {roi_percent:+.2f}%")
        print(f"  Fail Cadangan Disimpan  : {TEMP_OUTPUT_FILE}")
        print("=" * 80)

if __name__ == "__main__":
    main()
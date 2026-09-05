#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : 40_f18_multi_window_benchmark_hybrid.py
FORMULA NAME : Formula 40 - F18 Multi-Window Bayesian Benchmark & Rank Profiler
DESCRIPTION  : Menguji enjin Formula 18 (Dirichlet Dual-Window Bayesian Momentum)
               merentasi 5 tetingkap analisis sejarah berbanding 3 bulan terkini:
               1. 9 Bulan (Gelongsor ~275 Hari)
               2. 6 Bulan (Gelongsor ~183 Hari)
               3. 3 Bulan (Gelongsor ~92 Hari)
               4. 1 Bulan (Gelongsor ~30 Hari)
               5. 2 Minggu (Gelongsor ~14 Hari)

PORTFOLIO STRATEGI (25 NOMBOR - RM 25.00 / SESI):
  - Direct RM 1.00 (4 Nombor): Top 1 AAAB, Top 1 AABB, Top 1 AABC, Top 1 ABCD
  - iBox RM 1.00   (21 Nombor): 7x AAAB, 10x AABB, 2x AABC, 2x ABCD

OUTPUT TAMBAHAN:
  - Analisis Hari Cabutan (Rabu, Sabtu, Ahad, Selasa)
  - Analisis Lengkap PnL & Kenaan bagi setiap Rank 1 hingga 25
  - Penjanaan 5 Fail JSON Cadangan ke folder temp/output_formula40/
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import sys
import json
import math
from datetime import datetime, timedelta
from collections import defaultdict, Counter

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
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "temp", "output_formula40")

# ==========================================
# JADUAL PEMBAYARAN RASMI TOTO 4D (BIG RM 1.00)
# ==========================================
DIRECT_BIG_PAYOUT = {
    '1st': 2500.0,
    '2nd': 1000.0,
    '3rd': 500.0,
    'special': 180.0,
    'consolation': 60.0
}

IBOX_BIG_PAYOUT = {
    '1st': {24: 105.0, 12: 209.0, 6: 417.0, 4: 625.0},
    '2nd': {24: 42.0,  12: 84.0,  6: 167.0, 4: 250.0},
    '3rd': {24: 21.0,  12: 42.0,  6: 84.0,  4: 125.0},
    'special': {24: 8.0, 12: 15.0, 6: 30.0, 4: 45.0},
    'consolation': {24: 3.0, 12: 5.0, 6: 10.0, 4: 15.0}
}

MALAY_DAYS = {
    0: "Isnin",
    1: "Selasa",
    2: "Rabu",
    3: "Khamis",
    4: "Jumaat",
    5: "Sabtu",
    6: "Ahad"
}

# ==========================================
# PRA-PENGIRAAN STRUKTUR 10,000 NOMBOR
# ==========================================
def _init_lookup_tables():
    perm_table = {}
    canonical_table = {}
    for i in range(10000):
        s = f"{i:04d}"
        cnt = Counter(s).values()
        d = 1
        for c in cnt:
            d *= math.factorial(c)
        perm_table[s] = math.factorial(4) // d
        canonical_table[s] = "".join(sorted(s))
    return perm_table, canonical_table

PERM_LOOKUP, CANONICAL_LOOKUP = _init_lookup_tables()

def parse_date(date_str):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, TypeError):
            pass
    return datetime.min

# ==========================================
# ENJIN MATEMATIK FORMULA 18 TERAS
# ==========================================
def compute_formula_18_engine(history_draws):
    total_draws = len(history_draws)
    short_len = min(12, max(3, total_draws // 2)) if total_draws < 12 else 12
    long_len = min(60, total_draws)

    short_history = history_draws[-short_len:] if total_draws >= short_len else history_draws
    long_history = history_draws[-long_len:] if total_draws >= long_len else history_draws

    pos_alphas_long = [{d: 1.0 for d in range(10)} for _ in range(4)]
    for draw in long_history:
        items = [
            (draw.get('1st_prize'), 4.5),
            (draw.get('2nd_prize'), 3.2),
            (draw.get('3rd_prize'), 2.2)
        ]
        items += [(x, 0.8) for x in draw.get('special_prizes', [])]
        items += [(x, 0.4) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4):
                    pos_alphas_long[p][int(s[p])] += w

    pos_alphas_short = [{d: 0.5 for d in range(10)} for _ in range(4)]
    pair_alphas_short = defaultdict(lambda: 0.2)
    for idx, draw in enumerate(short_history):
        rec_boost = 1.0 + (idx / max(len(short_history), 1)) * 1.2
        items = [
            (draw.get('1st_prize'), 5.0),
            (draw.get('2nd_prize'), 3.5),
            (draw.get('3rd_prize'), 2.5)
        ]
        items += [(x, 1.0) for x in draw.get('special_prizes', [])]
        items += [(x, 0.5) for x in draw.get('consolation_prizes', [])]
        for s, w in items:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                wb = w * rec_boost
                for p in range(4):
                    pos_alphas_short[p][int(s[p])] += wb
                pair_alphas_short[(int(s[0]), int(s[1]))] += wb * 0.5
                pair_alphas_short[(int(s[2]), int(s[3]))] += wb * 0.5

    combined_pos_probs = [{} for _ in range(4)]
    shannon_entropy = 0.0
    for p in range(4):
        tot_l = sum(pos_alphas_long[p].values())
        tot_s = sum(pos_alphas_short[p].values())
        for d in range(10):
            p_long = pos_alphas_long[p][d] / tot_l
            p_short = pos_alphas_short[p][d] / tot_s
            prob = (0.30 * p_long) + (0.70 * p_short)
            combined_pos_probs[p][d] = max(prob, 1e-6)
            shannon_entropy -= prob * math.log(max(prob, 1e-6))

    tot_pair = sum(pair_alphas_short.values()) or 1.0
    return combined_pos_probs, pair_alphas_short, tot_pair, shannon_entropy

# ==========================================
# PENJANAAN 25 NOMBOR HIBRID & DIVERSIFIKASI
# ==========================================
def generate_f18_recommendations(history_draws):
    if len(history_draws) < 2:
        return [], 0.0

    pos_probs, pair_alphas, tot_pair, entropy_val = compute_formula_18_engine(history_draws)

    candidates_by_perm = {4: [], 6: [], 12: [], 24: []}
    for i in range(10000):
        num_str = f"{i:04d}"
        perm = PERM_LOOKUP[num_str]
        if perm not in candidates_by_perm:
            continue

        d0, d1, d2, d3 = int(num_str[0]), int(num_str[1]), int(num_str[2]), int(num_str[3])

        pf = pair_alphas.get((d0, d1), 0.2) / tot_pair
        pb = pair_alphas.get((d2, d3), 0.2) / tot_pair

        score = (
            math.log(pos_probs[0][d0]) +
            math.log(pos_probs[1][d1]) +
            math.log(pos_probs[2][d2]) +
            math.log(pos_probs[3][d3]) +
            0.35 * math.log(pf) +
            0.35 * math.log(pb)
        )
        candidates_by_perm[perm].append((score, num_str))

    for p in candidates_by_perm:
        candidates_by_perm[p].sort(key=lambda x: x[0], reverse=True)

    cat_titles = {
        4: "Triplet (AAAB)",
        6: "Dwi-Kembar (AABB)",
        12: "1-Pasang (AABC)",
        24: "Berbeza (ABCD)"
    }

    # 1. Direct (4 Nombor - Top 1 Setiap Corak)
    direct_selected = []
    for perm in (4, 6, 12, 24):
        if candidates_by_perm[perm]:
            top_score, top_num = candidates_by_perm[perm][0]
            direct_selected.append({
                "number": top_num,
                "permutation": perm,
                "score": round(top_score, 4),
                "bet_type": "Direct",
                "category": cat_titles[perm],
                "bet_amount_rm": 1.0
            })

    # 2. iBox (21 Nombor Berdiversifikasi)
    seen_canonical = set()
    ibox_selected = []

    # 7x 4-Way
    triplet_ibox = []
    used_triplets = set()
    for sc, num in candidates_by_perm[4]:
        c_box = CANONICAL_LOOKUP[num]
        if c_box in seen_canonical:
            continue
        cnt = Counter(num)
        triplet_d = [d for d, c in cnt.items() if c == 3][0]
        if triplet_d in used_triplets and len(triplet_ibox) < 7:
            continue
        used_triplets.add(triplet_d)
        seen_canonical.add(c_box)
        triplet_ibox.append({
            "number": num, "permutation": 4, "score": round(sc, 4),
            "bet_type": "iBox", "category": cat_titles[4], "bet_amount_rm": 1.0
        })
        if len(triplet_ibox) == 7:
            break

    if len(triplet_ibox) < 7:
        for sc, num in candidates_by_perm[4]:
            c_box = CANONICAL_LOOKUP[num]
            if c_box not in seen_canonical:
                seen_canonical.add(c_box)
                triplet_ibox.append({
                    "number": num, "permutation": 4, "score": round(sc, 4),
                    "bet_type": "iBox", "category": cat_titles[4], "bet_amount_rm": 1.0
                })
            if len(triplet_ibox) == 7:
                break
    ibox_selected.extend(triplet_ibox)

    # 10x 6-Way
    twin_ibox = []
    twin_digit_freq = Counter()
    for sc, num in candidates_by_perm[6]:
        c_box = CANONICAL_LOOKUP[num]
        if c_box in seen_canonical:
            continue
        cnt = Counter(num)
        pair_ds = tuple(sorted(cnt.keys()))
        if max(twin_digit_freq[d] for d in pair_ds) >= 3 and len(twin_ibox) < 8:
            continue
        for d in pair_ds:
            twin_digit_freq[d] += 1
        seen_canonical.add(c_box)
        twin_ibox.append({
            "number": num, "permutation": 6, "score": round(sc, 4),
            "bet_type": "iBox", "category": cat_titles[6], "bet_amount_rm": 1.0
        })
        if len(twin_ibox) == 10:
            break

    if len(twin_ibox) < 10:
        for sc, num in candidates_by_perm[6]:
            c_box = CANONICAL_LOOKUP[num]
            if c_box not in seen_canonical:
                seen_canonical.add(c_box)
                twin_ibox.append({
                    "number": num, "permutation": 6, "score": round(sc, 4),
                    "bet_type": "iBox", "category": cat_titles[6], "bet_amount_rm": 1.0
                })
            if len(twin_ibox) == 10:
                break
    ibox_selected.extend(twin_ibox)

    # 2x 12-Way
    twelve_ibox = []
    for sc, num in candidates_by_perm[12]:
        c_box = CANONICAL_LOOKUP[num]
        if c_box in seen_canonical:
            continue
        seen_canonical.add(c_box)
        twelve_ibox.append({
            "number": num, "permutation": 12, "score": round(sc, 4),
            "bet_type": "iBox", "category": cat_titles[12], "bet_amount_rm": 1.0
        })
        if len(twelve_ibox) == 2:
            break
    ibox_selected.extend(twelve_ibox)

    # 2x 24-Way
    twentyfour_ibox = []
    for sc, num in candidates_by_perm[24]:
        c_box = CANONICAL_LOOKUP[num]
        if c_box in seen_canonical:
            continue
        seen_canonical.add(c_box)
        twentyfour_ibox.append({
            "number": num, "permutation": 24, "score": round(sc, 4),
            "bet_type": "iBox", "category": cat_titles[24], "bet_amount_rm": 1.0
        })
        if len(twentyfour_ibox) == 2:
            break
    ibox_selected.extend(twentyfour_ibox)

    total_recommendations = direct_selected + ibox_selected
    for idx, item in enumerate(total_recommendations):
        item["rank"] = idx + 1

    return total_recommendations, entropy_val

# ==========================================
# PENILAIAN CABUTAN (DIRECT & IBOX)
# ==========================================
def evaluate_draw_hybrid(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]

    c_p1 = CANONICAL_LOOKUP.get(p1, "".join(sorted(p1)))
    c_p2 = CANONICAL_LOOKUP.get(p2, "".join(sorted(p2)))
    c_p3 = CANONICAL_LOOKUP.get(p3, "".join(sorted(p3)))
    c_specials = [CANONICAL_LOOKUP.get(x, "".join(sorted(x))) for x in specials]
    c_consolations = [CANONICAL_LOOKUP.get(x, "".join(sorted(x))) for x in consolations]

    total_winnings = 0.0
    rank_payouts = defaultdict(float)
    hit_logs = []

    for item in recommendations:
        num = item['number']
        perm = item['permutation']
        rank = item['rank']
        b_type = item['bet_type']

        if b_type == 'Direct':
            if num == p1:
                win = DIRECT_BIG_PAYOUT['1st']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT 1ST] Rank {rank:02d} [{num}] -> +RM {win:,.2f}")
            elif num == p2:
                win = DIRECT_BIG_PAYOUT['2nd']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT 2ND] Rank {rank:02d} [{num}] -> +RM {win:,.2f}")
            elif num == p3:
                win = DIRECT_BIG_PAYOUT['3rd']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"💥 [DIRECT 3RD] Rank {rank:02d} [{num}] -> +RM {win:,.2f}")
            elif num in specials:
                win = DIRECT_BIG_PAYOUT['special']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"⭐ [DIRECT SPECIAL] Rank {rank:02d} [{num}] -> +RM {win:,.2f}")
            elif num in consolations:
                win = DIRECT_BIG_PAYOUT['consolation']
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🎖️  [DIRECT CONSOLATION] Rank {rank:02d} [{num}] -> +RM {win:,.2f}")

        elif b_type == 'iBox':
            c_num = CANONICAL_LOOKUP.get(num, "".join(sorted(num)))
            if c_num == c_p1:
                win = IBOX_BIG_PAYOUT['1st'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥇 [iBox {perm}W] Rank {rank:02d} [{num}] 1st -> +RM {win:.2f}")
            if c_num == c_p2:
                win = IBOX_BIG_PAYOUT['2nd'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥈 [iBox {perm}W] Rank {rank:02d} [{num}] 2nd -> +RM {win:.2f}")
            if c_num == c_p3:
                win = IBOX_BIG_PAYOUT['3rd'][perm]
                total_winnings += win
                rank_payouts[rank] += win
                hit_logs.append(f"🥉 [iBox {perm}W] Rank {rank:02d} [{num}] 3rd -> +RM {win:.2f}")
            for idx_s, sp_box in enumerate(c_specials):
                if c_num == sp_box:
                    win = IBOX_BIG_PAYOUT['special'][perm]
                    total_winnings += win
                    rank_payouts[rank] += win
                    hit_logs.append(f"⭐ [iBox {perm}W] Rank {rank:02d} [{num}] Spec -> +RM {win:.2f}")
                    break
            for idx_c, cs_box in enumerate(c_consolations):
                if c_num == cs_box:
                    win = IBOX_BIG_PAYOUT['consolation'][perm]
                    total_winnings += win
                    rank_payouts[rank] += win
                    hit_logs.append(f"🎖️  [iBox {perm}W] Rank {rank:02d} [{num}] Cons -> +RM {win:.2f}")
                    break

    return total_winnings, rank_payouts, hit_logs

# ==========================================
# SIMULASI HORIZON & BENCHMARK UTAMA
# ==========================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        print(f"[RALAT] Fail data tidak wujud: {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)

    draws = [d for d in draws if parse_date(d.get('date', '')) != datetime.min]
    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)

    if total_records < 30:
        print("[AMARAN] Rekod data tidak mencukupi untuk simulasi.")
        return

    latest_date = parse_date(draws[-1].get('date', ''))
    test_cutoff_date = latest_date - timedelta(days=92)

    split_index = None
    for idx, d in enumerate(draws):
        if parse_date(d.get('date', '')) >= test_cutoff_date:
            split_index = idx
            break

    if split_index is None or split_index < 10:
        split_index = max(10, int(total_records * 0.75))

    testing_draws = draws[split_index:]
    total_test_draws = len(testing_draws)

    HORIZONS = [
        {"id": "9_months", "name": "9 Bulan Analisis", "days": 275, "slug": "f18_9months"},
        {"id": "6_months", "name": "6 Bulan Analisis", "days": 183, "slug": "f18_6months"},
        {"id": "3_months", "name": "3 Bulan Analisis", "days": 92,  "slug": "f18_3months"},
        {"id": "1_month",  "name": "1 Bulan Analisis", "days": 30,  "slug": "f18_1month"},
        {"id": "2_weeks",  "name": "2 Minggu Analisis", "days": 14,  "slug": "f18_2weeks"}
    ]

    if HAS_RICH:
        banner_text = Text()
        banner_text.append("🔬 FORMULA 40: MULTI-WINDOW BAYESIAN BENCHMARK MASTER\n", style="bold yellow")
        banner_text.append("Enjin Teras: Formula 18 (Dirichlet Dual-Window Bayesian Momentum)\n", style="cyan")
        banner_text.append(f"Data Sebenar 1 Tahun | Fasa Ujian Sebenar: 3 Bulan Terkini ({total_test_draws} Sesi Cabutan)\n", style="white")
        banner_text.append("Konfigurasi Pertaruhan : 25 Nombor (RM 25.00 / Sesi) -> 21 iBox + 4 Direct", style="bold green")
        console.print(Panel(banner_text, box=box.ROUNDED, border_style="bright_blue"))
    else:
        print("=" * 85)
        print(" FORMULA 40: MULTI-WINDOW BAYESIAN BENCHMARK (FORMULA 18 ONLY)")
        print(f" Ujian 3 Bulan Terkini: {total_test_draws} sesi cabutan | Bajet RM 25.00 / sesi")
        print("=" * 85)

    horizon_results = []
    best_horizon = None
    max_net_profit = -float('inf')

    for h_cfg in HORIZONS:
        h_name = h_cfg['name']
        h_days = h_cfg['days']
        h_slug = h_cfg['slug']

        total_invested = 0.0
        total_won = 0.0
        hits_count = 0
        direct_hits_count = 0
        prize_counter = Counter()

        day_performance = defaultdict(lambda: {"sessions": 0, "hits": 0, "invested": 0.0, "won": 0.0})
        rank_profit_loss = defaultdict(lambda: {
            "cost": 0.0,
            "won": 0.0,
            "hits": 0,
            "bet_type": "",
            "category": "",
            "perm": 0
        })

        latest_recommendations = []
        latest_entropy = 0.0

        for i, current_draw in enumerate(testing_draws):
            curr_date = parse_date(current_draw.get('date', ''))
            day_idx = curr_date.weekday()
            day_name = MALAY_DAYS.get(day_idx, "N/A")

            window_start = curr_date - timedelta(days=h_days)
            rolling_context = [
                d for d in draws[:split_index + i]
                if parse_date(d.get('date', '')) >= window_start
            ]

            recs, entropy = generate_f18_recommendations(rolling_context)
            if i == len(testing_draws) - 1:
                latest_recommendations = recs
                latest_entropy = entropy

            cost_session = sum(item['bet_amount_rm'] for item in recs)
            winnings, rank_payouts, hit_logs = evaluate_draw_hybrid(recs, current_draw)

            total_invested += cost_session
            total_won += winnings

            day_performance[day_name]["sessions"] += 1
            day_performance[day_name]["invested"] += cost_session
            day_performance[day_name]["won"] += winnings

            for r_item in recs:
                r_no = r_item['rank']
                rank_profit_loss[r_no]["cost"] += r_item['bet_amount_rm']
                payout = rank_payouts.get(r_no, 0.0)
                rank_profit_loss[r_no]["won"] += payout
                if payout > 0:
                    rank_profit_loss[r_no]["hits"] += 1
                rank_profit_loss[r_no]["bet_type"] = r_item['bet_type']
                rank_profit_loss[r_no]["category"] = r_item['category']
                rank_profit_loss[r_no]["perm"] = r_item['permutation']

            if winnings > 0:
                hits_count += 1
                day_performance[day_name]["hits"] += 1
                for log in hit_logs:
                    if "DIRECT" in log:
                        direct_hits_count += 1
                    if "1st" in log: prize_counter['1st'] += 1
                    elif "2nd" in log: prize_counter['2nd'] += 1
                    elif "3rd" in log: prize_counter['3rd'] += 1
                    elif "Spec" in log or "SPECIAL" in log: prize_counter['special'] += 1
                    elif "Cons" in log or "CONSOLATION" in log: prize_counter['consolation'] += 1

        net_profit = total_won - total_invested
        roi = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
        hit_rate = (hits_count / total_test_draws * 100) if total_test_draws > 0 else 0.0

        res_payload = {
            "config": h_cfg,
            "total_invested": total_invested,
            "total_won": total_won,
            "net_profit": net_profit,
            "roi": roi,
            "hit_rate": hit_rate,
            "hits_count": hits_count,
            "direct_hits_count": direct_hits_count,
            "prize_counter": prize_counter,
            "day_performance": day_performance,
            "rank_profit_loss": rank_profit_loss,
            "latest_recommendations": latest_recommendations,
            "latest_entropy": latest_entropy
        }
        horizon_results.append(res_payload)

        out_json_path = os.path.join(OUTPUT_DIR, f"recommendations_{h_slug}.json")
        json_export_data = {
            "formula": "Formula 40 - F18 Multi-Window Benchmark",
            "horizon_name": h_name,
            "horizon_days": h_days,
            "target_next_draw": draws[-1].get('date', 'N/A'),
            "entropy_shannon": round(latest_entropy, 4),
            "budget_total_rm": 25.0,
            "breakdown": {
                "direct_rm1": 4,
                "ibox_rm1": 21
            },
            "recommendations": latest_recommendations
        }
        with open(out_json_path, 'w', encoding='utf-8') as f_out:
            json.dump(json_export_data, f_out, indent=4)

        if net_profit > max_net_profit:
            max_net_profit = net_profit
            best_horizon = res_payload

    # ==========================================
    # PAPARAN KEPUTUSAN KESELURUHAN (RICH TABLE)
    # ==========================================
    if HAS_RICH:
        comp_table = Table(title="📊 PERBANDINGAN PRESTASI 5 HORIZON LATIHAN (FORMULA 18 - 3 BULAN TERKINI)", box=box.HEAVY_EDGE)
        comp_table.add_column("Horizon Analisis", style="bold cyan")
        comp_table.add_column("Modal", justify="right", style="white")
        comp_table.add_column("Pulangan", justify="right", style="bright_yellow")
        comp_table.add_column("Untung Bersih", justify="right")
        comp_table.add_column("ROI (%)", justify="right")
        comp_table.add_column("Hit Rate", justify="center", style="white")
        comp_table.add_column("Direct Tepat", justify="center", style="bold magenta")
        comp_table.add_column("Fail JSON Disimpan", style="dim")

        for r in horizon_results:
            p_color = "bold green" if r['net_profit'] >= 0 else "bold red"
            c_pnl = f"[{p_color}]RM {r['net_profit']:+,.2f}[/{p_color}]"
            c_roi = f"[{p_color}]{r['roi']:+,.2f}%[/{p_color}]"
            f_name = f"recommendations_{r['config']['slug']}.json"

            comp_table.add_row(
                r['config']['name'],
                f"RM {r['total_invested']:,.2f}",
                f"RM {r['total_won']:,.2f}",
                c_pnl,
                c_roi,
                f"{r['hit_rate']:.1f}% ({r['hits_count']}/{total_test_draws})",
                f"{r['direct_hits_count']}x",
                f_name
            )
        console.print(comp_table)

        # Jadual Analisis Hari
        b_name = best_horizon['config']['name']
        day_table = Table(title=f"📅 ANALISIS PRESTASI MENGIKUT HARI ({b_name})", box=box.ROUNDED)
        day_table.add_column("Hari Cabutan", style="bold yellow")
        day_table.add_column("Kekerapan Sesi", justify="center")
        day_table.add_column("Kenaan (Hits)", justify="center", style="green")
        day_table.add_column("Kadar Kenaan", justify="right")
        day_table.add_column("Modal Dilabur", justify="right")
        day_table.add_column("Pulangan Hadiah", justify="right", style="bright_yellow")
        day_table.add_column("Untung / Rugi", justify="right")
        day_table.add_column("ROI Hari", justify="right")

        for d_name in ["Rabu", "Sabtu", "Ahad", "Selasa"]:
            d_data = best_horizon['day_performance'].get(d_name, None)
            if d_data and d_data['sessions'] > 0:
                d_net = d_data['won'] - d_data['invested']
                d_roi = (d_net / d_data['invested'] * 100) if d_data['invested'] > 0 else 0.0
                d_rate = (d_data['hits'] / d_data['sessions'] * 100)
                d_color = "bold green" if d_net >= 0 else "bold red"

                day_table.add_row(
                    d_name,
                    f"{d_data['sessions']} sesi",
                    f"{d_data['hits']} kali",
                    f"{d_rate:.1f}%",
                    f"RM {d_data['invested']:,.2f}",
                    f"RM {d_data['won']:,.2f}",
                    f"[{d_color}]RM {d_net:+,.2f}[/{d_color}]",
                    f"[{d_color}]{d_roi:+,.1f}%[/{d_color}]"
                )
        console.print("\n")
        console.print(day_table)

        # ==========================================
        # JADUAL PENUH BEDAH SIASAT 25 NOMBOR (RANK 01 - 25)
        # ==========================================
        rank_data_list = []
        for r_no in range(1, 26):
            r_info = best_horizon['rank_profit_loss'][r_no]
            c = r_info['cost']
            w = r_info['won']
            h = r_info['hits']
            diff = w - c
            roi_r = (diff / c * 100) if c > 0 else 0.0
            hit_pct = (h / total_test_draws * 100) if total_test_draws > 0 else 0.0
            rank_data_list.append({
                "rank": r_no,
                "bet_type": r_info.get("bet_type", "N/A"),
                "category": r_info.get("category", "N/A"),
                "perm": r_info.get("perm", 0),
                "cost": c,
                "won": w,
                "diff": diff,
                "roi": roi_r,
                "hits": h,
                "hit_pct": hit_pct
            })

        max_hits = max(x["hits"] for x in rank_data_list)
        max_profit = max(x["diff"] for x in rank_data_list)
        min_profit = min(x["diff"] for x in rank_data_list)

        rank_table = Table(
            title=f"🎯 BEDAH SIASAT LENGKAP 25 RANK NOMBOR ({b_name} - 42 Sesi Ujian)",
            box=box.HEAVY_EDGE,
            header_style="bold magenta"
        )
        rank_table.add_column("Rank", justify="center", style="bold yellow")
        rank_table.add_column("Jenis Bet & Corak", style="white")
        rank_table.add_column("Kekerapan Mengena (Hits)", justify="center")
        rank_table.add_column("Modal Dilabur", justify="right", style="dim")
        rank_table.add_column("Pulangan Hadiah", justify="right", style="bright_yellow")
        rank_table.add_column("Untung Bersih (PnL)", justify="right")
        rank_table.add_column("ROI (%)", justify="right")
        rank_table.add_column("Status & Catatan", style="bold")

        for item in rank_data_list:
            r_no = item["rank"]
            b_type = item["bet_type"]
            cat = item["category"]
            perm = item["perm"]
            diff = item["diff"]
            roi_val = item["roi"]
            hits = item["hits"]
            hit_pct = item["hit_pct"]

            # Pewarnaan Jenis Bet
            b_color = "bright_cyan" if b_type == "Direct" else "green"
            bet_desc = f"[{b_color}]{b_type}[/{b_color}] {cat} ({perm}W)"

            # Status dan Badge Prestasi
            badges = []
            if diff == max_profit and diff > 0:
                badges.append("[bold bright_yellow]👑 RAJA PROFIT[/bold bright_yellow]")
            elif diff > 0:
                badges.append("[bold green]🚀 UNTUNG[/bold green]")
            elif diff == 0:
                badges.append("[yellow]⚖️ PULANG MODAL[/yellow]")
            elif diff == min_profit:
                badges.append("[bold red]🔻 PALING RUGI[/bold red]")
            else:
                badges.append("[red]❌ RUGI MODAL[/red]")

            if hits == max_hits and max_hits > 0:
                badges.append("[bold bright_magenta]🎯 TOP HIT[/bold bright_magenta]")

            badge_str = " ".join(badges)

            pnl_color = "bold bright_green" if diff > 0 else ("yellow" if diff == 0 else "bold red")
            hit_color = "bold bright_cyan" if hits >= 3 else ("bright_white" if hits > 0 else "dim")

            rank_table.add_row(
                f"Rank {r_no:02d}",
                bet_desc,
                f"[{hit_color}]{hits}x ({hit_pct:.1f}%)[/{hit_color}]",
                f"RM {item['cost']:.2f}",
                f"RM {item['won']:,.2f}",
                f"[{pnl_color}]RM {diff:+,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{roi_val:+,.1f}%[/{pnl_color}]",
                badge_str
            )

            if r_no == 4:
                rank_table.add_section()

        console.print("\n")
        console.print(rank_table)

        # Ringkasan Kepimpinan Rank
        best_profit_item = max(rank_data_list, key=lambda x: x["diff"])
        best_hit_item = max(rank_data_list, key=lambda x: x["hits"])
        worst_loss_item = min(rank_data_list, key=lambda x: x["diff"])

        summary_panel = Text()
        summary_panel.append("📌 RUMUSAN PRESTASI RANK (1 BULAN ANALISIS):\n", style="bold yellow")
        summary_panel.append(
            f"  • 👑 Raja Keuntungan Tertinggi : Rank {best_profit_item['rank']:02d} ({best_profit_item['bet_type']}) "
            f"Untung Bersih RM {best_profit_item['diff']:+,.2f} (ROI {best_profit_item['roi']:+,.1f}%)\n",
            style="bright_green"
        )
        summary_panel.append(
            f"  • 🎯 Kekerapan Mengena Terbanyak: Rank {best_hit_item['rank']:02d} ({best_hit_item['bet_type']}) "
            f"Kena sebanyak {best_hit_item['hits']} kali ({best_hit_item['hit_pct']:.1f}% daripada 42 sesi)\n",
            style="bright_cyan"
        )
        summary_panel.append(
            f"  • 🔻 Beban Kerugian Terbesar   : Rank {worst_loss_item['rank']:02d} ({worst_loss_item['bet_type']}) "
            f"Rugi Bersih RM {worst_loss_item['diff']:+,.2f} (Sifar Kenaan)",
            style="bright_red"
        )
        console.print(Panel(summary_panel, box=box.ROUNDED, border_style="cyan"))

        console.print(f"\n[bold green]💾 Semua 5 fail cadangan tersimpan rapi di:[/bold green] [underline]{OUTPUT_DIR}[/underline]\n")

    else:
        print("\n" + "=" * 95)
        print(f" BEDAH SIASAT LENGKAP 25 RANK NOMBOR ({best_horizon['config']['name']})")
        print("=" * 95)
        print(f"{'Rank':<8} | {'Jenis Bet & Corak':<26} | {'Hits':<10} | {'Modal':<9} | {'Pulangan':<11} | {'PnL':<12} | {'ROI':<9}")
        print("-" * 95)
        for r_no in range(1, 26):
            r_info = best_horizon['rank_profit_loss'][r_no]
            c = r_info['cost']
            w = r_info['won']
            h = r_info['hits']
            diff = w - c
            roi_r = (diff / c * 100) if c > 0 else 0.0
            cat_str = f"{r_info.get('bet_type','')} {r_info.get('category','')}"
            print(f"Rank {r_no:02d}  | {cat_str:<26} | {h}x ({h/total_test_draws*100:4.1f}%) | RM {c:6.2f} | RM {w:8.2f} | RM {diff:+9.2f} | {roi_r:+6.1f}%")
        print("=" * 95)

if __name__ == "__main__":
    main()
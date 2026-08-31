#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D PREDICTION & BACKTESTING ENGINE
MODULE       : xx_test_all_formula.py
DESCRIPTION  : Master Benchmark Runner - Menjalankan backtesting 21 formula
               matematik secara serentak bagi 6 bulan terkini
               dan memaparkan analisis ROI lengkap menggunakan Rich Terminal.
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import json
import math
import itertools
from datetime import datetime
from collections import defaultdict, Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich import box

# ==========================================
# KONFIGURASI DIREKTORI & DATA
# ==========================================
BASE_DIR = "/home/braderdin/toto4d-data-scraper"
DATA_FILE = os.path.join(BASE_DIR, "data", "output", "toto_4d_results.json")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

DIRECT_PAYOUT = {
    '1st': 2500.0,
    '2nd': 1000.0,
    '3rd': 490.0,
    'special': 180.0,
    'consolation': 60.0
}

DAY_NAMES_MY = {
    0: "Isnin",
    1: "Selasa (Khas)",
    2: "Rabu",
    3: "Khamis",
    4: "Jumaat",
    5: "Sabtu",
    6: "Ahad"
}

console = Console()

# ==========================================
# UTILITI MATEMATIK & PENILAIAN
# ==========================================
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

def get_digital_root(n):
    return 0 if n == 0 else 1 + ((n - 1) % 9)

def get_mirror_digit(d):
    return (10 - int(d)) % 10

def get_unique_permutations(num_str):
    return sorted(list(set("".join(p) for p in itertools.permutations(num_str))))

def format_recs_std(top_numbers):
    """Format RM13 (No 1-3: Direct+iBox, No 4-10: iBox)"""
    recs = []
    for rank, num in enumerate(top_numbers[:10], start=1):
        recs.append({
            "rank": rank,
            "number": num,
            "bet_direct_rm": 1 if rank <= 3 else 0,
            "bet_ibox_rm": 1
        })
    return recs

def evaluate_draw(recommendations, actual_draw):
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]
    
    total_winnings = 0.0
    hit_count = 0
    
    for item in recommendations:
        num = item['number']
        bet_direct = item['bet_direct_rm']
        bet_ibox = item['bet_ibox_rm']
        perms = get_permutation_count(num)
        sorted_num = "".join(sorted(num))
        item_win = 0.0
        
        # Direct Big
        if bet_direct > 0:
            if num == p1: item_win += DIRECT_PAYOUT['1st'] * bet_direct
            elif num == p2: item_win += DIRECT_PAYOUT['2nd'] * bet_direct
            elif num == p3: item_win += DIRECT_PAYOUT['3rd'] * bet_direct
            elif num in specials: item_win += DIRECT_PAYOUT['special'] * bet_direct
            elif num in consolations: item_win += DIRECT_PAYOUT['consolation'] * bet_direct
            
        # iBox
        if bet_ibox > 0 and perms > 0:
            if "".join(sorted(p1)) == sorted_num: item_win += (DIRECT_PAYOUT['1st'] / perms) * bet_ibox
            if "".join(sorted(p2)) == sorted_num: item_win += (DIRECT_PAYOUT['2nd'] / perms) * bet_ibox
            if "".join(sorted(p3)) == sorted_num: item_win += (DIRECT_PAYOUT['3rd'] / perms) * bet_ibox
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num: item_win += (DIRECT_PAYOUT['special'] / perms) * bet_ibox
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num: item_win += (DIRECT_PAYOUT['consolation'] / perms) * bet_ibox
                
        if item_win > 0:
            total_winnings += item_win
            hit_count += 1
            
    return total_winnings, hit_count

# ==========================================
# ENJIN FORMULA 01 HINGGA 21
# ==========================================
def formula_01_hot_position(history, *args):
    pos_w = [defaultdict(float) for _ in range(4)]
    bg_w = [defaultdict(float) for _ in range(3)]
    for d in history:
        for s, w in [(d.get('1st_prize'), 3.5), (d.get('2nd_prize'), 2.5), (d.get('3rd_prize'), 2.0)] + [(x, 1.2) for x in d.get('special_prizes', [])] + [(x, 1.0) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_w[p][int(s[p])] += w
                for bp in range(3): bg_w[bp][(int(s[bp]), int(s[bp+1]))] += w
    pos_p = [{d: (pos_w[p][d] + 0.1)/(sum(pos_w[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    bg_p = [{k: (bg_w[bp][k] + 0.01)/(sum(bg_w[bp].values()) + 1.0) for k in bg_w[bp]} for bp in range(3)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    sc = (pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3] *
                          (bg_p[0].get((d0, d1), 0.001)**0.5) * (bg_p[1].get((d1, d2), 0.001)**0.5) * (bg_p[2].get((d2, d3), 0.001)**0.5))
                    cand.append((sc, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_02_cold_gap(history, *args):
    n = len(history)
    last_p = {p: {d: -1 for d in range(10)} for p in range(4)}
    cnt_p = {p: {d: 0 for d in range(10)} for p in range(4)}
    for idx, d in enumerate(history):
        for s in [d.get('1st_prize'), d.get('2nd_prize'), d.get('3rd_prize')] + d.get('special_prizes', []) + d.get('consolation_prizes', []):
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4):
                    last_p[p][int(s[p])] = idx
                    cnt_p[p][int(s[p])] += 1
    haz = [{} for _ in range(4)]
    for p in range(4):
        for d in range(10):
            g = n - 1 - last_p[p][d] if last_p[p][d] != -1 else n + 5
            l_rate = (cnt_p[p][d] + 1.0) / n
            haz[p][d] = (1.0 - math.exp(-l_rate * (g + 1))) * (1.0 + (g / (1.0 / l_rate)))
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    cand.append((haz[0][d0] + haz[1][d1] + haz[2][d2] + haz[3][d3], f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_03_markov_chain(history, *args):
    trans = [{f: {t: 0.0 for t in range(10)} for f in range(10)} for _ in range(4)]
    for i in range(1, len(history)):
        prev_p1 = str(history[i-1].get('1st_prize', '')).strip()
        if len(prev_p1) == 4 and prev_p1.isdigit():
            for s, w in [(history[i].get('1st_prize'), 3.5), (history[i].get('2nd_prize'), 2.5), (history[i].get('3rd_prize'), 2.0)]:
                s = str(s).strip()
                if len(s) == 4 and s.isdigit():
                    for p in range(4): trans[p][int(prev_p1[p])][int(s[p])] += w
    tp = [{f: {t: (trans[p][f][t] + 0.1)/(sum(trans[p][f].values()) + 1.0) for t in range(10)} for f in range(10)} for p in range(4)]
    ref = str(history[-1].get('1st_prize', '0000')).strip()
    if len(ref) != 4 or not ref.isdigit(): ref = "0000"
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    sc = tp[0][int(ref[0])][d0] * tp[1][int(ref[1])][d1] * tp[2][int(ref[2])][d2] * tp[3][int(ref[3])][d3]
                    cand.append((sc, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_04_sum_root(history, *args):
    sums = []
    roots = defaultdict(float)
    pos_cnt = [defaultdict(float) for _ in range(4)]
    for d in history:
        for s, w in [(d.get('1st_prize'), 3.0), (d.get('2nd_prize'), 2.0), (d.get('3rd_prize'), 1.5)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                dg = [int(c) for c in s]
                sm = sum(dg)
                sums.append((sm, w))
                roots[get_digital_root(sm)] += w
                for p in range(4): pos_cnt[p][dg[p]] += w
    tot_w = sum(w for _, w in sums) or 1.0
    mu = sum(s * w for s, w in sums) / tot_w
    var = sum(w * ((s - mu)**2) for s, w in sums) / tot_w
    sigma = math.sqrt(max(var, 1.0))
    pos_p = [{d: (pos_cnt[p][d] + 0.1)/(sum(pos_cnt[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    sm = d0 + d1 + d2 + d3
                    gf = math.exp(-((sm - mu)**2)/(2 * (sigma**2)))
                    rf = (roots[get_digital_root(sm)] + 0.1) / (tot_w + 0.9)
                    pf = (pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3])**0.5
                    cand.append((gf * rf * pf, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_05_weighted_ema(history, *args):
    n = len(history)
    pos_w = [defaultdict(float) for _ in range(4)]
    for idx, d in enumerate(history):
        tf = math.exp(-0.08 * (n - 1 - idx))
        for s, w in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 2.8), (d.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_w[p][int(s[p])] += w * tf
    pos_p = [{d: (pos_w[p][d] + 0.05)/(sum(pos_w[p].values()) + 0.5) for d in range(10)} for p in range(4)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    cand.append((pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3], f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_06_delta_reversion(history, *args):
    last = history[-1]
    seeds = [int(last[k]) for k in ('1st_prize', '2nd_prize', '3rd_prize') if str(last.get(k, '')).isdigit()]
    if not seeds: seeds = [1234, 5678, 9012]
    deltas = [1111, 2222, 3333, 555, 1250]
    cand = set()
    for s in seeds:
        for dt in deltas:
            cand.add(f"{(s + dt) % 10000:04d}")
            cand.add(f"{(s - dt) % 10000:04d}")
    return format_recs_std(list(cand))

def formula_07_mirror_synergy(history, *args):
    last = history[-1]
    seeds = [str(last[k]).strip() for k in ('1st_prize', '2nd_prize', '3rd_prize') if str(last.get(k, '')).isdigit()]
    if not seeds: seeds = ["1234", "5678", "9012"]
    cand = []
    for s in seeds:
        cand.append("".join(str(get_mirror_digit(c)) for c in s))
        cand.append(f"{get_mirror_digit(s[0])}{get_mirror_digit(s[1])}{s[2]}{s[3]}")
        cand.append(f"{s[0]}{s[1]}{get_mirror_digit(s[2])}{get_mirror_digit(s[3])}")
    i = 0
    while len(cand) < 15:
        cand.append(f"{(int(seeds[0]) + i * 505) % 10000:04d}")
        i += 1
    return format_recs_std(list(dict.fromkeys(cand)))

def formula_08_parity_scale(history, *args):
    pos_w = [defaultdict(float) for _ in range(4)]
    for d in history:
        for s, w in [(d.get('1st_prize'), 3.5), (d.get('2nd_prize'), 2.5), (d.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_w[p][int(s[p])] += w
    pos_p = [{d: (pos_w[p][d] + 0.1)/(sum(pos_w[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    dg = [d0, d1, d2, d3]
                    odd_c = sum(1 for x in dg if x % 2 != 0)
                    low_c = sum(1 for x in dg if x < 5)
                    mult = 1.0
                    if odd_c == 2: mult *= 1.4
                    if low_c == 2: mult *= 1.4
                    sc = pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3] * mult
                    cand.append((sc, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_09_lag_autocorr(history, *args):
    n = len(history)
    pos_lag = [defaultdict(float) for _ in range(4)]
    for lag, lag_w in {1: 0.45, 2: 0.28, 3: 0.17, 4: 0.10}.items():
        if n > lag:
            ref = history[-lag]
            for s in [ref.get('1st_prize'), ref.get('2nd_prize'), ref.get('3rd_prize')] + ref.get('special_prizes', []):
                s = str(s).strip()
                if len(s) == 4 and s.isdigit():
                    for p in range(4): pos_lag[p][int(s[p])] += lag_w
    pos_p = [{d: (pos_lag[p][d] + 0.1)/(sum(pos_lag[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    cand.append((pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3], f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_10_ensemble(history, *args):
    r1 = [item['number'] for item in formula_01_hot_position(history)]
    r2 = [item['number'] for item in formula_05_weighted_ema(history)]
    r3 = [item['number'] for item in formula_08_parity_scale(history)]
    r4 = [item['number'] for item in formula_07_mirror_synergy(history)]
    score_borda = defaultdict(float)
    for r_list, w in [(r1, 3.0), (r2, 2.5), (r3, 2.0), (r4, 1.5)]:
        for rank, num in enumerate(r_list, start=1):
            score_borda[num] += (11 - rank) * w
    top = sorted(score_borda.items(), key=lambda x: x[1], reverse=True)
    return format_recs_std([item[0] for item in top])

def formula_11_bayesian(history, *args):
    total_draws = len(history)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_alphas = defaultdict(lambda: 0.5)
    for idx, d in enumerate(history):
        rec_f = 1.0 + (idx / total_draws) * 0.8
        for s, tw in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 2.8), (d.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in d.get('special_prizes', [])] + [(x, 0.6) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tw * rec_f
                for pos in range(4): pos_alphas[pos][int(s[pos])] += w
                pair_alphas[(int(s[0]), int(s[1]))] += w * 0.5
                pair_alphas[(int(s[2]), int(s[3]))] += w * 0.5
    post_p = [{d: pos_alphas[pos][d] / sum(pos_alphas[pos].values()) for d in range(10)} for pos in range(4)]
    tot_pair_alpha = sum(pair_alphas.values()) or 1.0
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    pf = pair_alphas.get((d0, d1), 0.5) / tot_pair_alpha
                    pb = pair_alphas.get((d2, d3), 0.5) / tot_pair_alpha
                    log_p = (math.log(post_p[0][d0]) + math.log(post_p[1][d1]) + math.log(post_p[2][d2]) + math.log(post_p[3][d3]) + 0.3*math.log(pf) + 0.3*math.log(pb))
                    cand.append((log_p, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_12_trigram(history, *args):
    unigram = defaultdict(float)
    bigram_01 = defaultdict(float)
    trigram_012 = defaultdict(float)
    trigram_123 = defaultdict(float)
    for d in history:
        for s, w in [(d.get('1st_prize'), 3.5), (d.get('2nd_prize'), 2.5), (d.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in d.get('special_prizes', [])] + [(x, 0.8) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                d0, d1, d2, d3 = int(s[0]), int(s[1]), int(s[2]), int(s[3])
                unigram[d0] += w
                bigram_01[(d0, d1)] += w
                trigram_012[(d0, d1, d2)] += w
                trigram_123[(d1, d2, d3)] += w
    tot_u = sum(unigram.values()) or 1.0
    cand = []
    for d0 in range(10):
        p_d0 = (unigram[d0] + 0.1) / (tot_u + 1.0)
        for d1 in range(10):
            p_d1 = (bigram_01.get((d0, d1), 0.0) + 0.05) / (unigram[d0] + 1.0)
            for d2 in range(10):
                p_d2 = (trigram_012.get((d0, d1, d2), 0.0) + 0.02) / (bigram_01.get((d0, d1), 0.0) + 0.5)
                for d3 in range(10):
                    p_d3 = (trigram_123.get((d1, d2, d3), 0.0) + 0.02) / (bigram_01.get((d1, d2), 0.0) + 0.5)
                    cand.append((p_d0 * p_d1 * p_d2 * p_d3, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_13_yield_maximizer(history, *args):
    pos_w = [defaultdict(float) for _ in range(4)]
    pair_w = defaultdict(float)
    double_freq = defaultdict(float)
    tot_d = len(history)
    for idx, d in enumerate(history):
        tw = 1.0 + (idx / tot_d) * 0.5
        for s, tier_w in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 2.8), (d.get('3rd_prize'), 2.0)] + [(x, 1.2) for x in d.get('special_prizes', [])] + [(x, 0.8) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tier_w * tw
                counts = Counter(s)
                for digit, cnt in counts.items():
                    if cnt >= 2: double_freq[int(digit)] += w * cnt
                for p in range(4): pos_w[p][int(s[p])] += w
                pair_w[(int(s[0]), int(s[1]))] += w
                pair_w[(int(s[2]), int(s[3]))] += w
    pos_p = [{d: (pos_w[p][d] + 0.1)/(sum(pos_w[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    tot_pair_w = sum(pair_w.values()) or 1.0
    tot_double_w = sum(double_freq.values()) or 1.0
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    ym = 24.0 / perms
                    bp = pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3]
                    pf = (pair_w.get((d0, d1), 0.0) + 0.01) / tot_pair_w
                    pb = (pair_w.get((d2, d3), 0.0) + 0.01) / tot_pair_w
                    db = 1.0
                    for digit in set([d0, d1, d2, d3]):
                        if [d0, d1, d2, d3].count(digit) >= 2:
                            db += (double_freq.get(digit, 0.0) / tot_double_w) * 2.0
                    cand.append((bp * (pf**0.25) * (pb**0.25) * ym * db, num_str))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

class KalmanTracker:
    def __init__(self):
        self.x, self.v = 4.5, 0.0
        self.p00, self.p01, self.p10, self.p11 = 5.0, 0.0, 0.0, 1.0
        self.q, self.r = 0.6, 2.5
    def update(self, z):
        xp = self.x + self.v
        p00p = self.p00 + self.p01 + self.p10 + self.p11 + self.q
        diff = (z - xp + 5) % 10 - 5
        s = p00p + self.r
        k0, k1 = p00p / s, (self.p10 + self.p11) / s
        self.x = (xp + k0 * diff) % 10.0
        self.v = self.v + k1 * diff
        self.p00 = (1.0 - k0) * p00p
    def predict(self):
        return (self.x + self.v) % 10.0, max(self.p00 + self.q, 0.5)

def formula_14_kalman(history, *args):
    trackers = [KalmanTracker() for _ in range(4)]
    for d in history:
        p1 = str(d.get('1st_prize', '')).strip()
        if len(p1) == 4 and p1.isdigit():
            for p in range(4): trackers[p].update(float(p1[p]))
    pos_dists = [{} for _ in range(4)]
    for p in range(4):
        mu, var = trackers[p].predict()
        sig = math.sqrt(var)
        for d in range(10):
            dist = abs((d - mu + 5) % 10 - 5)
            pos_dists[p][d] = math.exp(-(dist**2)/(2 * (sig**2)))
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    cand.append((pos_dists[0][d0] * pos_dists[1][d1] * pos_dists[2][d2] * pos_dists[3][d3], f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_15_cluster_affinity(history, *args):
    pos_w = [defaultdict(float) for _ in range(4)]
    pair_aff = defaultdict(float)
    trip_aff = defaultdict(float)
    tot_d = len(history)
    for idx, d in enumerate(history):
        rec_w = 1.0 + (idx / tot_d) * 0.6
        for s, tw in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 2.8), (d.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in d.get('special_prizes', [])] + [(x, 0.8) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tw * rec_w
                dg = [int(c) for c in s]
                for p in range(4): pos_w[p][dg[p]] += w
                for p1 in range(4):
                    for p2 in range(p1 + 1, 4):
                        pair_aff[tuple(sorted([dg[p1], dg[p2]]))] += w
                        for p3 in range(p2 + 1, 4):
                            trip_aff[tuple(sorted([dg[p1], dg[p2], dg[p3]]))] += w
    pos_p = [{d: (pos_w[p][d] + 0.1)/(sum(pos_w[p].values()) + 1.0) for d in range(10)} for p in range(4)]
    tot_p_aff = sum(pair_aff.values()) or 1.0
    tot_t_aff = sum(trip_aff.values()) or 1.0
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    dg = [d0, d1, d2, d3]
                    ps = pos_p[0][d0] * pos_p[1][d1] * pos_p[2][d2] * pos_p[3][d3]
                    ascore = sum(pair_aff.get(tuple(sorted([dg[p1], dg[p2]])), 0.0)/tot_p_aff for p1 in range(4) for p2 in range(p1+1, 4))
                    tscore = sum(trip_aff.get(tuple(sorted([dg[p1], dg[p2], dg[p3]])), 0.0)/tot_t_aff for p1 in range(4) for p2 in range(p1+1, 4) for p3 in range(p2+1, 4))
                    cand.append((ps * ((1.0 + ascore*2.0)**0.5) * ((1.0 + tscore*3.0)**0.5), f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    return format_recs_std([c[1] for c in cand])

def formula_16_bayesian_hybrid(history, *args):
    """Format RM15: No 1-5 (Direct+iBox), No 6-10 (iBox)"""
    total_draws = len(history)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    bigram_weights = [defaultdict(float) for _ in range(3)]
    for idx, draw in enumerate(history):
        rec_f = 1.0 + (idx / total_draws) * 0.75
        for num_str, tier_w in [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 2.8), (draw.get('3rd_prize'), 2.0)] + [(x, 1.2) for x in draw.get('special_prizes', [])] + [(x, 0.8) for x in draw.get('consolation_prizes', [])]:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * rec_f
                for pos in range(4): pos_alphas[pos][int(num_str[pos])] += w
                for bg_pos in range(3): bigram_weights[bg_pos][(int(num_str[bg_pos]), int(num_str[bg_pos+1]))] += w
    post_p = [{d: pos_alphas[pos][d] / sum(pos_alphas[pos].values()) for d in range(10)} for pos in range(4)]
    bg_p = [{k: (bigram_weights[bp][k] + 0.01) / (sum(bigram_weights[bp].values()) + 1.0) for k in bigram_weights[bp]} for bp in range(3)]
    cand = []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    sc = post_p[0][d0] * post_p[1][d1] * post_p[2][d2] * post_p[3][d3] * (bg_p[0].get((d0, d1), 0.001)**0.45) * (bg_p[1].get((d1, d2), 0.001)**0.45) * (bg_p[2].get((d2, d3), 0.001)**0.45)
                    cand.append((sc, f"{d0}{d1}{d2}{d3}"))
    cand.sort(key=lambda x: x[0], reverse=True)
    recs = []
    for rank, num in enumerate([c[1] for c in cand[:10]], start=1):
        recs.append({"rank": rank, "number": num, "bet_direct_rm": 1 if rank <= 5 else 0, "bet_ibox_rm": 1})
    return recs

def formula_17_bayesian_yield(history, *args):
    """Format RM15: No 1-5 (Direct+iBox), No 6-10 (iBox Kembar)"""
    total_draws = len(history)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_alphas = defaultdict(lambda: 0.5)
    double_counts = defaultdict(float)
    for idx, draw in enumerate(history):
        rec_f = 1.0 + (idx / total_draws) * 0.8
        for num_str, tier_w in [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 2.8), (draw.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in draw.get('special_prizes', [])] + [(x, 0.6) for x in draw.get('consolation_prizes', [])]:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tier_w * rec_f
                for d_val, freq in Counter(num_str).items():
                    if freq >= 2: double_counts[int(d_val)] += w * freq
                for pos in range(4): pos_alphas[pos][int(num_str[pos])] += w
                pair_alphas[(int(num_str[0]), int(num_str[1]))] += w * 0.5
                pair_alphas[(int(num_str[2]), int(num_str[3]))] += w * 0.5
    post_p = [{d: pos_alphas[pos][d] / sum(pos_alphas[pos].values()) for d in range(10)} for pos in range(4)]
    tot_pair_a = sum(pair_alphas.values()) or 1.0
    tot_dbl_w = sum(double_counts.values()) or 1.0
    all_c, dbl_c = [], []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    pf = pair_alphas.get((d0, d1), 0.5) / tot_pair_a
                    pb = pair_alphas.get((d2, d3), 0.5) / tot_pair_a
                    log_p = math.log(post_p[0][d0]) + math.log(post_p[1][d1]) + math.log(post_p[2][d2]) + math.log(post_p[3][d3]) + 0.3*math.log(pf) + 0.3*math.log(pb)
                    all_c.append((log_p, num_str))
                    if perms in (12, 6):
                        d_b = sum(double_counts.get(d, 0.0)/tot_dbl_w for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        dbl_c.append((log_p + math.log(24.0/perms) + 0.5*math.log(1.0 + d_b), num_str))
    all_c.sort(key=lambda x: x[0], reverse=True)
    dbl_c.sort(key=lambda x: x[0], reverse=True)
    top5 = [c[1] for c in all_c[:5]]
    top6_10 = [c[1] for c in dbl_c if c[1] not in top5][:5]
    recs = []
    for rank, num in enumerate(top5, start=1):
        recs.append({"rank": rank, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
    for rank, num in enumerate(top6_10, start=6):
        recs.append({"rank": rank, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
    return recs

def formula_18_dual_window(history, *args):
    """Format Dinamik RM18/RM11"""
    total_draws = len(history)
    short_h = history[-12:] if total_draws >= 12 else history
    long_h = history[-60:] if total_draws >= 60 else history
    pos_l = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pos_s = [{d: 0.5 for d in range(10)} for _ in range(4)]
    pair_s = defaultdict(lambda: 0.2)
    for d in long_h:
        for s, w in [(d.get('1st_prize'), 3.5), (d.get('2nd_prize'), 2.5), (d.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_l[p][int(s[p])] += w
    for idx, d in enumerate(short_h):
        wb = 1.0 + (idx / len(short_h))
        for s, w in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 3.0), (d.get('3rd_prize'), 2.0)]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                for p in range(4): pos_s[p][int(s[p])] += w * wb
                pair_s[(int(s[0]), int(s[1]))] += w * wb * 0.5
                pair_s[(int(s[2]), int(s[3]))] += w * wb * 0.5
    comb_p = [{} for _ in range(4)]
    entropy = 0.0
    for p in range(4):
        tl, ts = sum(pos_l[p].values()), sum(pos_s[p].values())
        for d in range(10):
            prob = 0.35 * (pos_l[p][d] / tl) + 0.65 * (pos_s[p][d] / ts)
            comb_p[p][d] = prob
            if prob > 0: entropy -= prob * math.log(prob)
    tot_pair_s = sum(pair_s.values()) or 1.0
    all_c, dbl_c = [], []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    pf = pair_s.get((d0, d1), 0.2) / tot_pair_s
                    pb = pair_s.get((d2, d3), 0.2) / tot_pair_s
                    lp = math.log(comb_p[0][d0]) + math.log(comb_p[1][d1]) + math.log(comb_p[2][d2]) + math.log(comb_p[3][d3]) + 0.35*math.log(pf) + 0.35*math.log(pb)
                    all_c.append((lp, num_str))
                    if perms in (12, 6): dbl_c.append((lp + math.log(24.0/perms), num_str))
    all_c.sort(key=lambda x: x[0], reverse=True)
    dbl_c.sort(key=lambda x: x[0], reverse=True)
    is_high = entropy < 8.15
    recs, seen = [], set()
    if is_high:
        for _, num in all_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 6: break
        for _, num in dbl_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 12: break
    else:
        for _, num in all_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 3: break
        for _, num in dbl_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 8: break
    return recs

def formula_19_twin_stacking(history, *args):
    """Format Dinamik RM18/RM11 Stacking"""
    total_draws = len(history)
    pos_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_clusters = defaultdict(float)
    for idx, d in enumerate(history):
        rec_f = 1.0 + (idx / total_draws) * 0.8
        for s, tw in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 3.0), (d.get('3rd_prize'), 2.0)] + [(x, 1.2) for x in d.get('special_prizes', [])] + [(x, 0.8) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tw * rec_f
                for p in range(4): pos_alphas[p][int(s[p])] += w
                if any(v >= 2 for v in Counter(s).values()):
                    pair_clusters["".join(sorted(s))] += w
    post_p = [{d: pos_alphas[pos][d] / sum(pos_alphas[pos].values()) for d in range(10)} for pos in range(4)]
    sorted_twins = sorted(pair_clusters.items(), key=lambda x: x[1], reverse=True)
    top_score = sorted_twins[0][1] if sorted_twins else 0.0
    avg_score = (sum(v for _, v in sorted_twins[:10]) / 10.0) if sorted_twins else 1.0
    is_high = (top_score / max(avg_score, 1.0)) >= 1.35
    stk_direct, stk_ibox = [], []
    for b_sig, _ in sorted_twins[:6]:
        perms = get_unique_permutations(b_sig)
        scored = sorted([(post_p[0][int(p[0])] * post_p[1][int(p[1])] * post_p[2][int(p[2])] * post_p[3][int(p[3])], p) for p in perms], key=lambda x: x[0], reverse=True)
        for _, p_num in scored:
            if p_num not in stk_direct: stk_direct.append(p_num)
        if scored and scored[0][1] not in stk_ibox: stk_ibox.append(scored[0][1])
    recs, seen = [], set()
    if is_high:
        for num in stk_direct:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 6: break
        for b_sig, _ in sorted_twins[2:15]:
            best_p = get_unique_permutations(b_sig)[0]
            if best_p not in seen: seen.add(best_p); recs.append({"rank": len(recs)+1, "number": best_p, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 12: break
    else:
        for num in stk_direct:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 3: break
        for b_sig, _ in sorted_twins[1:10]:
            best_p = get_unique_permutations(b_sig)[0]
            if best_p not in seen: seen.add(best_p); recs.append({"rank": len(recs)+1, "number": best_p, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 8: break
    return recs

def formula_20_regime_switch(history, *args):
    """Format Dinamik RM18/RM11 HMM"""
    total_draws = len(history)
    recent = history[-15:] if total_draws >= 15 else history
    twin_c, tot_c = 0, 0
    for d in recent:
        for s in [d.get('1st_prize'), d.get('2nd_prize'), d.get('3rd_prize')] + d.get('special_prizes', []) + d.get('consolation_prizes', []):
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                tot_c += 1
                if get_permutation_count(s) in (12, 6, 4): twin_c += 1
    pos_a = [{d: 1.0 for d in range(10)} for _ in range(4)]
    pair_a = defaultdict(lambda: 0.5)
    double_s = defaultdict(float)
    for idx, d in enumerate(history):
        rec_f = 1.0 + (idx / total_draws) * 0.8
        for s, tw in [(d.get('1st_prize'), 4.0), (d.get('2nd_prize'), 2.8), (d.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in d.get('special_prizes', [])] + [(x, 0.6) for x in d.get('consolation_prizes', [])]:
            s = str(s).strip()
            if len(s) == 4 and s.isdigit():
                w = tw * rec_f
                for d_val, freq in Counter(s).items():
                    if freq >= 2: double_s[int(d_val)] += w * freq
                for p in range(4): pos_a[p][int(s[p])] += w
                pair_a[(int(s[0]), int(s[1]))] += w * 0.5
                pair_a[(int(s[2]), int(s[3]))] += w * 0.5
    pos_p = [{} for _ in range(4)]
    entropy = 0.0
    for p in range(4):
        ta = sum(pos_a[p].values())
        for d in range(10):
            prob = pos_a[p][d] / ta
            pos_p[p][d] = prob
            if prob > 0: entropy -= prob * math.log(prob)
    tot_pa, tot_ds = sum(pair_a.values()) or 1.0, sum(double_s.values()) or 1.0
    is_twin_regime = ((twin_c / max(tot_c, 1)) >= 0.40) and (entropy < 8.20)
    gen_c, twn_c = [], []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    pf = pair_a.get((d0, d1), 0.5) / tot_pa
                    pb = pair_a.get((d2, d3), 0.5) / tot_pa
                    lp = math.log(pos_p[0][d0]) + math.log(pos_p[1][d1]) + math.log(pos_p[2][d2]) + math.log(pos_p[3][d3]) + 0.3*math.log(pf) + 0.3*math.log(pb)
                    gen_c.append((lp, num_str))
                    if perms in (12, 6):
                        db = sum(double_s.get(d, 0.0)/tot_ds for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        twn_c.append((lp + math.log(24.0/perms) + 0.4*math.log(1.0 + db), num_str))
    gen_c.sort(key=lambda x: x[0], reverse=True)
    twn_c.sort(key=lambda x: x[0], reverse=True)
    recs, seen = [], set()
    if is_twin_regime:
        for _, num in gen_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 6: break
        for _, num in twn_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 12: break
    else:
        for _, num in gen_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 3: break
        for _, num in twn_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 8: break
    return recs

def formula_21_day_conditional(history, target_date_str):
    """Format Dinamik RM18/RM11 Mengikut Hari Cabutan"""
    target_dt = parse_date(target_date_str)
    target_weekday = target_dt.weekday()
    total_draws = len(history)
    global_alphas = [{d: 1.0 for d in range(10)} for _ in range(4)]
    day_alphas = [{d: 0.5 for d in range(10)} for _ in range(4)]
    day_pair_a = defaultdict(lambda: 0.2)
    day_double_s = defaultdict(float)
    day_draw_count = 0
    for idx, draw in enumerate(history):
        d_date = parse_date(draw.get('date', ''))
        is_same = (d_date.weekday() == target_weekday)
        if is_same: day_draw_count += 1
        rec_f = 1.0 + (idx / total_draws) * 0.75
        for num_str, tw in [(draw.get('1st_prize'), 4.0), (draw.get('2nd_prize'), 2.8), (draw.get('3rd_prize'), 2.0)] + [(x, 1.0) for x in draw.get('special_prizes', [])] + [(x, 0.6) for x in draw.get('consolation_prizes', [])]:
            num_str = str(num_str).strip()
            if len(num_str) == 4 and num_str.isdigit():
                w = tw * rec_f
                for p in range(4): global_alphas[p][int(num_str[p])] += w
                if is_same:
                    for p in range(4): day_alphas[p][int(num_str[p])] += w * 1.5
                    day_pair_a[(int(num_str[0]), int(num_str[1]))] += w * 0.6
                    day_pair_a[(int(num_str[2]), int(num_str[3]))] += w * 0.6
                    for d_val, freq in Counter(num_str).items():
                        if freq >= 2: day_double_s[int(d_val)] += w * freq
    final_p = [{} for _ in range(4)]
    for p in range(4):
        tg, td = sum(global_alphas[p].values()), sum(day_alphas[p].values())
        for d in range(10):
            final_p[p][d] = 0.70 * (day_alphas[p][d] / td) + 0.30 * (global_alphas[p][d] / tg)
    tot_pa, tot_ds = sum(day_pair_a.values()) or 1.0, sum(day_double_s.values()) or 1.0
    is_high = (day_draw_count >= 10) and (target_weekday in (2, 5, 6))
    gen_c, twn_c = [], []
    for d0 in range(10):
        for d1 in range(10):
            for d2 in range(10):
                for d3 in range(10):
                    num_str = f"{d0}{d1}{d2}{d3}"
                    perms = get_permutation_count(num_str)
                    pf = day_pair_a.get((d0, d1), 0.2) / tot_pa
                    pb = day_pair_a.get((d2, d3), 0.2) / tot_pa
                    lp = math.log(final_p[0][d0]) + math.log(final_p[1][d1]) + math.log(final_p[2][d2]) + math.log(final_p[3][d3]) + 0.35*math.log(pf) + 0.35*math.log(pb)
                    gen_c.append((lp, num_str))
                    if perms in (12, 6):
                        db = sum(day_double_s.get(d, 0.0)/tot_ds for d in set([d0, d1, d2, d3]) if [d0, d1, d2, d3].count(d) >= 2)
                        twn_c.append((lp + math.log(24.0/perms) + 0.45*math.log(1.0 + db), num_str))
    gen_c.sort(key=lambda x: x[0], reverse=True)
    twn_c.sort(key=lambda x: x[0], reverse=True)
    recs, seen = [], set()
    if is_high:
        for _, num in gen_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 6: break
        for _, num in twn_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 12: break
    else:
        for _, num in gen_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 1, "bet_ibox_rm": 1})
            if len(recs) == 3: break
        for _, num in twn_c:
            if num not in seen: seen.add(num); recs.append({"rank": len(recs)+1, "number": num, "bet_direct_rm": 0, "bet_ibox_rm": 1})
            if len(recs) == 8: break
    return recs

# ==========================================
# SENARAI LENGKAP 21 FORMULA
# ==========================================
FORMULAS = [
    ("01", "01_hot_position_matrix", "Hot Position Matrix", formula_01_hot_position),
    ("02", "02_cold_gap_cycle", "Cold Gap Poisson", formula_02_cold_gap),
    ("03", "03_markov_digit_chain", "Markov Transition", formula_03_markov_chain),
    ("04", "04_sum_root_balance", "Sum & Root Bell", formula_04_sum_root),
    ("05", "05_weighted_decay_ema", "Weighted Decay EMA", formula_05_weighted_ema),
    ("06", "06_delta_mean_reversion", "Delta Reversion", formula_06_delta_reversion),
    ("07", "07_top3_mirror_pairing", "Top 3 Mirror Synergy", formula_07_mirror_synergy),
    ("08", "08_parity_scale_filter", "Parity High-Low", formula_08_parity_scale),
    ("09", "09_lag_autocorrelation", "Lag Autocorrelation", formula_09_lag_autocorr),
    ("10", "10_ensemble_meta_scorer", "Ensemble Meta Scorer", formula_10_ensemble),
    ("11", "11_bayesian_posterior_opt", "Bayesian Likelihood", formula_11_bayesian),
    ("12", "12_trigram_markov_field", "Trigram Markov Field", formula_12_trigram),
    ("13", "13_permutation_yield_maximizer", "Permutation Yield Opt", formula_13_yield_maximizer),
    ("14", "14_kalman_position_velocity", "Kalman Position Drift", formula_14_kalman),
    ("15", "15_box_cluster_affinity", "Box Cluster Affinity", formula_15_cluster_affinity),
    ("16", "16_bayesian_position_hybrid", "Bayesian-Position Hybrid", formula_16_bayesian_hybrid),
    ("17", "17_bayesian_pair_yield", "Bayesian Double-Yield", formula_17_bayesian_yield),
    ("18", "18_dual_window_bayesian_momentum", "Dual-Window Momentum", formula_18_dual_window),
    ("19", "19_twin_box_permutation_stacking", "Twin-Box Stacking", formula_19_twin_stacking),
    ("20", "20_dynamic_regime_switching", "Regime Switching HMM", formula_20_regime_switch),
    ("21", "21_draw_day_conditional_priors", "Day Conditional Priors", formula_21_day_conditional),
]

# ==========================================
# MASTER RUNNER & PELAPORAN TERMINAL
# ==========================================
def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    header_text = Text("⚡ TOTO 4D MASTER BENCHMARK ENGINE (21 FORMULA MATEMATIK) ⚡", style="bold yellow", justify="center")
    sub_text = Text("Simulasi Walk-Forward 6 Bulan | Ujian Standard, Target Yield & Taruhan Dinamik", style="cyan", justify="center")
    console.print(Panel(Text.assemble(header_text, "\n", sub_text), border_style="bright_blue", box=box.ROUNDED))

    if not os.path.exists(DATA_FILE):
        console.print(f"[bold red]❌ Ralat: Fail data tidak ditemui di '{DATA_FILE}'[/bold red]")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        draws = json.load(f)

    draws.sort(key=lambda x: parse_date(x.get('date', '')))
    total_records = len(draws)
    
    if total_records < 20:
        console.print(f"[bold red]❌ Data tidak mencukupi: {total_records} rekod sahaja.[/bold red]")
        return

    split_idx = total_records // 2
    training_set = draws[:split_idx]
    testing_set = draws[split_idx:]
    
    start_date = testing_set[0].get('date', 'N/A')
    end_date = testing_set[-1].get('date', 'N/A')

    info_table = Table(box=box.SIMPLE_HEAVY, show_header=False, pad_edge=False)
    info_table.add_column("Key", style="bold white")
    info_table.add_column("Val", style="bold green")
    info_table.add_row("📊 Jumlah Data Sejarah", f"{total_records} sesi cabutan")
    info_table.add_row("🏋️  Fasa Latihan (Warm-up)", f"{len(training_set)} sesi pertama (~6 bulan)")
    info_table.add_row("🎯 Fasa Ujian (Backtesting)", f"{len(testing_set)} sesi terkini ({start_date} -> {end_date})")
    info_table.add_row("💰 Strategi Taruhan Diuji", "Standard (RM13), Top-5 Cover (RM15), Dinamik Entropi (RM11/RM18)")
    console.print(Panel(info_table, title="[bold white]Parameter Benchmark Penuh[/bold white]", border_style="cyan"))

    results_summary = []

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=30, style="grey37", complete_style="bright_green"),
        TextColumn("[bold yellow]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        main_task = progress.add_task("[yellow]Menilai 21 Formula...", total=len(FORMULAS))
        
        for f_no, f_id, f_name, f_func in FORMULAS:
            task = progress.add_task(f"[cyan]Testing [{f_no}] {f_name}...", total=len(testing_set))
            
            total_invested = 0.0
            total_won = 0.0
            total_hits = 0
            best_win = 0.0
            latest_payload = None
            
            for i, curr_draw in enumerate(testing_set):
                target_date = curr_draw.get('date', '')
                history_window = draws[:split_idx + i]
                
                # Panggilan fungsi dengan parameter sejarah & tarikh sasaran
                recs = f_func(history_window, target_date)
                
                # Kiraan kos dinamik berasaskan setiap rekod pertaruhan yang dijana
                cost = sum(item['bet_direct_rm'] + item['bet_ibox_rm'] for item in recs)
                winnings, hits = evaluate_draw(recs, curr_draw)
                
                total_invested += cost
                total_won += winnings
                if hits > 0:
                    total_hits += 1
                if winnings > best_win:
                    best_win = winnings
                    
                latest_payload = {
                    "formula_id": f_id,
                    "formula_name": f_name,
                    "target_date": target_date,
                    "draw_no": curr_draw.get('draw_no'),
                    "budget_total_rm": cost,
                    "recommendations": recs
                }
                
                progress.update(task, advance=1)
                
            progress.remove_task(task)
            progress.update(main_task, advance=1)
            
            temp_path = os.path.join(TEMP_DIR, f"recommendations_{f_id}.json")
            with open(temp_path, 'w', encoding='utf-8') as f_out:
                json.dump(latest_payload, f_out, indent=4)
                
            net_profit = total_won - total_invested
            roi_pct = (net_profit / total_invested * 100) if total_invested > 0 else 0.0
            hit_rate = (total_hits / len(testing_set) * 100) if len(testing_set) > 0 else 0.0
            
            results_summary.append({
                "no": f_no,
                "id": f_id,
                "name": f_name,
                "modal": total_invested,
                "menang": total_won,
                "untung": net_profit,
                "roi": roi_pct,
                "hits": total_hits,
                "hit_rate": hit_rate,
                "best_win": best_win
            })

    # Susun ikut ranking ROI tertinggi
    results_summary.sort(key=lambda x: x['roi'], reverse=True)

    result_table = Table(
        title="🏆 PAPAN PRESTASI PELABURAN 6 BULAN (KESEMUA 21 FORMULA)",
        box=box.ROUNDED,
        header_style="bold bright_white on blue",
        title_style="bold yellow",
        show_lines=True
    )

    result_table.add_column("Ked", justify="center", style="bold white", width=4)
    result_table.add_column("Formula", style="bold cyan", width=25)
    result_table.add_column("Modal (RM)", justify="right", style="white", width=11)
    result_table.add_column("Menang (RM)", justify="right", style="bright_green", width=12)
    result_table.add_column("Untung Bersih (RM)", justify="right", width=18)
    result_table.add_column("ROI (%)", justify="right", width=12)
    result_table.add_column("Hit Rate", justify="center", style="bright_yellow", width=14)
    result_table.add_column("Kemenangan Max", justify="right", style="magenta", width=15)

    for rank, res in enumerate(results_summary, start=1):
        if res['untung'] > 0:
            net_str = f"[bold bright_green]+RM {res['untung']:,.2f}[/bold bright_green]"
            roi_str = f"[bold bright_green]+{res['roi']:.2f}% 🚀[/bold bright_green]"
        elif res['untung'] == 0:
            net_str = f"[bold white] RM {res['untung']:,.2f}[/bold white]"
            roi_str = f"[bold white] {res['roi']:.2f}%[/bold white]"
        else:
            net_str = f"[bold bright_red]-RM {abs(res['untung']):,.2f}[/bold bright_red]"
            roi_str = f"[bold bright_red]{res['roi']:.2f}% 🔻[/bold bright_red]"
            
        badge = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"{rank:02d}"))

        result_table.add_row(
            badge,
            f"[{res['no']}] {res['name']}",
            f"RM {res['modal']:,.2f}",
            f"RM {res['menang']:,.2f}",
            net_str,
            roi_str,
            f"{res['hits']}/{len(testing_set)} ({res['hit_rate']:.1f}%)",
            f"RM {res['best_win']:,.2f}"
        )

    console.print(result_table)

    best = results_summary[0]
    best_panel = Panel(
        Text.assemble(
            ("🌟 FORMULA TERBAIK KESELURUHAN (CHAMPION): ", "bold yellow"),
            (f"[{best['no']}] {best['name']}\n", "bold bright_cyan"),
            (f"💰 Untung Bersih: RM {best['untung']:+,.2f}  |  ", "bold white"),
            (f"📈 ROI: {best['roi']:+.2f}%  |  ", "bold bright_green" if best['roi'] >= 0 else "bold red"),
            (f"🎯 Hit Rate: {best['hit_rate']:.1f}% ({best['hits']}/{len(testing_set)} cabutan)  |  ", "bold bright_yellow"),
            (f"💎 Max Single Win: RM {best['best_win']:,.2f}", "bold magenta")
        ),
        title="[bold green]Keputusan Penanda Aras Tertinggi[/bold green]",
        border_style="bright_green",
        box=box.DOUBLE
    )
    console.print(best_panel)

if __name__ == "__main__":
    main()
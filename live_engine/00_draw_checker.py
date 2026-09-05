#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & DRAW VERIFICATION
MODULE       : 00_draw_checker.py
DESCRIPTION  : Mengutip data cabutan terkini (1 minggu), membandingkan dengan 
               cadangan Formula 18, 20, 36, 37, 39 & 42, mengira kemenangan 
               (Direct Big & iBox Big), membuat perbandingan simulasi bajet
               jimat (RM10 & RM15) bagi F42, dan menghantar laporan ke Telegram.
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import re
import json
import time
import math
from collections import Counter
from datetime import datetime, timedelta
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ==========================================
# KONFIGURASI DIREKTORI & PERSEKITARAN (.ENV)
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMP_DIR = os.path.join(BASE_DIR, "live_engine", "temp")
ROOT_TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(ROOT_TEMP_DIR, exist_ok=True)

ENV_LOCAL = os.path.join(BASE_DIR, ".env.local")
ENV_DEFAULT = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_LOCAL):
    load_dotenv(ENV_LOCAL)
elif os.path.exists(ENV_DEFAULT):
    load_dotenv(ENV_DEFAULT)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FILE_FORMULA_18 = os.path.join(TEMP_DIR, "18_dual_window_bayesian_momentum.json")
FILE_FORMULA_20 = os.path.join(TEMP_DIR, "20_dynamic_regime_switching.json")
FILE_FORMULA_36 = os.path.join(TEMP_DIR, "36_tuned_dynamic_ema_gate.json")
FILE_FORMULA_37 = os.path.join(ROOT_TEMP_DIR, "recommendations_37_ensemble_multi_regime_ibox.json")
FILE_FORMULA_39 = os.path.join(ROOT_TEMP_DIR, "recommendations_39_ensemble_hybrid_direct_ibox.json")
FILE_FORMULA_42 = os.path.join(ROOT_TEMP_DIR, "recommendations_42_ensemble_hybrid_direct_ibox.json")
REPORT_OUTPUT_FILE = os.path.join(TEMP_DIR, "draw_checker_report.json")

BASE_URL = "https://4d4d.co/result"

# ==========================================
# STRUKTUR PEMBAYARAN RASMI (BIG FORECAST)
# ==========================================
PAYOUT_DIRECT_BIG = {
    '1st': 2500.0,
    '2nd': 1000.0,
    '3rd': 500.0,
    'special': 180.0,
    'consolation': 60.0
}

PAYOUT_IBOX_BIG = {
    24: {'1st': 105.0, '2nd': 42.0,  '3rd': 21.0,  'special': 8.0,  'consolation': 3.0},
    12: {'1st': 209.0, '2nd': 84.0,  '3rd': 42.0,  'special': 15.0, 'consolation': 5.0},
    6:  {'1st': 417.0, '2nd': 167.0, '3rd': 84.0,  'special': 30.0, 'consolation': 10.0},
    4:  {'1st': 625.0, '2nd': 250.0, '3rd': 125.0, 'special': 45.0, 'consolation': 15.0},
}


def get_permutation_count(num_str):
    """Mengira bilangan permutasi (24, 12, 6, 4, 1)."""
    counts = Counter(str(num_str)).values()
    denom = 1
    for c in counts:
        denom *= math.factorial(c)
    return math.factorial(4) // denom


def extract_4d_number(element):
    if not element:
        return None
    text = re.sub(r'\D', '', element.get_text())
    return text if len(text) == 4 else None


def parse_toto_box(toto_box, date_str):
    draw_node = toto_box.find("td", id="mdn")
    draw_no = "N/A"
    if draw_node:
        m = re.search(r'[\d-]+', draw_node.get_text())
        if m:
            draw_no = m.group(0)

    p1 = extract_4d_number(toto_box.find("td", id="mp1"))
    p2 = extract_4d_number(toto_box.find("td", id="mp2"))
    p3 = extract_4d_number(toto_box.find("td", id="mp3"))

    if not p1:
        all_nums = re.findall(r'\b\d{4}\b', toto_box.get_text())
        if len(all_nums) >= 3:
            p1, p2, p3 = all_nums[0], all_nums[1], all_nums[2]
            specials = all_nums[3:13] if len(all_nums) >= 13 else []
            consolations = all_nums[13:23] if len(all_nums) >= 23 else []
            return {
                "date": date_str, "draw_no": draw_no,
                "1st_prize": p1, "2nd_prize": p2, "3rd_prize": p3,
                "special_prizes": specials, "consolation_prizes": consolations
            }
        return None

    specials, consolations = [], []
    for table in toto_box.find_all("table"):
        txt = table.get_text()
        cells = [extract_4d_number(c) for c in table.find_all("td", id="ms1")]
        valid = [c for c in cells if c]
        if "Special" in txt or "特別獎" in txt:
            specials.extend(valid)
        elif "Consolation" in txt or "安慰獎" in txt:
            consolations.extend(valid)

    return {
        "date": date_str, "draw_no": draw_no,
        "1st_prize": p1, "2nd_prize": p2 or "N/A", "3rd_prize": p3 or "N/A",
        "special_prizes": specials, "consolation_prizes": consolations
    }


def fetch_latest_draw(days=7):
    """Mengutip keputusan Sports Toto 4D untuk tempoh 7 hari terkini."""
    print(f"[🔍] Mengutip keputusan terkini dari 4d4d.co ({days} hari)...")
    session = cffi_requests.Session(impersonate="chrome120")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    now = datetime.now()
    dates_to_check = [now - timedelta(days=i) for i in range(days)]

    for dt in dates_to_check:
        formatted_slash = dt.strftime("%d/%m/%Y")
        for fmt in (dt.strftime("%d-%m-%Y"), dt.strftime("%Y-%m-%d")):
            url = f"{BASE_URL}/{fmt}.html"
            try:
                res = session.get(url, headers=headers, timeout=8)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    for box in soup.find_all("div", class_="outerbox"):
                        if "Toto" in box.get_text():
                            draw_data = parse_toto_box(box, formatted_slash)
                            if draw_data and draw_data.get("1st_prize") != "N/A":
                                print(f"[+] Keputusan rasmi ditemui: {formatted_slash} (Draw #{draw_data['draw_no']})")
                                return draw_data
            except Exception:
                continue
    return None


def evaluate_predictions(recs, actual_draw):
    """Menyemak kenaan dan mengira jumlah kemenangan."""
    p1 = str(actual_draw.get('1st_prize', '')).strip()
    p2 = str(actual_draw.get('2nd_prize', '')).strip()
    p3 = str(actual_draw.get('3rd_prize', '')).strip()
    specials = [str(x).strip() for x in actual_draw.get('special_prizes', [])]
    consolations = [str(x).strip() for x in actual_draw.get('consolation_prizes', [])]

    total_winnings = 0.0
    hit_logs = []

    for item in recs:
        rank = item.get('rank', 0)
        num = str(item.get('number', '')).strip()
        bet_direct = item.get('bet_direct_rm', 0)
        bet_ibox = item.get('bet_ibox_rm', 0)

        # Keserasian fleksibel untuk Formula 37, 39 & 42
        if item.get('bet_type') == 'iBox' and bet_ibox == 0:
            bet_ibox = item.get('bet_amount_rm', 1.0)
        elif item.get('bet_type') == 'Direct' and bet_direct == 0:
            bet_direct = item.get('bet_amount_rm', 1.0)

        perms = item.get('permutation') or get_permutation_count(num)
        sorted_num = "".join(sorted(num))

        # 1. Semakan Hadiah Tepat (Direct Big)
        if bet_direct > 0:
            if num == p1:
                win = PAYOUT_DIRECT_BIG['1st'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 1st Prize", "rank": rank, "number": num, "win_rm": win, "bet_kind": "Direct"})
            elif num == p2:
                win = PAYOUT_DIRECT_BIG['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 2nd Prize", "rank": rank, "number": num, "win_rm": win, "bet_kind": "Direct"})
            elif num == p3:
                win = PAYOUT_DIRECT_BIG['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 3rd Prize", "rank": rank, "number": num, "win_rm": win, "bet_kind": "Direct"})
            elif num in specials:
                win = PAYOUT_DIRECT_BIG['special'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": f"Direct Special ({num})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "Direct"})
            elif num in consolations:
                win = PAYOUT_DIRECT_BIG['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": f"Direct Consolation ({num})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "Direct"})

        # 2. Semakan Hadiah Permutasi (iBox Big)
        if bet_ibox > 0 and perms in PAYOUT_IBOX_BIG:
            rates = PAYOUT_IBOX_BIG[perms]
            if "".join(sorted(p1)) == sorted_num:
                win = rates['1st'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 1st Prize ({p1})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "iBox"})
            if "".join(sorted(p2)) == sorted_num:
                win = rates['2nd'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 2nd Prize ({p2})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "iBox"})
            if "".join(sorted(p3)) == sorted_num:
                win = rates['3rd'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 3rd Prize ({p3})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "iBox"})
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = rates['special'] * bet_ibox
                    total_winnings += win
                    hit_logs.append({"type": f"iBox Special ({sp})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "iBox"})
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = rates['consolation'] * bet_ibox
                    total_winnings += win
                    hit_logs.append({"type": f"iBox Consolation ({cs})", "rank": rank, "number": num, "win_rm": win, "bet_kind": "iBox"})

    return total_winnings, hit_logs


def send_telegram_message(text_message):
    if not BOT_TOKEN or not CHAT_ID:
        print("[-] Ralat: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak dijumpai.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=12).json()
        if res.get("ok"):
            print("[+] Notifikasi Telegram berjaya dihantar!")
            return True
        else:
            print(f"[-] Ralat Telegram API: {res}")
    except Exception as e:
        print(f"[-] Ralat penghantaran: {e}")
    return False


def build_result_message(formula_title, payload, actual_draw, winnings, hits):
    total_cost = payload.get("budget_total_rm", 0.0)
    net_profit = winnings - total_cost
    draw_no = actual_draw.get("draw_no", "N/A")
    draw_date = actual_draw.get("date", "N/A")
    
    status_icon = "🎉🔥 <b>MENANG! (JACKPOT/HIT)</b>" if winnings > 0 else "💤 <b>TIADA KENAAN (LOSS)</b>"

    lines = [
        "🏁 <b>SPORTS TOTO 4D — KEPUTUSAN SEMAKAN LIVE</b> 🏁",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>Formula:</b> <code>{formula_title}</code>",
        f"📅 <b>Keputusan Rasmi:</b> <code>Draw #{draw_no} ({draw_date})</code>",
        f"🥇 <b>1st:</b> <code>{actual_draw.get('1st_prize')}</code> │ 🥈 <b>2nd:</b> <code>{actual_draw.get('2nd_prize')}</code> │ 🥉 <b>3rd:</b> <code>{actual_draw.get('3rd_prize')}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>Status:</b> {status_icon}",
        f"💵 <b>Modal Taruhan:</b> <code>RM {total_cost:.2f}</code>",
        f"🎁 <b>Jumlah Menang:</b> <code>RM {winnings:.2f}</code>",
        f"📈 <b>Untung / Rugi Bersih:</b> <b>RM {net_profit:+.2f}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if hits:
        lines.append("🎯 <b>PERINCIAN KENAAN HADIAH:</b>")
        for h in hits:
            lines.append(f"  ✅ <b>#{h['rank']:02d}</b> (<code>{h['number']}</code>) 👉 <b>{h['type']}</b> (+RM {h['win_rm']:.2f})")
    else:
        lines.append("<i>Tiada nombor cadangan yang mengena pada sesi cabutan ini.</i>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Disemak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>")
    return "\n".join(lines)


def build_result_message_formula_37(payload, actual_draw, winnings, hits):
    """Menjana laporan semakan bertema khas untuk Formula 37 Ensemble Master."""
    total_cost = payload.get("budget_rm", payload.get("budget_total_rm", 20.0))
    net_profit = winnings - total_cost
    draw_no = actual_draw.get("draw_no", "N/A")
    draw_date = actual_draw.get("date", "N/A")
    meta = payload.get("meta_signals", {})
    regime = meta.get("regime_status", "EXPONENTIAL-BALANCED")
    
    if winnings > 0:
        status_icon = "🎉💎 <b>MENANG / PROFIT! TAHNIAH!</b>"
        profit_text = f"<b>+RM {net_profit:,.2f}</b>"
    else:
        status_icon = "💤🌧️ <b>TIADA KENAAN (LOSS)</b>"
        profit_text = f"<b>-RM {abs(net_profit):,.2f}</b>"

    lines = [
        "🏆 <b>SPORTS TOTO 4D — SEMAKAN LIVE FORMULA 37</b> 🏆",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🚀 <b>Ensemble Master (Multi-Regime & Asymmetric iBox V2)</b>",
        f"📅 <b>Keputusan Rasmi:</b> <code>Draw #{draw_no} ({draw_date})</code>",
        f"🥇 <b>1st:</b> <code>{actual_draw.get('1st_prize')}</code> │ 🥈 <b>2nd:</b> <code>{actual_draw.get('2nd_prize')}</code> │ 🥉 <b>3rd:</b> <code>{actual_draw.get('3rd_prize')}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>Status Keputusan:</b> {status_icon}",
        f"🌐 <b>Rejim Pasaran:</b> <code>{regime}</code>",
        f"💵 <b>Modal Taruhan:</b> <code>RM {total_cost:.2f}</code> (20 Nombor iBox RM1)",
        f"🎁 <b>Jumlah Pulangan:</b> <b>RM {winnings:.2f}</b>",
        f"📈 <b>Untung / Rugi Bersih:</b> {profit_text}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if hits:
        lines.append("🎯 <b>PERINCIAN KENAAN iBOX RASMI:</b>")
        for h in hits:
            lines.append(f"  ✨ <b>Rank #{h['rank']:02d}</b> (<code>{h['number']}</code>) ➔ <b>{h['type']}</b> (+RM {h['win_rm']:.2f})")
    else:
        lines.append("<i>Tiada kenaan bagi 20 nombor cadangan Formula 37 pada cabutan ini.</i>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Disemak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>")
    return "\n".join(lines)


def build_result_message_formula_39(payload, actual_draw, winnings, hits):
    """Menjana format laporan semakan eksklusif untuk Formula 39 (Hybrid Direct & iBox Portfolio RM25)."""
    total_cost = payload.get("budget_rm", payload.get("budget_total_rm", 25.0))
    net_profit = winnings - total_cost
    draw_no = actual_draw.get("draw_no", "N/A")
    draw_date = actual_draw.get("date", "N/A")
    meta = payload.get("meta_signals", {})
    regime = meta.get("regime_status", "EXPONENTIAL-BALANCED")
    twin_ratio = meta.get("twin_ratio", 0.0)

    had_direct = any("Direct" in h.get("type", "") for h in hits)

    if winnings > 0:
        if had_direct:
            status_icon = "💥🎯 <b>JACKPOT DIRECT HIT! TAHNIAH!</b>"
        else:
            status_icon = "🎉💎 <b>MENANG iBOX / PROFIT!</b>"
        profit_text = f"<b>+RM {net_profit:,.2f}</b>"
    else:
        status_icon = "💤🌧️ <b>TIADA KENAAN (LOSS)</b>"
        profit_text = f"<b>-RM {abs(net_profit):,.2f}</b>"

    lines = [
        "👑 <b>SPORTS TOTO 4D — SEMAKAN LIVE FORMULA 39</b> 👑",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🏆 <b>Hybrid Portfolio Master (Direct & iBox RM25)</b>",
        f"📅 <b>Keputusan Rasmi:</b> <code>Draw #{draw_no} ({draw_date})</code>",
        f"🥇 <b>1st:</b> <code>{actual_draw.get('1st_prize')}</code> │ 🥈 <b>2nd:</b> <code>{actual_draw.get('2nd_prize')}</code> │ 🥉 <b>3rd:</b> <code>{actual_draw.get('3rd_prize')}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>Status Keputusan:</b> {status_icon}",
        f"🌐 <b>Rejim Pasaran:</b> <code>{regime}</code> (Twin: <code>{twin_ratio*100:.1f}%</code>)",
        f"💵 <b>Modal Taruhan:</b> <code>RM {total_cost:.2f}</code> (4 Direct + 21 iBox)",
        f"🎁 <b>Jumlah Pulangan:</b> <b>RM {winnings:,.2f}</b>",
        f"📈 <b>Untung / Rugi Bersih:</b> {profit_text}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if hits:
        direct_hits = [h for h in hits if "Direct" in h.get("type", "")]
        ibox_hits = [h for h in hits if "Direct" not in h.get("type", "")]

        if direct_hits:
            lines.append("💥 <b>PERINCIAN KENAAN DIRECT BIG:</b>")
            for h in direct_hits:
                lines.append(f"  🎯 <b>Rank #{h['rank']:02d}</b> (<code>{h['number']}</code>) ➔ <b>{h['type']}</b> (+RM {h['win_rm']:,.2f})")
            if ibox_hits:
                lines.append("")

        if ibox_hits:
            lines.append("🛡️ <b>PERINCIAN KENAAN iBOX BIG:</b>")
            for h in ibox_hits:
                lines.append(f"  ✨ <b>Rank #{h['rank']:02d}</b> (<code>{h['number']}</code>) ➔ <b>{h['type']}</b> (+RM {h['win_rm']:,.2f})")
    else:
        lines.append("<i>Tiada kenaan bagi 25 nombor cadangan Formula 39 pada cabutan ini.</i>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Disemak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>")
    return "\n".join(lines)


def build_result_message_formula_42(payload, actual_draw, winnings, hits):
    """
    Menjana format semakan eksklusif Formula 42 dengan perbandingan prestasi:
    1. Pelaburan Penuh (RM 25.00 - 25 Nombor)
    2. Pilihan Bajet Jimat (RM 10.00 - Top 10 Ranks)
    3. Pilihan Bajet Sederhana (RM 15.00 - Top 15 Ranks)
    """
    draw_no = actual_draw.get("draw_no", "N/A")
    draw_date = actual_draw.get("date", "N/A")
    meta = payload.get("meta_signals", {})
    regime = meta.get("regime_status", "EXPONENTIAL-BALANCED")
    twin_ratio = meta.get("twin_ratio", 0.0)
    budget_picks = payload.get("budget_picks", {})

    t10_ranks = set(budget_picks.get("tier_rm10_ranks", []))
    t15_ranks = set(budget_picks.get("tier_rm15_ranks", []))

    # 1. Kiraan Mod Penuh (RM 25)
    cost_full = payload.get("budget_rm", 25.0)
    net_full = winnings - cost_full
    roi_full = (net_full / cost_full * 100) if cost_full > 0 else 0.0

    # 2. Kiraan Mod Bajet RM 10 (Top 10)
    cost_10 = float(len(t10_ranks)) if t10_ranks else 10.0
    hits_10 = [h for h in hits if h.get("rank") in t10_ranks]
    win_10 = sum(h.get("win_rm", 0.0) for h in hits_10)
    net_10 = win_10 - cost_10
    roi_10 = (net_10 / cost_10 * 100) if cost_10 > 0 else 0.0

    # 3. Kiraan Mod Bajet RM 15 (Top 15)
    cost_15 = float(len(t15_ranks)) if t15_ranks else 15.0
    hits_15 = [h for h in hits if h.get("rank") in t15_ranks]
    win_15 = sum(h.get("win_rm", 0.0) for h in hits_15)
    net_15 = win_15 - cost_15
    roi_15 = (net_15 / cost_15 * 100) if cost_15 > 0 else 0.0

    def format_status(net_val, win_val):
        if net_val > 0:
            return "🎉 <b>UNTUNG BERSIH</b>", "bold green"
        elif win_val > 0:
            return "⚠️ <b>KURANG RUGI (HITS)</b>", "yellow"
        else:
            return "💤 <b>RUGI MODAL (LOSS)</b>", "red"

    stat_full_txt, _ = format_status(net_full, winnings)
    stat_10_txt, _ = format_status(net_10, win_10)
    stat_15_txt, _ = format_status(net_15, win_15)

    had_direct = any("Direct" in h.get("type", "") for h in hits)

    lines = [
        "🌟 <b>SPORTS TOTO 4D — SEMAKAN FORMULA 42 (FLAGSHIP)</b> 🌟",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🏆 <b>Ensemble Optimized Portfolio (Twin Overweight)</b>",
        f"📅 <b>Keputusan Rasmi:</b> <code>Draw #{draw_no} ({draw_date})</code>",
        f"🥇 <b>1st:</b> <code>{actual_draw.get('1st_prize')}</code> │ 🥈 <b>2nd:</b> <code>{actual_draw.get('2nd_prize')}</code> │ 🥉 <b>3rd:</b> <code>{actual_draw.get('3rd_prize')}</code>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 <b>PERBANDINGAN 3 MOD BAJET PELABURAN:</b>",
        "",
        "💎 <b>1. Mod Penuh (RM 25.00 — 25 Nombor):</b>",
        f"  • Pulangan: <b>RM {winnings:,.2f}</b> │ Untung: <b>RM {net_full:+,.2f}</b> ({roi_full:+.1f}%)",
        f"  • Status: {stat_full_txt}",
        "",
        "💵 <b>2. Mod Jimat (RM 10.00 — Top 10 Nombor):</b>",
        f"  • Pulangan: <b>RM {win_10:,.2f}</b> │ Untung: <b>RM {net_10:+,.2f}</b> ({roi_10:+.1f}%)",
        f"  • Status: {stat_10_txt}",
        "",
        "💵 <b>3. Mod Sederhana (RM 15.00 — Top 15 Nombor):</b>",
        f"  • Pulangan: <b>RM {win_15:,.2f}</b> │ Untung: <b>RM {net_15:+,.2f}</b> ({roi_15:+.1f}%)",
        f"  • Status: {stat_15_txt}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if hits:
        lines.append("🎯 <b>PERINCIAN KENAAN HADIAH RASMI:</b>")
        for h in hits:
            r_no = h.get("rank", 0)
            if r_no in t10_ranks:
                tier_badge = "⭐ <b>[Top 10 & 15]</b>"
            elif r_no in t15_ranks:
                tier_badge = "💡 <b>[Top 15 Sahaja]</b>"
            else:
                tier_badge = "🛡️ <b>[Portfolio Penuh]</b>"

            d_icon = "💥 [DIRECT]" if "Direct" in h.get("type", "") else "✨ [iBox]"
            lines.append(f"  {d_icon} <b>Rank #{r_no:02d}</b> (<code>{h['number']}</code>) ➔ <b>{h['type']}</b> (+RM {h['win_rm']:,.2f}) {tier_badge}")
    else:
        lines.append("<i>Tiada nombor Formula 42 yang mengena pada sesi cabutan ini.</i>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🌐 <i>Rejim: {regime} (Kembar: {twin_ratio*100:.1f}%)</i>")
    lines.append(f"⏰ <i>Disemak pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>")
    return "\n".join(lines)


def main():
    print("=" * 80)
    print(" 🚀 MEMULAKAN SEMAKAN KEPUTUSAN CABUTAN TOTO 4D (6 FORMULA)")
    print("=" * 80)

    actual_draw = fetch_latest_draw(days=7)
    if not actual_draw:
        print("[-] Tiada keputusan cabutan ditemui untuk disemak.")
        return

    full_reports = {"draw_evaluated": actual_draw, "evaluations": []}

    # 1. Semakan Formula 18
    if os.path.exists(FILE_FORMULA_18):
        with open(FILE_FORMULA_18, "r", encoding="utf-8") as f:
            data_18 = json.load(f)
        recs_18 = data_18.get("recommendations", [])
        winnings_18, hits_18 = evaluate_predictions(recs_18, actual_draw)
        msg_18 = build_result_message("Formula 18: Dual-Window Bayesian Momentum", data_18, actual_draw, winnings_18, hits_18)
        send_telegram_message(msg_18)
        full_reports["evaluations"].append({"formula": "18_dual_window_bayesian_momentum", "winnings": winnings_18, "hits": hits_18})
        time.sleep(1.5)

    # 2. Semakan Formula 20
    if os.path.exists(FILE_FORMULA_20):
        with open(FILE_FORMULA_20, "r", encoding="utf-8") as f:
            data_20 = json.load(f)
        recs_20 = data_20.get("recommendations", [])
        winnings_20, hits_20 = evaluate_predictions(recs_20, actual_draw)
        msg_20 = build_result_message("Formula 20: Dynamic Regime-Switching Gate", data_20, actual_draw, winnings_20, hits_20)
        send_telegram_message(msg_20)
        full_reports["evaluations"].append({"formula": "20_dynamic_regime_switching", "winnings": winnings_20, "hits": hits_20})
        time.sleep(1.5)

    # 3. Semakan Formula 36
    if os.path.exists(FILE_FORMULA_36):
        with open(FILE_FORMULA_36, "r", encoding="utf-8") as f:
            data_36 = json.load(f)
        recs_36 = data_36.get("recommendations", [])
        winnings_36, hits_36 = evaluate_predictions(recs_36, actual_draw)
        msg_36 = build_result_message("Formula 36: Tuned Dynamic Exponential Decay Gate", data_36, actual_draw, winnings_36, hits_36)
        send_telegram_message(msg_36)
        full_reports["evaluations"].append({"formula": "36_tuned_dynamic_ema_gate", "winnings": winnings_36, "hits": hits_36})
        time.sleep(1.5)

    # 4. Semakan Formula 37 (Ensemble Master)
    file_37_target = FILE_FORMULA_37
    if not os.path.exists(file_37_target):
        alt_37 = os.path.join(TEMP_DIR, "recommendations_37_ensemble_multi_regime_ibox.json")
        if os.path.exists(alt_37):
            file_37_target = alt_37

    if os.path.exists(file_37_target):
        with open(file_37_target, "r", encoding="utf-8") as f:
            data_37 = json.load(f)
        recs_37 = data_37.get("recommendations", [])
        winnings_37, hits_37 = evaluate_predictions(recs_37, actual_draw)
        msg_37 = build_result_message_formula_37(data_37, actual_draw, winnings_37, hits_37)
        send_telegram_message(msg_37)
        full_reports["evaluations"].append({"formula": "37_ensemble_multi_regime_ibox", "winnings": winnings_37, "hits": hits_37})
        time.sleep(1.5)
    else:
        print(f"[-] Fail Formula 37 tidak dijumpai di: {file_37_target}")

    # 5. Semakan Formula 39 (Hybrid Direct & iBox Master)
    file_39_target = FILE_FORMULA_39
    if not os.path.exists(file_39_target):
        alt_39 = os.path.join(TEMP_DIR, "recommendations_39_ensemble_hybrid_direct_ibox.json")
        if os.path.exists(alt_39):
            file_39_target = alt_39

    if os.path.exists(file_39_target):
        with open(file_39_target, "r", encoding="utf-8") as f:
            data_39 = json.load(f)
        recs_39 = data_39.get("recommendations", [])
        winnings_39, hits_39 = evaluate_predictions(recs_39, actual_draw)
        msg_39 = build_result_message_formula_39(data_39, actual_draw, winnings_39, hits_39)
        send_telegram_message(msg_39)
        full_reports["evaluations"].append({"formula": "39_ensemble_hybrid_direct_ibox", "winnings": winnings_39, "hits": hits_39})
        time.sleep(1.5)
    else:
        print(f"[-] Fail Formula 39 tidak dijumpai di: {file_39_target}")

    # 6. Semakan Formula 42 (Flagship Portfolio + Perbandingan Bajet RM10/RM15)
    file_42_target = FILE_FORMULA_42
    if not os.path.exists(file_42_target):
        alt_42 = os.path.join(TEMP_DIR, "recommendations_42_ensemble_hybrid_direct_ibox.json")
        if os.path.exists(alt_42):
            file_42_target = alt_42

    if os.path.exists(file_42_target):
        with open(file_42_target, "r", encoding="utf-8") as f:
            data_42 = json.load(f)
        recs_42 = data_42.get("recommendations", [])
        winnings_42, hits_42 = evaluate_predictions(recs_42, actual_draw)
        msg_42 = build_result_message_formula_42(data_42, actual_draw, winnings_42, hits_42)
        send_telegram_message(msg_42)
        full_reports["evaluations"].append({
            "formula": "42_ensemble_optimized_portfolio_hybrid",
            "winnings": winnings_42,
            "hits": hits_42,
            "budget_picks_evaluated": data_42.get("budget_picks", {})
        })
    else:
        print(f"[-] Fail Formula 42 tidak dijumpai di: {file_42_target}")

    # Simpan laporan semakan ke JSON untuk fail artifact
    with open(REPORT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_reports, f, indent=4, ensure_ascii=False)

    print(f"[+] Laporan semakan disimpan ke: {REPORT_OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
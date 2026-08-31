#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & DRAW VERIFICATION
MODULE       : 00_draw_checker.py
DESCRIPTION  : Mengutip data cabutan terkini (1 minggu), membandingkan dengan 
               cadangan Formula 18, 20 & 36 di live_engine/temp/, mengira kemenangan
               (Direct Big & iBox Big), dan menghantar laporan ke Telegram.
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
os.makedirs(TEMP_DIR, exist_ok=True)

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
        perms = get_permutation_count(num)
        sorted_num = "".join(sorted(num))

        # 1. Semakan Direct Big
        if bet_direct > 0:
            if num == p1:
                win = PAYOUT_DIRECT_BIG['1st'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 1st Prize", "rank": rank, "number": num, "win_rm": win})
            elif num == p2:
                win = PAYOUT_DIRECT_BIG['2nd'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 2nd Prize", "rank": rank, "number": num, "win_rm": win})
            elif num == p3:
                win = PAYOUT_DIRECT_BIG['3rd'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct 3rd Prize", "rank": rank, "number": num, "win_rm": win})
            elif num in specials:
                win = PAYOUT_DIRECT_BIG['special'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct Special", "rank": rank, "number": num, "win_rm": win})
            elif num in consolations:
                win = PAYOUT_DIRECT_BIG['consolation'] * bet_direct
                total_winnings += win
                hit_logs.append({"type": "Direct Consolation", "rank": rank, "number": num, "win_rm": win})

        # 2. Semakan iBox Big (Gunakan jadual tepat mengikut permutasi)
        if bet_ibox > 0 and perms in PAYOUT_IBOX_BIG:
            rates = PAYOUT_IBOX_BIG[perms]
            if "".join(sorted(p1)) == sorted_num:
                win = rates['1st'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 1st Prize ({p1})", "rank": rank, "number": num, "win_rm": win})
            if "".join(sorted(p2)) == sorted_num:
                win = rates['2nd'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 2nd Prize ({p2})", "rank": rank, "number": num, "win_rm": win})
            if "".join(sorted(p3)) == sorted_num:
                win = rates['3rd'] * bet_ibox
                total_winnings += win
                hit_logs.append({"type": f"iBox 3rd Prize ({p3})", "rank": rank, "number": num, "win_rm": win})
            for sp in specials:
                if "".join(sorted(sp)) == sorted_num:
                    win = rates['special'] * bet_ibox
                    total_winnings += win
                    hit_logs.append({"type": f"iBox Special ({sp})", "rank": rank, "number": num, "win_rm": win})
            for cs in consolations:
                if "".join(sorted(cs)) == sorted_num:
                    win = rates['consolation'] * bet_ibox
                    total_winnings += win
                    hit_logs.append({"type": f"iBox Consolation ({cs})", "rank": rank, "number": num, "win_rm": win})

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


def main():
    print("=" * 80)
    print(" 🚀 MEMULAKAN SEMAKAN KEPUTUSAN CABUTAN TOTO 4D (3 FORMULA)")
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

    # Simpan laporan semakan ke folder temp untuk kegunaan artifact
    with open(REPORT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_reports, f, indent=4, ensure_ascii=False)

    print(f"[+] Laporan semakan disimpan ke: {REPORT_OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
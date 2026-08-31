#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & NOTIFICATION PIPELINE
MODULE       : 00_telegram.py
DESCRIPTION  : Membaca fail JSON cadangan formula (18, 20 & 36) di live_engine/temp/
               dan menghantar 3 notifikasi berasingan berformat kemas ke Telegram.
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# KONFIGURASI DIREKTORI & PERSEKITARAN (.ENV)
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMP_DIR = os.path.join(BASE_DIR, "live_engine", "temp")

ENV_LOCAL = os.path.join(BASE_DIR, ".env.local")
ENV_DEFAULT = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_LOCAL):
    load_dotenv(ENV_LOCAL)
elif os.path.exists(ENV_DEFAULT):
    load_dotenv(ENV_DEFAULT)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Laluan fail input JSON bagi ketiga-tiga formula
FILE_FORMULA_18 = os.path.join(TEMP_DIR, "18_dual_window_bayesian_momentum.json")
FILE_FORMULA_20 = os.path.join(TEMP_DIR, "20_dynamic_regime_switching.json")
FILE_FORMULA_36 = os.path.join(TEMP_DIR, "36_tuned_dynamic_ema_gate.json")


def send_telegram_message(text_message):
    """Fungsi pembantu untuk menghantar mesej ke Telegram API menggunakan format HTML."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[-] Ralat: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak dijumpai dalam persekitaran.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        res_data = response.json()
        if res_data.get("ok"):
            print("[+] Mesej berjaya dihantar ke Telegram!")
            return True
        else:
            print(f"[-] Ralat Telegram API: {res_data}")
    except Exception as e:
        print(f"[-] Ralat sambungan semasa menghantar ke Telegram: {e}")

    return False


def build_message_formula_18(data):
    """Menjana format mesej untuk Formula 18 (Dual-Window Bayesian Momentum)."""
    formula_name = data.get("formula_name", "Dual-Window Bayesian Momentum")
    conf_tier = data.get("confidence_tier", "N/A")
    entropy = data.get("entropy", 0.0)
    budget = data.get("budget_total_rm", 0.0)
    last_date = data.get("last_draw_date", "N/A")
    last_draw_no = data.get("last_draw_no", "N/A")
    gen_time = data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recs = data.get("recommendations", [])

    conf_icon = "🔥" if "HIGH" in conf_tier else "🛡️"

    lines = [
        "🎰 <b>SPORTS TOTO 4D — ENGINE PREDICTION</b> 🎰",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>Formula 18: {formula_name}</b>",
        f"📅 <b>Rujukan Sesi:</b> <code>Draw #{last_draw_no} ({last_date})</code>",
        f"{conf_icon} <b>Keyakinan:</b> <code>{conf_tier}</code> | Entropi: <code>{entropy:.4f}</code>",
        f"💰 <b>Cadangan Modal:</b> <b>RM {budget:.2f}</b> ({len(recs)} Nombor)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>CADANGAN NOMBOR & PERUNTUKAN TARUHAN:</b>",
    ]

    for item in recs:
        rank = item.get("rank", 0)
        num = item.get("number", "----")
        direct = item.get("bet_direct_rm", 0)
        ibox = item.get("bet_ibox_rm", 0)

        if direct > 0 and ibox > 0:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  Direct: <b>RM{direct}</b> + iBox: <b>RM{ibox}</b>")
        else:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  iBox Sahaja: <b>RM{ibox}</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Sila kawal risiko & bertaruh secara berhemah.</i>")

    return "\n".join(lines)


def build_message_formula_20(data):
    """Menjana format mesej untuk Formula 20 (Dynamic Regime-Switching Gate)."""
    formula_name = data.get("formula_name", "Dynamic Regime-Switching Gate")
    regime_mode = data.get("regime_mode", "N/A")
    entropy = data.get("entropy", 0.0)
    budget = data.get("budget_total_rm", 0.0)
    last_date = data.get("last_draw_date", "N/A")
    last_draw_no = data.get("last_draw_no", "N/A")
    gen_time = data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recs = data.get("recommendations", [])

    regime_icon = "♊" if "TWIN" in regime_mode else "🎲"

    lines = [
        "🎰 <b>SPORTS TOTO 4D — ENGINE PREDICTION</b> 🎰",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>Formula 20: {formula_name}</b>",
        f"📅 <b>Rujukan Sesi:</b> <code>Draw #{last_draw_no} ({last_date})</code>",
        f"{regime_icon} <b>Rejim Pasaran:</b> <code>{regime_mode}</code> | Entropi: <code>{entropy:.4f}</code>",
        f"💰 <b>Cadangan Modal:</b> <b>RM {budget:.2f}</b> ({len(recs)} Nombor)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>CADANGAN NOMBOR & PERUNTUKAN TARUHAN:</b>",
    ]

    for item in recs:
        rank = item.get("rank", 0)
        num = item.get("number", "----")
        direct = item.get("bet_direct_rm", 0)
        ibox = item.get("bet_ibox_rm", 0)

        if direct > 0 and ibox > 0:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  Direct: <b>RM{direct}</b> + iBox: <b>RM{ibox}</b>")
        else:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  iBox Sahaja: <b>RM{ibox}</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Sila kawal risiko & bertaruh secara berhemah.</i>")

    return "\n".join(lines)


def build_message_formula_36(data):
    """Menjana format mesej untuk Formula 36 (Tuned Dynamic Exponential Decay Gate)."""
    formula_name = data.get("formula_name", "Tuned Dynamic Exponential Decay Gate")
    mode_name = data.get("mode", "N/A")
    entropy = data.get("entropy", 0.0)
    budget = data.get("budget_total_rm", 0.0)
    last_date = data.get("last_draw_date", "N/A")
    last_draw_no = data.get("last_draw_no", "N/A")
    gen_time = data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    recs = data.get("recommendations", [])

    mode_icon = "⚡" if "HIGH" in mode_name else "🛡️"

    lines = [
        "🎰 <b>SPORTS TOTO 4D — ENGINE PREDICTION</b> 🎰",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>Formula 36: {formula_name}</b>",
        f"📅 <b>Rujukan Sesi:</b> <code>Draw #{last_draw_no} ({last_date})</code>",
        f"{mode_icon} <b>Status Mod:</b> <code>{mode_name}</code> | Entropi: <code>{entropy:.4f}</code>",
        f"💰 <b>Cadangan Modal:</b> <b>RM {budget:.2f}</b> ({len(recs)} Nombor)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>CADANGAN NOMBOR & PERUNTUKAN TARUHAN:</b>",
    ]

    for item in recs:
        rank = item.get("rank", 0)
        num = item.get("number", "----")
        direct = item.get("bet_direct_rm", 0)
        ibox = item.get("bet_ibox_rm", 0)

        if direct > 0 and ibox > 0:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  Direct: <b>RM{direct}</b> + iBox: <b>RM{ibox}</b>")
        else:
            lines.append(f"  <b>#{rank:02d}</b>  👉  <code><b>{num}</b></code>  │  iBox Sahaja: <b>RM{ibox}</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Sila kawal risiko & bertaruh secara berhemah.</i>")

    return "\n".join(lines)


def process_and_send():
    print("=" * 80)
    print(" 🚀 MEMULAKAN PENGHANTARAN NOTIFIKASI TELEGRAM (LIVE ENGINE - 3 FORMULA)")
    print("=" * 80)

    # 1. Proses Formula 18
    if os.path.exists(FILE_FORMULA_18):
        try:
            with open(FILE_FORMULA_18, "r", encoding="utf-8") as f:
                data_18 = json.load(f)
            msg_18 = build_message_formula_18(data_18)
            print("[+] Menghantar Mesej 1 (Formula 18: Dual-Window Bayesian Momentum)...")
            send_telegram_message(msg_18)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 18: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_18}")

    time.sleep(1.5)

    # 2. Proses Formula 20
    if os.path.exists(FILE_FORMULA_20):
        try:
            with open(FILE_FORMULA_20, "r", encoding="utf-8") as f:
                data_20 = json.load(f)
            msg_20 = build_message_formula_20(data_20)
            print("[+] Menghantar Mesej 2 (Formula 20: Dynamic Regime-Switching Gate)...")
            send_telegram_message(msg_20)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 20: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_20}")

    time.sleep(1.5)

    # 3. Proses Formula 36
    if os.path.exists(FILE_FORMULA_36):
        try:
            with open(FILE_FORMULA_36, "r", encoding="utf-8") as f:
                data_36 = json.load(f)
            msg_36 = build_message_formula_36(data_36)
            print("[+] Menghantar Mesej 3 (Formula 36: Tuned Dynamic Exponential Decay Gate)...")
            send_telegram_message(msg_36)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 36: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_36}")

    print("=" * 80)
    print(" ✨ Selesai penghantaran notifikasi 3 formula!")
    print("=" * 80)


if __name__ == "__main__":
    process_and_send()
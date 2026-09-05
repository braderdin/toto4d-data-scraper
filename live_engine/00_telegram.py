#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 4D LIVE ENGINE & NOTIFICATION PIPELINE
MODULE       : 00_telegram.py
DESCRIPTION  : Membaca fail JSON cadangan formula (18, 20, 36, 37, 39 & 42) dan
               menghantar 6 notifikasi berasingan berformat kemas dan berstruktur
               ke Telegram menggunakan reka bentuk visual tersuai.
               Khusus Formula 42: Dilengkapi penunjuk prestasi 3 bulan bagi
               setiap nombor serta seleksi pilihan bajet pantas RM10 & RM15.
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
TEMP_FORMULA_DIR = os.path.join(BASE_DIR, "temp")

ENV_LOCAL = os.path.join(BASE_DIR, ".env.local")
ENV_DEFAULT = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_LOCAL):
    load_dotenv(ENV_LOCAL)
elif os.path.exists(ENV_DEFAULT):
    load_dotenv(ENV_DEFAULT)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Laluan fail input JSON bagi keenam-enam formula
FILE_FORMULA_18 = os.path.join(TEMP_DIR, "18_dual_window_bayesian_momentum.json")
FILE_FORMULA_20 = os.path.join(TEMP_DIR, "20_dynamic_regime_switching.json")
FILE_FORMULA_36 = os.path.join(TEMP_DIR, "36_tuned_dynamic_ema_gate.json")
FILE_FORMULA_37 = os.path.join(TEMP_FORMULA_DIR, "recommendations_37_ensemble_multi_regime_ibox.json")
FILE_FORMULA_39 = os.path.join(TEMP_FORMULA_DIR, "recommendations_39_ensemble_hybrid_direct_ibox.json")
FILE_FORMULA_42 = os.path.join(TEMP_FORMULA_DIR, "recommendations_42_ensemble_hybrid_direct_ibox.json")


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


def build_message_formula_37(data):
    """Menjana format mesej khas untuk Formula 37 (Multi-Regime Ensemble & Asymmetric iBox Master)."""
    formula_name = data.get("formula_name", "Multi-Regime Ensemble & Asymmetric iBox Master")
    target_date = data.get("target_date", "N/A")
    draw_no = data.get("draw_no", "N/A")
    budget = data.get("budget_rm", 20.0)
    meta = data.get("meta_signals", {})
    regime = meta.get("regime_status", "BALANCED")
    twin_ratio = meta.get("twin_ratio", 0.0)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recs = data.get("recommendations", [])

    lines = [
        "🚀 <b>SPORTS TOTO 4D — ENSEMBLE MASTER (F37)</b> 🚀",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>Formula 37: {formula_name}</b>",
        f"📅 <b>Rujukan Sesi:</b> <code>Draw #{draw_no} ({target_date})</code>",
        f"🌐 <b>Rejim Pasaran:</b> <code>{regime}</code> (Twin: <code>{twin_ratio*100:.1f}%</code>)",
        f"💰 <b>Cadangan Modal:</b> <b>RM {budget:.2f}</b> (Tepat 20 Nombor iBox RM1)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>CADANGAN 20 NOMBOR (SEMUA iBOX RM 1.00):</b>",
        "",
        "💎 <b>4-Way Triplet (AAAB) — Potensi RM625:</b>"
    ]

    p4 = [r for r in recs if r.get("permutation") == 4]
    p6 = [r for r in recs if r.get("permutation") == 6]
    p12 = [r for r in recs if r.get("permutation") == 12]
    p24 = [r for r in recs if r.get("permutation") == 24]

    for item in p4:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox: <b>RM 1.00</b>")

    lines.append("")
    lines.append("🔥 <b>6-Way Dwi-Kembar (AABB) — Potensi RM417:</b>")
    for item in p6:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox: <b>RM 1.00</b>")

    lines.append("")
    lines.append("⚡ <b>12-Way 1-Pasang (AABC) — Potensi RM209:</b>")
    for item in p12:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox: <b>RM 1.00</b>")

    lines.append("")
    lines.append("🛡️ <b>24-Way Berbeza Penuh (ABCD) — Liputan Varians:</b>")
    for item in p24:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox: <b>RM 1.00</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Sila kawal risiko & bertaruh secara berhemah.</i>")

    return "\n".join(lines)


def build_message_formula_39(data):
    """Menjana format mesej eksklusif untuk Formula 39 (Hybrid Direct & iBox Portfolio RM25)."""
    formula_name = data.get("formula_name", "Formula 39 - Ensemble Hybrid Direct & iBox Master")
    target_date = data.get("target_date", "N/A")
    draw_no = data.get("draw_no", "N/A")
    budget = data.get("budget_rm", 25.0)
    meta = data.get("meta_signals", {})
    regime = meta.get("regime_status", "EXPONENTIAL-BALANCED")
    twin_ratio = meta.get("twin_ratio", 0.0)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recs = data.get("recommendations", [])

    direct_list = [r for r in recs if r.get("bet_type") == "Direct"]
    ibox_list = [r for r in recs if r.get("bet_type") == "iBox"]

    lines = [
        "👑 <b>SPORTS TOTO 4D — HYBRID PORTFOLIO MASTER (F39)</b> 👑",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>Formula 39:</b> <code>{formula_name}</code>",
        f"📅 <b>Rujukan Sesi:</b> <code>Draw #{draw_no} ({target_date})</code>",
        f"🌐 <b>Rejim Pasaran:</b> <code>{regime}</code> (Twin: <code>{twin_ratio*100:.1f}%</code>)",
        f"💰 <b>Cadangan Modal:</b> <b>RM {budget:.2f}</b> (4 Direct + 21 iBox)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💥 <b>4 NOMBOR DIRECT BIG (RM 1.00) — JACKPOT HUNT:</b>",
    ]

    for item in direct_list:
        cat_short = item.get("category", "").split("(")[0].strip()
        lines.append(f"  <b>#{item['rank']:02d}</b>  🎯  <code><b>{item['number']}</b></code>  │  Direct <b>RM 1.00</b> ({cat_short})")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ <b>21 NOMBOR BIG iBOX (RM 1.00) — RISK ABSORBER:</b>")

    ibox_p4 = [r for r in ibox_list if r.get("permutation") == 4]
    ibox_p6 = [r for r in ibox_list if r.get("permutation") == 6]
    ibox_p12 = [r for r in ibox_list if r.get("permutation") == 12]
    ibox_p24 = [r for r in ibox_list if r.get("permutation") == 24]

    lines.append("")
    lines.append("💎 <b>4-Way Triplet (7x iBox RM1 — Potensi RM625):</b>")
    for item in ibox_p4:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox <b>RM 1.00</b>")

    lines.append("")
    lines.append("🔥 <b>6-Way Dwi-Kembar (10x iBox RM1 — Potensi RM417):</b>")
    for item in ibox_p6:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox <b>RM 1.00</b>")

    lines.append("")
    lines.append("⚡ <b>12-Way 1-Pasang (2x iBox RM1 — Potensi RM209):</b>")
    for item in ibox_p12:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox <b>RM 1.00</b>")

    lines.append("")
    lines.append("🎲 <b>24-Way Berbeza (2x iBox RM1 — Spektrum Penuh):</b>")
    for item in ibox_p24:
        lines.append(f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox <b>RM 1.00</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Sila kawal modal & bertaruh secara berhemah.</i>")

    return "\n".join(lines)


def build_message_formula_42(data):
    """Menjana format mesej Formula 42 dengan rekod prestasi 3 bulan bagi setiap rank dan cadangan bajet jimat."""
    formula_name = data.get("formula_name", "Formula 42 - Ensemble Optimized Portfolio (Twin Overweight)")
    target_date = data.get("target_date", "N/A")
    draw_no = data.get("draw_no", "N/A")
    budget = data.get("budget_rm", 25.0)
    meta = data.get("meta_signals", {})
    regime = meta.get("regime_status", "EXPONENTIAL-BALANCED")
    twin_ratio = meta.get("twin_ratio", 0.0)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recs = data.get("recommendations", [])
    budget_picks = data.get("budget_picks", {})

    direct_list = [r for r in recs if r.get("bet_type") == "Direct"]
    ibox_list = [r for r in recs if r.get("bet_type") == "iBox"]

    lines = [
        "🌟 <b>SPORTS TOTO 4D — FLAGSHIP MASTER (F42)</b> 🌟",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>Formula 42:</b> <code>{formula_name}</code>",
        f"📅 <b>Sasaran Cabutan:</b> <code>Draw #{draw_no} ({target_date})</code>",
        f"📊 <b>Rejim Pasaran:</b> <code>{regime}</code> (Kembar: <code>{twin_ratio*100:.1f}%</code>)",
        f"💰 <b>Strategi Penuh:</b> <b>RM {budget:.2f}</b> (4 Direct + 21 iBox)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>4 DIRECT BIG (RM 1.00) — JACKPOT HUNT:</b>",
    ]

    for item in direct_list:
        cat_short = item.get("category", "").split("(")[0].strip()
        perf = item.get("perf_3m", {})
        pnl = perf.get("pnl_rm", 0.0)
        hits = perf.get("hits", 0)

        # Lencana status prestasi 3 bulan bagi Direct
        if pnl > 0:
            badge = f"👑 <b>[+RM{pnl:,.0f} | {hits}x]</b>"
        elif hits > 0:
            badge = f"🎯 <b>[RM{pnl:,.0f} | {hits}x]</b>"
        else:
            badge = "🔻 [0 Hit]"

        lines.append(f"  <b>#{item['rank']:02d}</b>  💥  <code><b>{item['number']}</b></code>  │  Direct <b>RM1</b> ({cat_short}) {badge}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ <b>21 BIG iBOX (RM 1.00) — PRESTASI 3 BULAN:</b>")

    ibox_p4 = [r for r in ibox_list if r.get("permutation") == 4]
    ibox_p6 = [r for r in ibox_list if r.get("permutation") == 6]
    ibox_p12 = [r for r in ibox_list if r.get("permutation") == 12]
    ibox_p24 = [r for r in ibox_list if r.get("permutation") == 24]

    def format_ibox_line(item, label):
        perf = item.get("perf_3m", {})
        pnl = perf.get("pnl_rm", 0.0)
        hits = perf.get("hits", 0)
        if pnl > 0:
            badge = f"🚀 <b>[+RM{pnl:,.0f} | {hits}x]</b>"
        elif hits > 0:
            badge = f"🎯 <b>[RM{pnl:,.0f} | {hits}x]</b>"
        else:
            badge = "🔻 [0x]"
        return f"  <b>#{item['rank']:02d}</b>  👉  <code><b>{item['number']}</b></code>  │  iBox <b>RM1</b> ({label}) {badge}"

    lines.append("")
    lines.append("💎 <b>4-Way Triplet (4x iBox RM1 — Fokus Padat):</b>")
    for item in ibox_p4:
        lines.append(format_ibox_line(item, "AAAB"))

    lines.append("")
    lines.append(f"🔥 <b>6-Way Dwi-Kembar ({len(ibox_p6)}x iBox RM1 — Zon Untung Tertinggi):</b>")
    for item in ibox_p6:
        lines.append(format_ibox_line(item, "AABB"))

    lines.append("")
    lines.append("⚡ <b>12-Way 1-Pasang (2x iBox RM1 — Perisai Modal):</b>")
    for item in ibox_p12:
        lines.append(format_ibox_line(item, "AABC"))

    lines.append("")
    lines.append("🎲 <b>24-Way Berbeza (2x iBox RM1 — Penampung Varians):</b>")
    for item in ibox_p24:
        lines.append(format_ibox_line(item, "ABCD"))

    # ==============================================================================
    # SEKSYEN KHAS: CADANGAN PILIHAN BAJET JIMAT (RM10 & RM15)
    # ==============================================================================
    t10 = budget_picks.get("tier_rm10_ranks", [])
    t15 = budget_picks.get("tier_rm15_ranks", [])

    if t10 and t15:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <b>PILIHAN BAJET JIMAT (BERDASARKAN PRESTASI 3 BULAN):</b>")

        t10_nums = []
        for r_no in t10:
            match = next((x for x in recs if x["rank"] == r_no), None)
            if match:
                t10_nums.append(f"<code>#{r_no:02d}({match['number']})</code>")

        t15_extra = []
        for r_no in t15[10:]:
            match = next((x for x in recs if x["rank"] == r_no), None)
            if match:
                t15_extra.append(f"<code>#{r_no:02d}({match['number']})</code>")

        lines.append(f"💵 <b>Bajet RM 10.00 (Top 10 Nombor Terbaik):</b>\n  👉 {' '.join(t10_nums)}")
        lines.append(f"💵 <b>Bajet RM 15.00 (+5 Nombor Tambahan):</b>\n  👉 {' '.join(t15_extra)}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ <i>Dijana pada: {gen_time}</i>")
    lines.append("⚠️ <i>Gunakan strategi portfolio dengan disiplin modal.</i>")

    return "\n".join(lines)


def process_and_send():
    print("=" * 80)
    print(" 🚀 MEMULAKAN PENGHANTARAN NOTIFIKASI TELEGRAM (LIVE ENGINE - 6 FORMULA)")
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

    time.sleep(1.5)

    # 4. Proses Formula 37 (Ensemble Master)
    if os.path.exists(FILE_FORMULA_37):
        try:
            with open(FILE_FORMULA_37, "r", encoding="utf-8") as f:
                data_37 = json.load(f)
            msg_37 = build_message_formula_37(data_37)
            print("[+] Menghantar Mesej 4 (Formula 37: Multi-Regime Ensemble & Asymmetric iBox Master)...")
            send_telegram_message(msg_37)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 37: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_37}")

    time.sleep(1.5)

    # 5. Proses Formula 39 (Hybrid Direct & iBox Master)
    if os.path.exists(FILE_FORMULA_39):
        try:
            with open(FILE_FORMULA_39, "r", encoding="utf-8") as f:
                data_39 = json.load(f)
            msg_39 = build_message_formula_39(data_39)
            print("[+] Menghantar Mesej 5 (Formula 39: Ensemble Hybrid Direct & iBox Master)...")
            send_telegram_message(msg_39)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 39: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_39}")

    time.sleep(1.5)

    # 6. Proses Formula 42 (Flagship Master - F18 Tuned + Twin Overweight)
    if os.path.exists(FILE_FORMULA_42):
        try:
            with open(FILE_FORMULA_42, "r", encoding="utf-8") as f:
                data_42 = json.load(f)
            msg_42 = build_message_formula_42(data_42)
            print("[+] Menghantar Mesej 6 (Formula 42: Flagship Optimized Portfolio Master)...")
            send_telegram_message(msg_42)
        except Exception as e:
            print(f"[-] Ralat memproses fail Formula 42: {e}")
    else:
        print(f"[-] Fail tidak dijumpai: {FILE_FORMULA_42}")

    print("=" * 80)
    print(" ✨ Selesai penghantaran notifikasi 6 formula!")
    print("=" * 80)


if __name__ == "__main__":
    process_and_send()
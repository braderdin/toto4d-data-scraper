import os
import sys
import json
import re
from collections import Counter

# Tambah laluan direktori induk supaya boleh mengimport toto_01, toto_02, dan toto_03
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from toto_01_scraper import fetch_toto_data
from toto_03_telegram import send_telegram_message

# Import terus toto_02_analyzer untuk mengekstrak Top 10 mutlak
try:
    import toto_02_analyzer
except ImportError:
    toto_02_analyzer = None

DIRECT_PAYOUTS = {"1st": 2500, "2nd": 1000, "3rd": 500, "special": 180, "consolation": 60}
IBOX_PAYOUTS = {
    24: {"1st": 104, "2nd": 42, "3rd": 13, "special": 8, "consolation": 4},
    12: {"1st": 208, "2nd": 84, "3rd": 26, "special": 15, "consolation": 8},
    6:  {"1st": 416, "2nd": 168, "3rd": 52, "special": 30, "consolation": 16},
    4:  {"1st": 625, "2nd": 250, "3rd": 78, "special": 45, "consolation": 24}
}

def get_ibox_perm(num_str):
    u = len(set(num_str))
    if u == 4: return 24
    c = sorted(Counter(num_str).values(), reverse=True)
    if c == [2, 1, 1]: return 12
    if c == [2, 2]: return 6
    if c == [3, 1]: return 4
    return 1

def extract_top10_from_analyzer(data):
    """
    Menjalankan toto_02_analyzer ke atas dataset 'data' yang sama
    dan mengekstrak Top 10 nombor tepat seperti dalam Laporan Telegram.
    """
    top_10 = []
    if toto_02_analyzer and hasattr(toto_02_analyzer, 'analyze_data'):
        try:
            report = toto_02_analyzer.analyze_data(data)
            if isinstance(report, tuple):
                report = report[0]
            if isinstance(report, str):
                # Ekstrak nombor 1. XXXX hingga 10. XXXX terus dari teks laporan
                matches = re.findall(r'(?:10|[1-9])\.\s*(\d{4})', report)
                if len(matches) >= 10:
                    top_10 = matches[:10]
        except Exception as e:
            print(f"[!] Ralat semasa memanggil toto_02_analyzer: {e}")

    # Fallback keselamatan jika toto_02_analyzer tidak dipasang dengan betul
    if not top_10 or len(top_10) < 10:
        pos_ribuan, pos_ratusan, pos_puluhan, pos_sa = Counter(), Counter(), Counter(), Counter()
        for draw in data:
            items = [draw.get("1st_prize"), draw.get("2nd_prize"), draw.get("3rd_prize")]
            for n in draw.get("special_prizes", []): items.append(n)
            for n in draw.get("consolation_prizes", []): items.append(n)
            for num in items:
                if num and len(num) == 4 and num.isdigit():
                    pos_ribuan[num[0]] += 1
                    pos_ratusan[num[1]] += 1
                    pos_puluhan[num[2]] += 1
                    pos_sa[num[3]] += 1
        total = sum(pos_ribuan.values()) or 1
        candidates = {}
        for i in range(10000):
            num = f"{i:04d}"
            score = (pos_ribuan[num[0]] + pos_ratusan[num[1]] + pos_puluhan[num[2]] + pos_sa[num[3]]) / total
            if sum(1 for d in num if int(d) % 2 == 0) == 2:
                score *= 1.15
            candidates[num] = score
        top_10 = [n for n, s in sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]]

    return top_10[:10]

def check_latest_draw():
    json_path = os.path.abspath(os.path.join(parent_dir, "..", "data", "output", "toto_4d_results.json"))
    data = []

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[-] Ralat membaca fail JSON tempatan: {e}")

    if not data:
        print("[!] Fail tempatan tiada. Mengutip data baharu dari web...")
        data = fetch_toto_data(days=365)

    if not data or len(data) < 2:
        print("[-] Data tidak mencukupi untuk semakan.")
        return

    latest_draw = data[0]
    draw_date = latest_draw.get("date") or latest_draw.get("draw_date") or "Terkini"
    draw_no = latest_draw.get("draw_no", "-")

    # Jalankan terus ke atas dataset 'data' penuh supaya 100% IDENTIK dengan toto_02
    top_10 = extract_top10_from_analyzer(data)

    # Petakan Keputusan Rasmi
    winning_map = {}
    if latest_draw.get("1st_prize"): winning_map[latest_draw["1st_prize"]] = "1st"
    if latest_draw.get("2nd_prize"): winning_map[latest_draw["2nd_prize"]] = "2nd"
    if latest_draw.get("3rd_prize"): winning_map[latest_draw["3rd_prize"]] = "3rd"
    for n in latest_draw.get("special_prizes", []): winning_map[n] = "special"
    for n in latest_draw.get("consolation_prizes", []): winning_map[n] = "consolation"

    total_cost = 13
    total_winnings = 0
    winning_tickets = []

    # 1. Semak Top 1..3 (Direct RM1 + iBox RM1)
    for idx, num in enumerate(top_10[:3], 1):
        perm = get_ibox_perm(num)
        for win_num, cat in winning_map.items():
            if win_num == num:
                payout = DIRECT_PAYOUTS[cat]
                total_winnings += payout
                winning_tickets.append(f"🎉 **Top {idx} ({num})** ➔ DIRECT KENA Hadiah {cat.upper()} (RM{payout})")
            if len(win_num) == 4 and sorted(win_num) == sorted(num):
                payout = IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                total_winnings += payout
                winning_tickets.append(f"✨ **Top {idx} ({num})** ➔ iBox KENA Hadiah {cat.upper()} (RM{payout})")

    # 2. Semak Top 4..10 (iBox RM1 Sahaja)
    for idx, num in enumerate(top_10[3:10], 4):
        perm = get_ibox_perm(num)
        for win_num, cat in winning_map.items():
            if len(win_num) == 4 and sorted(win_num) == sorted(num):
                payout = IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                total_winnings += payout
                winning_tickets.append(f"✨ **Top {idx} ({num})** ➔ iBox KENA Hadiah {cat.upper()} (RM{payout})")

    net_profit = total_winnings - total_cost

    msg = []
    msg.append("🎟️ **SEMAKAN KEPUTUSAN TIKET TOTO 4D**")
    msg.append(f"📅 Cabutan: **{draw_date}** (Draw No: **{draw_no}**)")
    msg.append("==========================================")
    msg.append("📋 **SENARAI 10 NOMBOR TARUHAN:**")
    msg.append(f"• **Top 1-3 (Direct+iBox):** {', '.join(top_10[:3])}")
    msg.append(f"• **Top 4-10 (iBox):** {', '.join(top_10[3:10])}")
    msg.append("------------------------------------------")
    msg.append(f"💵 Modal Taruhan Dilabur: **RM{total_cost}** (Pakej 10 Nombor)")
    msg.append("")

    if winning_tickets:
        msg.append("🏆 **SENARAI NOMBOR YANG KENA/MENANG:**")
        for win_item in winning_tickets:
            msg.append(f"   {win_item}")
        msg.append("")
        msg.append("------------------------------------------")
        msg.append(f"💰 **TOTAL HADIAH BOLEH TEBUS DI KEDAI:** **RM{total_winnings}**")
        if net_profit > 0:
            msg.append(f"🟢 **UNTUNG BERSIH:** **+RM{net_profit}** 🎉")
        else:
            msg.append(f"🔴 **RUGI BERSIH:** **RM{net_profit}**")
    else:
        msg.append("❌ **TIADA NOMBOR KENA PADA CABUTAN INI.**")
        msg.append("------------------------------------------")
        msg.append(f"🔴 **KEDUDUKAN NET:** **-RM{total_cost}**")

    msg.append("")
    msg.append("📌 *Bawa resit asal ke kaunter Sports Toto untuk tebus hadiah jika ada.*")

    report_text = "\n".join(msg)
    print(report_text)
    send_telegram_message(report_text)

if __name__ == "__main__":
    check_latest_draw()
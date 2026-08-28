import os
import json
from collections import Counter
from toto_01_scraper import fetch_toto_data
from toto_03_telegram import send_telegram_message

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

def generate_top10_diverse(slice_data):
    pos_ribuan, pos_ratusan, pos_puluhan, pos_sa = Counter(), Counter(), Counter(), Counter()
    for draw in slice_data:
        items = [(draw.get("1st_prize"), 5), (draw.get("2nd_prize"), 4), (draw.get("3rd_prize"), 3)]
        for n in draw.get("special_prizes", []): items.append((n, 2))
        for n in draw.get("consolation_prizes", []): items.append((n, 1))
        for num, w in items:
            if num and len(num) == 4 and num.isdigit():
                pos_ribuan[num[0]] += w; pos_ratusan[num[1]] += w
                pos_puluhan[num[2]] += w; pos_sa[num[3]] += w

    total_samples = sum(pos_ribuan.values()) or 1
    candidates = {}
    for i in range(10000):
        num = f"{i:04d}"
        score = (pos_ribuan[num[0]] + pos_ratusan[num[1]] + pos_puluhan[num[2]] + pos_sa[num[3]]) / total_samples
        if sum(1 for d in num if int(d) % 2 == 0) == 2: score *= 1.15
        candidates[num] = score

    sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    unique_ibox_sets = set()
    final_picks = []

    for num, _ in sorted_candidates:
        sorted_sig = "".join(sorted(num))
        if sorted_sig in unique_ibox_sets: continue
        
        too_similar = False
        for existing in final_picks:
            if len(list((Counter(num) & Counter(existing)).elements())) >= 3:
                too_similar = True; break
                
        if not too_similar:
            unique_ibox_sets.add(sorted_sig)
            final_picks.append(num)
            if len(final_picks) == 10: break

    return final_picks

def check_latest_draw():
    # 1. Buka fail JSON tempatan untuk kelajuan optimum
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "output", "toto_4d_results.json")
    data = []

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[-] Ralat membaca fail JSON tempatan: {e}")

    # Fallback: Jika fail tempatan tiada/kosong, lakukan scraping semula
    if not data:
        print("[!] Fail tempatan tiada. Mengutip data baharu dari web...")
        data = fetch_toto_data(days=365)

    if not data or len(data) < 2:
        print("[-] Data tidak mencukupi untuk semakan.")
        return

    # Cabutan RASMI TERKINI (data[0]) & Sejarah analisis (data[1:])
    latest_draw = data[0]
    history_slice = data[1:]

    # KEMASKINI 1: Menyokong key 'date' atau 'draw_date'
    draw_date = latest_draw.get("date") or latest_draw.get("draw_date") or "Terkini"
    draw_no = latest_draw.get("draw_no", "-")

    # Jana 10 cadangan nombor berdasarkan sejarah lalu
    top_10 = generate_top10_diverse(history_slice)

    # Petakan Keputusan Rasmi Terkini
    winning_map = {}
    if latest_draw.get("1st_prize"): winning_map[latest_draw["1st_prize"]] = "1st"
    if latest_draw.get("2nd_prize"): winning_map[latest_draw["2nd_prize"]] = "2nd"
    if latest_draw.get("3rd_prize"): winning_map[latest_draw["3rd_prize"]] = "3rd"
    for n in latest_draw.get("special_prizes", []): winning_map[n] = "special"
    for n in latest_draw.get("consolation_prizes", []): winning_map[n] = "consolation"

    total_cost = 13  # Top 3 (RM6) + Top 4-10 (RM7)
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

    # KEMASKINI 2: Format Mesej Telegram dengan Senarai 10 Nombor Taruhan
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
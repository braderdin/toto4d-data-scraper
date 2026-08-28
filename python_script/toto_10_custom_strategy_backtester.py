import os
import json
from collections import Counter
from rich.console import Console
from rich.table import Table

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

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

def run_custom_backtest():
    if not os.path.exists(INPUT_FILE): return
    with open(INPUT_FILE, "r", encoding="utf-8") as f: data = json.load(f)

    total_draws, total_spent, total_won, hits = 0, 0, 0, 0
    direct_hits, ibox_hits = 0, 0

    for i in range(20, len(data)):
        history, target = data[:i], data[i]
        top_10 = generate_top10_diverse(history)
        if len(top_10) < 10: continue

        total_draws += 1
        total_spent += 13  # Top 3 (RM2x3=6) + Top 4-10 (RM1x7=7)

        winning_map = {}
        if target.get("1st_prize"): winning_map[target["1st_prize"]] = "1st"
        if target.get("2nd_prize"): winning_map[target["2nd_prize"]] = "2nd"
        if target.get("3rd_prize"): winning_map[target["3rd_prize"]] = "3rd"
        for n in target.get("special_prizes", []): winning_map[n] = "special"
        for n in target.get("consolation_prizes", []): winning_map[n] = "consolation"

        draw_hit = False
        # Top 1..3: Direct RM1 + iBox RM1
        for num in top_10[:3]:
            perm = get_ibox_perm(num)
            for win_num, cat in winning_map.items():
                if win_num == num:
                    total_won += DIRECT_PAYOUTS[cat]
                    direct_hits += 1
                    draw_hit = True
                if len(win_num) == 4 and sorted(win_num) == sorted(num):
                    total_won += IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                    ibox_hits += 1
                    draw_hit = True

        # Top 4..10: iBox RM1 Sahaja
        for num in top_10[3:10]:
            perm = get_ibox_perm(num)
            for win_num, cat in winning_map.items():
                if len(win_num) == 4 and sorted(win_num) == sorted(num):
                    total_won += IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                    ibox_hits += 1
                    draw_hit = True

        if draw_hit: hits += 1

    table = Table(title="🎯 UJIAN STRATEGI PROPER (TOP 10 DIVERSE: RM13/CABUTAN)")
    table.add_column("Metrik Prestasi", style="bold cyan")
    table.add_column("Hasil Strategi Anda", style="bold yellow")

    table.add_row("Jumlah Cabutan Diuji", f"{total_draws} cabutan")
    table.add_row("Nisbah Cabutan Kena", f"{(hits/total_draws*100):.1f}% ({hits} cabutan)")
    table.add_row("Direct Hits / iBox Hits", f"{direct_hits} Direct / {ibox_hits} iBox")
    table.add_row("Jumlah Modal Dilabur", f"RM{total_spent}")
    table.add_row("Jumlah Hadiah Dimena", f"RM{total_won}")
    
    net = total_won - total_spent
    color = "bold green" if net >= 0 else "bold red"
    table.add_row("Kedudukan Net (Untung/Rugi)", f"[{color}]RM{net}[/{color}]")

    console.print(table)

if __name__ == "__main__":
    run_custom_backtest()
import os
import json
from collections import Counter
from rich.console import Console
from rich.table import Table

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

# Jadual Hadiah Direct RM1 (SportsToto 4D Big)
DIRECT_PAYOUTS = {
    "1st": 2500,
    "2nd": 1000,
    "3rd": 500,
    "special": 180,
    "consolation": 60
}

# Jadual Hadiah iBox RM1 Mengikut Jenis Permutasi
IBOX_PAYOUTS = {
    24: {"1st": 104, "2nd": 42, "3rd": 13, "special": 8, "consolation": 4},
    12: {"1st": 208, "2nd": 84, "3rd": 26, "special": 15, "consolation": 8},
    6:  {"1st": 416, "2nd": 168, "3rd": 52, "special": 30, "consolation": 16},
    4:  {"1st": 625, "2nd": 250, "3rd": 78, "special": 45, "consolation": 24}
}

def get_ibox_permutations(num_str):
    unique_count = len(set(num_str))
    if unique_count == 4:
        return 24
    counts = sorted(Counter(num_str).values(), reverse=True)
    if counts == [2, 1, 1]:
        return 12
    elif counts == [2, 2]:
        return 6
    elif counts == [3, 1]:
        return 4
    return 1

def generate_top10_for_slice(slice_data):
    if len(slice_data) < 10:
        return []

    pos_ribuan, pos_ratusan, pos_puluhan, pos_sa = Counter(), Counter(), Counter(), Counter()
    for draw in slice_data:
        items = [(draw.get("1st_prize"), 5), (draw.get("2nd_prize"), 4), (draw.get("3rd_prize"), 3)]
        for num in draw.get("special_prizes", []): items.append((num, 2))
        for num in draw.get("consolation_prizes", []): items.append((num, 1))
        
        for num, w in items:
            if num and len(num) == 4 and num.isdigit():
                pos_ribuan[num[0]] += w
                pos_ratusan[num[1]] += w
                pos_puluhan[num[2]] += w
                pos_sa[num[3]] += w

    total_samples = sum(pos_ribuan.values()) or 1
    candidates = {}
    
    # Menilai 10,000 kombinasi 4D
    for i in range(10000):
        num = f"{i:04d}"
        score = (pos_ribuan[num[0]] + pos_ratusan[num[1]] + pos_puluhan[num[2]] + pos_sa[num[3]]) / total_samples
        if sum(1 for d in num if int(d) % 2 == 0) == 2:
            score *= 1.15
        candidates[num] = score

    return [n for n, s in sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]]

def run_full_strategy_backtest():
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail JSON tidak dijumpai.[/bold red]")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if len(data) < 30:
        console.print("[bold yellow]⚠️ Sampel data terlalu sedikit (Minimum 30 cabutan).[/bold yellow]")
        return

    console.print(f"\n[bold cyan]🎯 Memulakan Simulasi Pakej RM13/Cabutan ({len(data)} cabutan)...[/bold cyan]\n")

    total_draws = 0
    total_spent = 0
    total_won = 0
    draws_with_hits = 0

    direct_hits_count = 0
    ibox_hits_count = 0

    prize_breakdown = {
        "1st": 0, "2nd": 0, "3rd": 0, "special": 0, "consolation": 0
    }

    hit_gaps = []
    last_hit_index = None

    # Mulakan simulasi rolling dari cabutan ke-20
    for i in range(20, len(data)):
        history = data[:i]
        target = data[i]

        top_10 = generate_top10_for_slice(history)
        if not top_10:
            continue

        total_draws += 1
        draw_cost = 13  # Tier 1 (RM6) + Tier 2 (RM7) = RM13
        total_spent += draw_cost

        # Peta keputusan cabutan rasmi
        winning_map = {}
        if target.get("1st_prize"): winning_map[target["1st_prize"]] = "1st"
        if target.get("2nd_prize"): winning_map[target["2nd_prize"]] = "2nd"
        if target.get("3rd_prize"): winning_map[target["3rd_prize"]] = "3rd"
        for n in target.get("special_prizes", []):
            if n: winning_map[n] = "special"
        for n in target.get("consolation_prizes", []):
            if n: winning_map[n] = "consolation"

        draw_hit_flag = False

        # 1. Uji Tier 1 (Top 1..3) -> Direct RM1 + iBox RM1
        for num in top_10[:3]:
            num_sorted = sorted(num)
            perm = get_ibox_permutations(num)

            for win_num, cat in winning_map.items():
                # Semak Kena Direct (Susunan Tepat)
                if win_num == num:
                    win_amt = DIRECT_PAYOUTS[cat]
                    total_won += win_amt
                    direct_hits_count += 1
                    prize_breakdown[cat] += 1
                    draw_hit_flag = True

                # Semak Kena iBox (Susunan Pusing)
                if len(win_num) == 4 and sorted(win_num) == num_sorted:
                    ibox_amt = IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                    total_won += ibox_amt
                    ibox_hits_count += 1
                    if win_num != num:  # Elak bertindih kiraan kategori jika bukan direct
                        prize_breakdown[cat] += 1
                    draw_hit_flag = True

        # 2. Uji Tier 2 (Top 4..10) -> iBox RM1 Sahaja
        for num in top_10[3:10]:
            num_sorted = sorted(num)
            perm = get_ibox_permutations(num)

            for win_num, cat in winning_map.items():
                if len(win_num) == 4 and sorted(win_num) == num_sorted:
                    ibox_amt = IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
                    total_won += ibox_amt
                    ibox_hits_count += 1
                    prize_breakdown[cat] += 1
                    draw_hit_flag = True

        if draw_hit_flag:
            draws_with_hits += 1
            if last_hit_index is not None:
                hit_gaps.append(i - last_hit_index)
            last_hit_index = i

    avg_gap = (sum(hit_gaps) / len(hit_gaps)) if hit_gaps else 0
    hit_rate = (draws_with_hits / total_draws * 100) if total_draws else 0
    net_result = total_won - total_spent

    # Cetak Jadual Analisis
    table = Table(title="💰 PRESTASI SEJARAH PAKEJ RM13 / CABUTAN (TOP 10 STRATEGY)")
    table.add_column("Metrik Prestasi", style="bold cyan")
    table.add_column("Nilai / Keputusan", style="bold yellow")

    table.add_row("Jumlah Cabutan Diuji", f"{total_draws} cabutan")
    table.add_row("Kerap Kena Cabutan (Draw Hit Rate)", f"{hit_rate:.1f}% ({draws_with_hits} cabutan kena)")
    table.add_row("Purata Kitaran Kena (Average Gap)", f"Setiap {avg_gap:.1f} cabutan sekali")
    table.add_row("Kena Direct (Tepat)", f"{direct_hits_count} kali")
    table.add_row("Kena iBox (Pusing)", f"{ibox_hits_count} kali")
    table.add_row("Jumlah Modal Dilabur (RM13 x N)", f"RM{total_spent}")
    table.add_row("Jumlah Pulangan Hadiah", f"RM{total_won}")

    profit_color = "bold green" if net_result >= 0 else "bold red"
    sign = "+" if net_result >= 0 else ""
    table.add_row("Kedudukan Net (Untung / Rugi)", f"[{profit_color}]{sign}RM{net_result}[/{profit_color}]")

    console.print(table)

    console.print("\n🎯 **Pecahan Tangkapan Kategori Hadiah:**")
    for cat, count in prize_breakdown.items():
        console.print(f"  • Hadiah {cat.capitalize()}: {count} kali")

if __name__ == "__main__":
    run_full_strategy_backtest()
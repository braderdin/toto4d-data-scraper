import os
import json
from collections import Counter
from rich.console import Console
from rich.table import Table

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

# Nilai Anggaran Pulangan iBox RM1
PAYOUTS_IBOX = {
    "1st": 104,
    "2nd": 42,
    "3rd": 13,
    "special": 8,
    "consolation": 4
}

def is_balanced(num_str):
    evens = sum(1 for d in num_str if int(d) % 2 == 0)
    return evens == 2

def generate_hybrid_for_slice(slice_data):
    if len(slice_data) < 10:
        return []
    
    positions = [{"hot": Counter(), "gap": {str(d): None for d in range(10)}} for _ in range(4)]
    for idx, draw in enumerate(slice_data):
        main_prizes = [draw.get("1st_prize"), draw.get("2nd_prize"), draw.get("3rd_prize")]
        for num in main_prizes:
            if num and len(num) == 4 and num.isdigit():
                for pos in range(4):
                    d = num[pos]
                    positions[pos]["hot"][d] += 1
                    if positions[pos]["gap"][d] is None:
                        positions[pos]["gap"][d] = idx

    hot_digits = [p["hot"].most_common(1)[0][0] for p in positions]
    cold_digits = [max(p["gap"].items(), key=lambda x: x[1] if x[1] is not None else 999)[0] for p in positions]

    candidates = set()
    for pos_to_replace in range(4):
        comb = list(hot_digits)
        comb[pos_to_replace] = cold_digits[pos_to_replace]
        candidates.add("".join(comb))

    comb2 = [hot_digits[0], cold_digits[1], cold_digits[2], hot_digits[3]]
    candidates.add("".join(comb2))
    comb3 = [cold_digits[0], hot_digits[1], hot_digits[2], cold_digits[3]]
    candidates.add("".join(comb3))

    return [num for num in candidates if is_balanced(num)][:5]

def run_backtest():
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail JSON tidak dijumpai.[/bold red]")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if len(data) < 30:
        console.print("[bold yellow]⚠️ Sampel data terlalu sedikit untuk backtest (Minimum 30 cabutan).[/bold yellow]")
        return

    console.print(f"\n[bold cyan]🔍 Memulakan Simulasi Sejarah Kitaran Nombor Hybrid ({len(data)} cabutan)...[/bold cyan]\n")

    total_tested_draws = 0
    total_hits = 0
    total_spent = 0
    total_won = 0
    prize_counts = {"1st": 0, "2nd": 0, "3rd": 0, "special": 0, "consolation": 0}
    hit_gaps = []
    last_hit_draw_idx = None

    # Rolling window: Guna data [0..i-1] untuk ramal cabutan ke-i
    for i in range(20, len(data)):
        history_slice = data[:i]
        target_draw = data[i]
        
        hybrid_picks = generate_hybrid_for_slice(history_slice)
        if not hybrid_picks:
            continue

        total_tested_draws += 1
        
        # Himpunkan keputusan rasmi cabutan target
        all_winning = {}
        if target_draw.get("1st_prize"): all_winning[target_draw["1st_prize"]] = "1st"
        if target_draw.get("2nd_prize"): all_winning[target_draw["2nd_prize"]] = "2nd"
        if target_draw.get("3rd_prize"): all_winning[target_draw["3rd_prize"]] = "3rd"
        for n in target_draw.get("special_prizes", []):
            if n: all_winning[n] = "special"
        for n in target_draw.get("consolation_prizes", []):
            if n: all_winning[n] = "consolation"

        # Semak setiap cadangan Hybrid mengikut peraturan iBox (pusingan digit)
        draw_hit = False
        for pick in hybrid_picks:
            total_spent += 1  # Andaikan modal iBox RM1 per cadangan
            pick_sorted = sorted(pick)
            
            for win_num, cat in all_winning.items():
                if len(win_num) == 4 and sorted(win_num) == pick_sorted:
                    total_hits += 1
                    prize_counts[cat] += 1
                    total_won += PAYOUTS_IBOX[cat]
                    draw_hit = True

        if draw_hit:
            if last_hit_draw_idx is not None:
                hit_gaps.append(i - last_hit_draw_idx)
            last_hit_draw_idx = i

    avg_gap = (sum(hit_gaps) / len(hit_gaps)) if hit_gaps else 0

    # Jadual Ringkasan Hasil
    table = Table(title="📊 ANALISIS KITARAN & HISTORIKAL NOMBOR HYBRID")
    table.add_column("Metrik Kitaran", style="bold cyan")
    table.add_column("Keputusan / Data", style="bold yellow")

    table.add_row("Jumlah Cabutan Diuji", f"{total_tested_draws} cabutan")
    table.add_row("Jumlah Kena (iBox Hit)", f"{total_hits} kali")
    table.add_row("Nisbah Cabutan Kena (Draw Hit Rate)", f"{(len(hit_gaps) / total_tested_draws * 100):.1f}%" if total_tested_draws else "0%")
    table.add_row("Kitaran Purata Kena (Average Gap)", f"Setiap {avg_gap:.1f} cabutan sekali")
    table.add_row("Anggaran Modal iBox Dilabur", f"RM{total_spent}")
    table.add_row("Anggaran Hadiah Dimena", f"RM{total_won}")
    
    net_profit = total_won - total_spent
    profit_str = f"[bold green]+RM{net_profit}[/bold green]" if net_profit >= 0 else f"[bold red]-RM{abs(net_profit)}[/bold red]"
    table.add_row("Kedudukan Net (Untung/Rugi)", profit_str)

    console.print(table)

    console.print("\n🎯 **Pecahan Tangkapan Kategori Hadiah:**")
    for cat, count in prize_counts.items():
        console.print(f"  • Hadiah {cat.capitalize()}: {count} kali")

if __name__ == "__main__":
    run_backtest()
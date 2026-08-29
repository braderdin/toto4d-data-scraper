import os
import json
from rich.console import Console

console = Console()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results_new.json")

def analyze_gap():
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail JSON tidak dijumpai.[/bold red]")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return

    total_draws = len(data)

    pos_gap = {
        "ribuan": {str(d): None for d in range(10)},
        "ratusan": {str(d): None for d in range(10)},
        "puluhan": {str(d): None for d in range(10)},
        "sa": {str(d): None for d in range(10)}
    }

    main_prize_gaps = {}

    for draw_idx, draw in enumerate(data):
        main_numbers = [
            draw.get("1st_prize"),
            draw.get("2nd_prize"),
            draw.get("3rd_prize")
        ]

        for num in main_numbers:
            if num and len(num) == 4 and num.isdigit():
                if num not in main_prize_gaps:
                    main_prize_gaps[num] = draw_idx
                # rekod gap digit per posisí kalau belum direkod
                if pos_gap["ribuan"][num[0]] is None: pos_gap["ribuan"][num[0]] = draw_idx
                if pos_gap["ratusan"][num[1]] is None: pos_gap["ratusan"][num[1]] = draw_idx
                if pos_gap["puluhan"][num[2]] is None: pos_gap["puluhan"][num[2]] = draw_idx
                if pos_gap["sa"][num[3]] is None: pos_gap["sa"][num[3]] = draw_idx

    report = []
    report.append("⏳ ANALISIS SELA MASA (GAP ANALYSIS) BARU")
    report.append("---------------------------------------")
    report.append("💤 Digit posisi paling lama 'tidur':")

    for pos_name, digits_dict in pos_gap.items():
        coldest = max(digits_dict.items(), key=lambda x: x[1] if x[1] is not None else total_draws)
        gap_val = coldest[1] if coldest[1] is not None else total_draws
        report.append(f"  • {pos_name.capitalize()}: Digit '{coldest[0]}' (tidak keluar {gap_val} cabutan)")

    report.append("")
    report.append("🔥 Top 3 nombor hadiah utama paling lama:")
    sorted_gaps = sorted(main_prize_gaps.items(), key=lambda x: x[1], reverse=True)[:3]
    for num, gap in sorted_gaps:
        report.append(f"  • {num}: terakhir naik {gap} cabutan lepas")

    report_text = "\n".join(report)
    console.print(report_text)


if __name__ == "__main__":
    analyze_gap()

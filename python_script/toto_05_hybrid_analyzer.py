import os
import json
from collections import Counter
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

def is_balanced(num_str):
    """Menyemak adakah nombor mempunyai nisbah 2 Genap : 2 Ganjil."""
    evens = sum(1 for d in num_str if int(d) % 2 == 0)
    return evens == 2

def generate_hybrid_recommendations():
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail JSON tidak dijumpai.[/bold red]")
        return ""

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return ""

    # 1. Kumpulkan digit kerap (Hot) & digit paling lama tidur (Cold Gap) bagi setiap posisi
    positions = [{"hot": Counter(), "gap": {str(d): None for d in range(10)}} for _ in range(4)]
    
    for idx, draw in enumerate(data):
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

    # 2. Bina kombinasi Hybrid
    candidates = set()
    
    # Gabungan Hot + Cold mengikut posisi berbeza
    for pos_to_replace in range(4):
        comb = list(hot_digits)
        comb[pos_to_replace] = cold_digits[pos_to_replace]
        candidates.add("".join(comb))

    # Gabungan 2 Hot + 2 Cold
    comb2 = [hot_digits[0], cold_digits[1], cold_digits[2], hot_digits[3]]
    candidates.add("".join(comb2))
    
    comb3 = [cold_digits[0], hot_digits[1], hot_digits[2], cold_digits[3]]
    candidates.add("".join(comb3))

    # 3. Tapis mengikut nisbah 2 Genap : 2 Ganjil
    final_picks = [num for num in candidates if is_balanced(num)][:5]

    report = []
    report.append("⚡ **5 CADANGAN NOMBOR HYBRID (HOT + GAP):**")
    report.append("------------------------------------------")
    for idx, num in enumerate(final_picks, 1):
        report.append(f"  {idx}. {num} (Pilihan Keseimbangan Hot/Cold + 2E:2O)")

    report_text = "\n".join(report)
    console.print(report_text)
    return report_text

if __name__ == "__main__":
    generate_hybrid_recommendations()
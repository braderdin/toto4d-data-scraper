import os
import json
from collections import Counter
from rich.console import Console

console = Console()

# --- JALUR DATA ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # naik 2 ke atas
DATA_DIR = os.path.join(BASE_DIR, "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results_new.json")  # fail baru

def load_data():
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail data tiada.[/bold red]")
        return None
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_balanced(num_str):
    """Sama ada 2 Genap + 2 Ganjil."""
    evens = sum(1 for d in num_str if int(d) % 2 == 0)
    return evens == 2


def analyze_data():
    data = load_data()
    if not data:
        return None
    if len(data) == 0:
        console.print("[bold red]❌ Data kosong.[/bold red]")
        return None

    total_draws = len(data)

    # Matriks kejadian digit per posisí
    pos_ribuan = Counter()
    pos_ratusan = Counter()
    pos_puluhan = Counter()
    pos_sa = Counter()

    all_numbers_weighted = Counter()
    category_counts = {"1st": Counter(), "2nd": Counter(), "3rd": Counter(), "special": Counter(), "consolation": Counter()}
    all_drawn_unique_set = set()
    even_odd_patterns = Counter()

    for draw in data:
        items = [
            (draw.get("1st_prize"), 5, "1st"),
            (draw.get("2nd_prize"), 4, "2nd"),
            (draw.get("3rd_prize"), 3, "3rd")
        ]
        for num in draw.get("special_prizes", []):
            items.append((num, 2, "special"))
        for num in draw.get("consolation_prizes", []):
            items.append((num, 1, "consolation"))

        for num, weight, cat in items:
            if num and len(num) == 4 and num.isdigit():
                all_numbers_weighted[num] += weight
                category_counts[cat][num] += 1
                all_drawn_unique_set.add(num)

                pos_ribuan[num[0]] += 1
                pos_ratusan[num[1]] += 1
                pos_puluhan[num[2]] += 1
                pos_sa[num[3]] += 1

                evens = sum(1 for d in num if int(d) % 2 == 0)
                odds = 4 - evens
                even_odd_patterns[f"{evens} Genap + {odds} Ganjil"] += 1

    # Cold numbers (belum pernah keluar)
    all_possible_4d = {f"{i:04d}" for i in range(10000)}
    cold_numbers = list(all_possible_4d - all_drawn_unique_set)

    # --- Formula baru: skor kebarangkalian ---
    candidates = {}
    total_samples = sum(pos_ribuan.values()) or 1

    for num in all_possible_4d:
        d0, d1, d2, d3 = num[0], num[1], num[2], num[3]
        score = (pos_ribuan[d0] / total_samples) + \
                (pos_ratusan[d1] / total_samples) + \
                (pos_puluhan[d2] / total_samples) + \
                (pos_sa[d3] / total_samples)

        # Penalti kalau 2E:2O ->Tambah 15%
        if is_balanced(num):
            score *= 1.15

        # Bonus iBox: digit berulang naik sedikit skor
        unique_digits = len(set(num))
        if unique_digits == 3:  # iBox 12
            score *= 1.02
        elif unique_digits == 2:  # iBox 6
            score *= 1.05

        candidates[num] = score

    top_10 = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- Laporan ---
    report = []
    report.append("📊 LAPORAN ANALISIS MATEMATIK TOTO 4D BARU")
    report.append("=======================================")
    report.append(f"🗓 Jumlah cabutan diuji: {total_draws}")
    report.append(f"❄️ Nombor belum pernah keluar (Cold): {len(cold_numbers)} daripada 10,000")
    report.append("")

    report.append("🏆 Top 10 Nombor Berpotensi (Formula Baru):")
    for idx, (num, sc) in enumerate(top_10, 1):
        bal = "2E:2O ✅" if is_balanced(num) else "Lain ✖"
        ibox = "iBox 12/6" if unique_digits in (2,3) else "Direct"
        report.append(f"  {idx}. {num} | Skor: {sc:.4f} | {bal} | {ibox}")

    report.append("")
    report.append("📐 Kuantiti nisbah 2E:2O:")
    balanced_total = sum(1 for n in candidates if is_balanced(n))
    report.append(f"  • {balanced_total}/{len(candidates)} ({balanced_total/len(candidates)*100:.1f}%)")

    report.append("")
    report.append("🎯 10 CADANGAN NOMINI TERBAEK:")
    for idx, (num, sc) in enumerate(top_10, 1):
        uq = len(set(num))
        ib_type = "iBox 12" if uq == 3 else ("iBox 6" if uq == 2 else "Direct")
        report.append(f"  {idx}. **{num}** [{ib_type}] ➔ Skor {sc:.4f}")

    report_text = "\n".join(report)
    console.print(report_text)
    return report_text


if __name__ == "__main__":
    analyze_data()

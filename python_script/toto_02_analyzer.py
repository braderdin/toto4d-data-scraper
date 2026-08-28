import os
import json
from collections import Counter
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

def load_data():
    if not os.path.exists(INPUT_FILE):
        return None
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_data():
    """Fungsi utama dipanggil oleh toto_main.py"""
    data = load_data()
    if not data:
        console.print("[bold red]❌ Gagal membaca fail data toto_4d_results.json[/bold red]")
        return None

    total_draws = len(data)
    if total_draws == 0:
        console.print("[bold red]❌ Fail data kosong.[/bold red]")
        return None
    
    all_numbers_weighted = Counter()
    category_counts = {"1st": Counter(), "2nd": Counter(), "3rd": Counter(), "special": Counter(), "consolation": Counter()}
    all_drawn_unique_set = set()
    
    pos_ribuan = Counter()
    pos_ratusan = Counter()
    pos_puluhan = Counter()
    pos_sa = Counter()
    
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

    # Cold Numbers
    all_possible_4d = {f"{i:04d}" for i in range(10000)}
    cold_numbers = list(all_possible_4d - all_drawn_unique_set)
    
    # Top 10 Predictions
    candidates = {}
    total_samples = sum(pos_ribuan.values()) or 1
    
    for num in all_possible_4d:
        d0, d1, d2, d3 = num[0], num[1], num[2], num[3]
        score = (pos_ribuan[d0] / total_samples) + \
                (pos_ratusan[d1] / total_samples) + \
                (pos_puluhan[d2] / total_samples) + \
                (pos_sa[d3] / total_samples)
        
        evens = sum(1 for d in num if int(d) % 2 == 0)
        if evens == 2:
            score *= 1.15
            
        candidates[num] = score

    top_10_predictions = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]

    report = []
    report.append("📊 **LAPORAN ANALISIS MATEMATIK TOTO 4D ADVANCED**")
    report.append("=======================================")
    report.append(f"🗓 **Jumlah Cabutan Diuji:** {total_draws} cabutan")
    report.append(f"❄️ **Nombor Belum Pernah Keluar (Cold Numbers):** {len(cold_numbers)} daripada 10,000 set")
    report.append("")
    report.append("🏆 **Top 3 Nombor Kerap Naik Hadiah Utama (1st/2nd/3rd):**")
    main_prizes = category_counts["1st"] + category_counts["2nd"] + category_counts["3rd"]
    for num, count in main_prizes.most_common(3):
        report.append(f"  • {num}: {count} kali")

    report.append("")
    report.append("🎲 **Nisbah Genap / Ganjil Dominan:**")
    for pattern, count in even_odd_patterns.most_common(3):
        report.append(f"  • {pattern}: {count} kali")

    report.append("")
    report.append("📌 **Digit Kebarangkalian Posisi Tertinggi:**")
    if pos_ribuan: report.append(f"  • Ribuan (X___): Digit '{pos_ribuan.most_common(1)[0][0]}' ({pos_ribuan.most_common(1)[0][1]}x)")
    if pos_ratusan: report.append(f"  • Ratusan (_X__): Digit '{pos_ratusan.most_common(1)[0][0]}' ({pos_ratusan.most_common(1)[0][1]}x)")
    if pos_puluhan: report.append(f"  • Puluhan (__X_): Digit '{pos_puluhan.most_common(1)[0][0]}' ({pos_puluhan.most_common(1)[0][1]}x)")
    if pos_sa: report.append(f"  • Sa      (___X): Digit '{pos_sa.most_common(1)[0][0]}' ({pos_sa.most_common(1)[0][1]}x)")

    report.append("")
    report.append("🎯 **10 CADANGAN NOMBOR BERPOTENSI TINGGI (NEXT DRAW):**")
    for idx, (num, score) in enumerate(top_10_predictions, 1):
        report.append(f"  {idx}. {num} (Skor Matematik: {score:.4f})")

    report.append("")
    report.append("📐 **Nota Kebarangkalian:** Skor dihitung berasaskan Matriks Posisi Digit Tertinggi dan penyesuaian taburan 2 Genap : 2 Ganjil.")

    report_text = "\n".join(report)
    console.print(report_text)
    
    return report_text

analyze_toto_data = analyze_data

if __name__ == "__main__":
    analyze_data()
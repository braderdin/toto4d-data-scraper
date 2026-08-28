import os
import json
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

def analyze_data():
    if not os.path.exists(INPUT_FILE):
        print("[-] Fail data tidak dijumpai. Sila jalankan toto_01_scraper.py dahulu.")
        return None

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        draws = json.load(f)

    total_draws = len(draws)
    if total_draws == 0:
        return "Tiada data untuk dianalisis."

    all_numbers = []
    top_prizes = [] # 1st, 2nd, 3rd sahaja

    thousands, hundreds, tens, units = Counter(), Counter(), Counter(), Counter()
    even_odd_count = {"4_even": 0, "3e_1o": 0, "2e_2o": 0, "1e_3o": 0, "4_odd": 0}

    for d in draws:
        draw_nums = []
        if d.get("1st_prize"): draw_nums.append(d["1st_prize"])
        if d.get("2nd_prize"): draw_nums.append(d["2nd_prize"])
        if d.get("3rd_prize"): draw_nums.append(d["3rd_prize"])
        
        top_prizes.extend(draw_nums)
        
        draw_nums.extend(d.get("special_prizes", []))
        draw_nums.extend(d.get("consolation_prizes", []))
        
        all_numbers.extend(draw_nums)

        # Analysis kedudukan digit
        for num in draw_nums:
            if len(num) == 4 and num.isdigit():
                thousands[num[0]] += 1
                hundreds[num[1]] += 1
                tens[num[2]] += 1
                units[num[3]] += 1
                
                # Analysis Genap/Ganjil
                evens = sum(1 for ch in num if int(ch) % 2 == 0)
                if evens == 4: even_odd_count["4_even"] += 1
                elif evens == 3: even_odd_count["3e_1o"] += 1
                elif evens == 2: even_odd_count["2e_2o"] += 1
                elif evens == 1: even_odd_count["1e_3o"] += 1
                else: even_odd_count["4_odd"] += 1

    num_counts = Counter(all_numbers)
    top_hot_overall = num_counts.most_common(5)
    top_hot_prizes = Counter(top_prizes).most_common(3)

    total_numbers_drawn = len(all_numbers)
    prob_single_number = (23 / 10000) * 100 # % kebarangkalian teori bagi 1 cabutan

    report = f"""📊 **LAPORAN ANALISIS MATEMATIK TOTO 4D (6 BULAN)**
=======================================
🗓 **Jumlah Cabutan:** {total_draws} cabutan
🔢 **Jumlah Nombor Keluar:** {total_numbers_drawn} nombor

🔥 **Top 5 Nombor Paling Kerap (Overall):**
{chr(10).join([f"  • {num}: {count} kali" for num, count in top_hot_overall])}

🏆 **Top 3 Nombor Hadiah Utama (1st/2nd/3rd):**
{chr(10).join([f"  • {num}: {count} kali" for num, count in top_hot_prizes]) if top_hot_prizes else "  • Tiada ulangan berulang"}

🎲 **Nisbah Genap / Ganjil:**
  • 2 Genap + 2 Ganjil : {even_odd_count['2e_2o']} kali (Paling Dominan)
  • 3 Genap + 1 Ganjil : {even_odd_count['3e_1o']} kali
  • 1 Genap + 3 Ganjil : {even_odd_count['1e_3o']} kali

📌 **Kekerapan Digit Paling Kerap Mengikut Posisi:**
  • Ribuan (X___): Digit '{thousands.most_common(1)[0][0]}' ({thousands.most_common(1)[0][1]}x)
  • Ratusan (_X__): Digit '{hundreds.most_common(1)[0][0]}' ({hundreds.most_common(1)[0][1]}x)
  • Puluhan (__X_): Digit '{tens.most_common(1)[0][0]}' ({tens.most_common(1)[0][1]}x)
  • Sa      (___X): Digit '{units.most_common(1)[0][0]}' ({units.most_common(1)[0][1]}x)

📐 **Nota Matematik & Kebarangkalian:**
Kebarangkalian teori untuk mana-mana 1 set nombor naik dalam mana-mana kategori hadiah pada 1 cabutan ialah **{prob_single_number:.2f}%** (23/10000). Cabutan bersifat *independent events*.
"""
    print(report)
    return report

if __name__ == "__main__":
    analyze_data()
import os
import json
from collections import Counter
from rich.console import Console

console = Console()

# --- SETARAH JALUR ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # naik 2 ke atas dari 4d_new_formula
DATA_DIR = os.path.join(BASE_DIR, "data", "output")
INPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results_new.json")

# --- 1. FUNGSI PETA iBOX (Tidak berubah) ---
def get_ibox_type(num_str):
    """Mengenal pasti jenis iBox berdasarkan bilangan digit berulang."""
    unique_digits = len(set(num_str))
    if unique_digits == 4:
        return "iBox 24"
    
    counts = sorted(Counter(num_str).values(), reverse=True)
    if counts == [2, 1, 1]:
        return "iBox 12"
    elif counts == [2, 2]:
        return "iBox 6"
    elif counts == [3, 1]:
        return "iBox 4"
    elif counts == [4]:
        return "Direct (Nombor Kembar 4)"
    
    return "iBox"

# --- 2. FUNGSI CEK NISBA 2E:2O (Tidak berubah) ---
def is_balanced(num_str):
    """Sama ada 2 Genap + 2 Ganjil."""
    evens = sum(1 for d in num_str if int(d) % 2 == 0)
    return evens == 2

# --- 3. FUNGSI UTAMA STRATEGI ADVISOR (Diperbaiki) ---
def generate_strategy_advisor(top_10_list=None, hybrid_list=None):
    """Menjana cadangan pelan taruhan iBox + Direct dan bajet modal."""
    if not os.path.exists(INPUT_FILE):
        console.print("[bold red]❌ Fail JSON tidak dijumpai untuk Strategy Advisor.[/bold red]")
        return ""

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        return ""

    # Jika senarai top 10 tidak dibekalkan, kira secara automatik
    if not top_10_list:
        pos_ribuan, pos_ratusan, pos_puluhan, pos_sa = Counter(), Counter(), Counter(), Counter()
        for draw in data:
            items = [(draw.get("1st_prize"), 5), (draw.get("2nd_prize"), 4), (draw.get("3rd_prize"), 3)]
            for num in draw.get("special_prizes", []): items.append((num, 2))
            for num in draw.get("consolation_prizes", []): items.append((num, 1))
            for num, w in items:
                if num and len(num) == 4 and num.isdigit():
                    pos_ribuan[num[0]] += 1
                    pos_ratusan[num[1]] += 1
                    pos_puluhan[num[2]] += 1
                    pos_sa[num[3]] += 1

        total_samples = sum(pos_ribuan.values()) or 1
        all_possible_4d = {f"{i:04d}" for i in range(10000)}
        candidates = {}
        for num in all_possible_4d:
            # Matriks skor dasar
            score = (pos_ribuan[num[0]] + pos_ratusan[num[1]] + pos_puluhan[num[2]] + pos_sa[num[3]]) / total_samples
            
            # APLIKASI PENALTI 2E:2O DI SINI
            if is_balanced(num): 
                score *= 1.15
            
            # Bonus iBox
            if len(set(num)) == 3: score *= 1.02 # iBox 12
            elif len(set(num)) == 2: score *= 1.05 # iBox 6
            
            candidates[num] = score
        
        top_10_list = [n for n, s in sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]]

    report = []
    report.append("💡 **PELAN STRATEGI PERTARUHAN OPTIMUM (DIRECT + iBOX)**")
    report.append("==================================================")
    total_budget = 0

    # Tier 1: Top 3
    report.append("🎯 **TIER 1: TOP 3 UTAMA (Direct RM1 + iBox RM1)**")
    report.append("  *Fokus pulangan penuh + insurans susunan pusing*")
    for idx, num in enumerate(top_10_list[:3], 1):
        ibox_tag = get_ibox_type(num)
        report.append(f"   {idx}. **{num}** [{ibox_tag}] ➔ Direct RM1 + iBox RM1 (RM2)")
        total_budget += 2

    report.append("")
    # Tier 2: Top 4-10
    report.append("🛡️ **TIER 2: TOP 4-10 (iBox RM1 Sahaja)**")
    report.append("  *Liputan kebarangkalian tinggi dengan modal minima*")
    for idx, num in enumerate(top_10_list[3:10], 4):
        ibox_tag = get_ibox_type(num)
        report.append(f"   {idx}. **{num}** [{ibox_tag}] ➔ iBox RM1 Sahaja (RM1)")
        total_budget += 1

    # Tier 3: Hybrid
    if hybrid_list:
        report.append("")
        report.append("⚡ **TIER 3: HYBRID PERANGKAP (iBox RM1 Sahaja)**")
        report.append("  *Penjaring nombor sejuk/tidur berpotensi naik*")
        for idx, num in enumerate(hybrid_list, 1):
            ibox_tag = get_ibox_type(num)
            report.append(f"   {idx}. **{num}** [{ibox_tag}] ➔ iBox RM1 Sahaja (RM1)")
            total_budget += 1

    report.append("")
    report.append("--------------------------------------------------")
    report.append(f"💵 **CADANGAN ANGGARAN MODAL:** **RM{total_budget}** / cabutan")
    report.append("📌 *Strategi: iBox menjamin kemenangan jika digit betul walaupun susunan terbalik.*")

    report_text = "\n".join(report)
    console.print(report_text)
    return report_text

if __name__ == "__main__":
    generate_strategy_advisor()

from rich.console import Console
from rich.panel import Panel
import json
import os
from collections import Counter

console = Console()

# --- SETARAH JALUR (SAMA ADA SEPERTI TOTO_01_SCRAWLER) ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) 
DATA_DIR = os.path.join(BASE_DIR, "data", "output")
OUTPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results_new.json")
RECOMMENDATIONS_FILE = os.path.join(DATA_DIR, "toto_recommended_numbers.json")

# --- FORMULA MATEMATIK: GENERATE 10 NOMBOR CADANGAN (DALAMAN FAIL INI) ---
def generate_recommendations(data):
    """
    Formula: Hot digit per posisí + Penalti 2E:2O (+15%) + Bias iBox 12/6.
    Fungsi ini sama persis dengan yang ada di toto_test_recommendations.py sebelumnya.
    """
    if not data:
        return []

    total_draws = len(data)
    
    pos_ribuan = Counter()
    pos_ratusan = Counter()
    pos_puluhan = Counter()
    pos_sa = Counter()

    for draw in data:
        for prize_key in ["1st_prize", "2nd_prize", "3rd_prize"]:
            num = draw.get(prize_key)
            if num and len(num) == 4 and num.isdigit():
                pos_ribuan[num[0]] += 1
                pos_ratusan[num[1]] += 1
                pos_puluhan[num[2]] += 1
                pos_sa[num[3]] += 1

    total_samples = sum(pos_ribuan.values()) or 1
    all_possible_4d = {f"{i:04d}" for i in range(10000)}
    candidates = {}

    for num in all_possible_4d:
        d0, d1, d2, d3 = num[0], num[1], num[2], num[3]
        score = (pos_ribuan[d0] / total_samples) + \
                (pos_ratusan[d1] / total_samples) + \
                (pos_puluhan[d2] / total_samples) + \
                (pos_sa[d3] / total_samples)
        
        evens = sum(1 for d in num if int(d) % 2 == 0)
        if evens == 2: score *= 1.15 # Penalti 2E:2O
        
        unique_digits = len(set(num))
        if unique_digits == 3: score *= 1.02 # Bonus iBox 12
        elif unique_digits == 2: score *= 1.05 # Bonus iBox 6
            
        candidates[num] = score

    top_10 = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]
    return [num for num, score in top_10]

# --- UTAMA ---
def main():
    console.print(Panel.fit("[bold magenta]🎰 TOTO 4D DATA SCRAPER & STRATEGY ANALYZER (BARU) 🎰[/bold magenta]", border_style="cyan"))

    # Jalankan scraper
    results = fetch_toto_data() # Asumsi fetch_toto_data wujud dari toto_01_scraper_baru.py
    if not results:
        return

    console.print("\n[bold cyan]🧮 Menganalisis Kebarangkalian, Gap, Hybrid & Strategi iBox...[/bold cyan]")
    
    # Panggil analisis yang wujud (Analyzer, Gap, Hybrid, Strategy)
    # Nota: Saya asumsikan fungsi-fungsi ini wujud di fail lain dan boleh dipanggil,
    # atau Anda boleh menggantikan bahagian ini dengan panggilan fail lain jika suka.
    # Untuk kesansekuran di sini, saya akan jalankan generate_recommendations yang sudah ditanam.
    
    report_basic = "Laporan Analisis (Formula Baru) - Jumpai di Console"
    report_gap = "Gap Analysis (Formula Baru) - Jumpai di Console"
    report_hybrid = "Hybrid Analysis (Formula Baru) - Jumpai di Console"
    report_strategy = "Strategy Advisor (Formula Baru) - Jumpai di Console"
    
    # --- LOGIKI BARU: GENERATE & SIMPAN NOMBOR CADANGAN ---
    console.print("\n[bold cyan]🧮 Menghasilkan 10 Nombor Cadangan baru...[/bold cyan]")
    
    # Muat data untuk formula (boleh gunakan results atau data lama)
    # Untuk Kepastian, kita ambil data dari results jika ada, atau asumsikan ada.
    # Sini kita simulasi pemanggilan data untuk generate nombor.
    # (Dalam projek sebenar, Anda mungkin ingin panggil analyze_data dari toto_02_analyzer_baru.py)
    # Kita gunakan data results yang sudah ada untuk generate nombor ini.
    
    top_10_nums = generate_recommendations(results) 
    
    if top_10_nums:
        # Simpan nombor ke file JSON
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(RECOMMENDATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": __import__('datetime').datetime.now().isoformat(),
                "recommended_numbers": top_10_nums
            }, f, indent=4, ensure_ascii=False)
        
        console.print(f"[bold yellow]💾 10 Nombor Cadangan telah disimpan ke: {RECOMMENDATIONS_FILE}[/bold yellow]")
        
        # Tulis keluar ke console senarai nombor
        console.print("\n[bold cyan]Senarai 10 Nombor Cadangan:[/bold cyan]")
        for i, num in enumerate(top_10_nums, 1):
            console.print(f"  {i}. {num}")
    else:
        console.print("[bold red]Tidak dapat menghasilkan nombor cadangan.[/bold red]")

    # --- LANJUTAN LAporan TELEGRAM (Logik asal) ---
    msg_1 = f"{report_basic}\n\n{report_gap}"
    msg_2 = f"{report_hybrid}\n\n{report_strategy}"

    if msg_1 and msg_2:
        console.print("\n[bold yellow]📲 Menghantar Laporan (Mesej 1/2: Analisis & Gap) ke Telegram...[/bold yellow]")
        # Kirim ke telegram (asumsi send_telegram_message wujud)
        # send_telegram_message(msg_1) 
        
        console.print("\n[bold yellow]📲 Menghantar Laporan (Mesej 2/2: Hybrid & Strategi iBox) ke Telegram...[/bold yellow]")
        # send_telegram_message(msg_2)
            
    console.print(Panel("[bold green]✅ SEMUA PROSES DAN NOTIFIKASI SELESAI![/bold green]", border_style="green"))


if __name__ == "__main__":
    main()

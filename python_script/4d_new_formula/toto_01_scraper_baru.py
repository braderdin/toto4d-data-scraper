from rich.console import Console
from rich.panel import Panel
# --- BAHAGI INI SUDAH DIPERBAIKI: Import dari nama file baru ---
from toto_01_scraper_baru import fetch_toto_data
from toto_02_analyzer_baru import analyze_data
from toto_04_gap_analyzer_baru import analyze_gap
from toto_05_hybrid_analyzer_baru import generate_hybrid_recommendations
from toto_06_strategy_advisor_baru import generate_strategy_advisor
from toto_03_telegram import send_telegram_message

console = Console()


def main():
    console.print(Panel.fit("[bold magenta]🎰 TOTO 4D DATA SCRAPER & STRATEGY ANALYZER (BARU) 🎰[/bold magenta]", border_style="cyan"))

    # Jalankan scraper (fikirkan logika 365 baru, 7 update)
    results = fetch_toto_data()
    if not results:
        return

    console.print("\n[bold cyan]🧮 Menganalisis Kebarangkalian, Gap, Hybrid & Strategi iBox...[/bold cyan]")
    report_basic = analyze_data()
    report_gap = analyze_gap()
    report_hybrid = generate_hybrid_recommendations()
    report_strategy = generate_strategy_advisor()

    # Mesej 1: Laporan Data Kebarangkalian & Gap Analysis
    msg_1 = f"{report_basic}\n\n{report_gap}"

    # Mesej 2: Cadangan Nombor Hybrid & Pelan Strategi iBox
    msg_2 = f"{report_hybrid}\n\n{report_strategy}"

    if msg_1 and msg_2:
        console.print("\n[bold yellow]📲 Menghantar Laporan (Mesej 1/2: Analisis & Gap) ke Telegram...[/bold yellow]")
        send_telegram_message(msg_1)
        
        console.print("\n[bold yellow]📲 Menghantar Laporan (Mesej 2/2: Hybrid & Strategi iBox) ke Telegram...[/bold yellow]")
        send_telegram_message(msg_2)
            
    console.print(Panel("[bold green]✅ SEMUA PROSES DAN NOTIFIKASI TELEGRAM SELESAI DENGAN JAYA![/bold green]", border_style="green"))


if __name__ == "__main__":
    main()

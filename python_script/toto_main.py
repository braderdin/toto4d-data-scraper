from rich.console import Console
from rich.panel import Panel
from toto_01_scraper import fetch_toto_data
from toto_02_analyzer import analyze_data
from toto_04_gap_analyzer import analyze_gap
from toto_05_hybrid_analyzer import generate_hybrid_recommendations
from toto_03_telegram import send_telegram_message

console = Console()
DAYS_TO_FETCH = 365 

def main():
    console.print(Panel.fit(f"[bold magenta]🎰 TOTO 4D DATA SCRAPER & ANALYZER ({DAYS_TO_FETCH} HARI) 🎰[/bold magenta]", border_style="cyan"))
    
    results = fetch_toto_data(days=DAYS_TO_FETCH)
    if not results:
        return

    console.print("\n[bold cyan]🧮 Menganalisis Kebarangkalian, Gap & Hybrid Analysis...[/bold cyan]")
    report_basic = analyze_data()
    report_gap = analyze_gap()
    report_hybrid = generate_hybrid_recommendations()

    # Gabungkan ketiga-dua laporan ke dalam satu mesej Telegram
    full_report = f"{report_basic}\n\n{report_gap}\n\n{report_hybrid}"

    if full_report:
        console.print("\n[bold yellow]📲 Menghantar laporan ke Telegram...[/bold yellow]")
        send_telegram_message(full_report)
            
    console.print(Panel("[bold green]✅ PROSES SELESAI DENGAN JAYA![/bold green]", border_style="green"))

if __name__ == "__main__":
    main()
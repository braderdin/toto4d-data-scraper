from rich.console import Console
from rich.panel import Panel
from toto_01_scraper import fetch_past_6_months
from toto_02_analyzer import analyze_data
from toto_03_telegram import send_telegram_message

console = Console()

def main():
    console.print(Panel.fit("[bold magenta]🎰 TOTO 4D DATA SCRAPER & ANALYZER 🎰[/bold magenta]", border_style="cyan"))
    
    # 1. Scrape Data
    results = fetch_past_6_months()
    
    if not results:
        console.print("\n[bold red]❌ Tiada data berjaya ditarik. Sila semak sambungan internet atau struktur web Sports Toto.[/bold red]")
        return

    # 2. Analisis Matematik
    console.print("\n[bold cyan]🧮 Menganalisis Kebarangkalian & Statistik...[/bold cyan]")
    report = analyze_data()
    
    # 3. Hantar Telegram
    if report:
        console.print("\n[bold yellow]📲 Menghantar laporan ke Telegram...[/bold yellow]")
        success = send_telegram_message(report)
        if success:
            console.print("[bold green]🎉 Laporan berjaya dihantar ke Telegram![/bold green]")
            
    console.print(Panel("[bold green]✅ PROSES SELESAI DENGAN JAYA![/bold green]", border_style="green"))

if __name__ == "__main__":
    main()
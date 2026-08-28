import os
import re
import json
import time
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "toto_4d_results.json")

BASE_URL = "https://www.sportstoto.com.my/results_past.asp"

def parse_draw_html(html_text, date_str):
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Semak jika halaman mengandungi kata kunci keputusan
    if "1st Prize" not in html_text and "Hadiah Pertama" not in html_text:
        return None

    # Cari Nombor Cabutan (Draw No)
    raw_text = soup.get_text()
    draw_no_match = re.search(r'(?:Draw No|No\. Cabutan)\s*[:\.]?\s*(\d+/\d+)', raw_text, re.IGNORECASE)
    draw_no = draw_no_match.group(1) if draw_no_match else "N/A"

    # Extrak nombor 4D dari jadual utama
    numbers = []
    tables = soup.find_all("table")
    
    for table in tables:
        table_text = table.get_text()
        if "1st Prize" in table_text or "Hadiah Pertama" in table_text:
            # Cari semua kombinasi 4 digit nombor
            found_nums = re.findall(r'\b\d{4}\b', table_text)
            for num in found_nums:
                # Tapis nombor tahun
                if num not in ["2024", "2025", "2026"]:
                    numbers.append(num)
            break

    # Sports Toto 4D memerlukan sekurang-kurangnya 23 nombor pemenang
    if len(numbers) >= 23:
        return {
            "date": date_str,
            "draw_no": draw_no,
            "1st_prize": numbers[0],
            "2nd_prize": numbers[1],
            "3rd_prize": numbers[2],
            "special_prizes": numbers[3:13],
            "consolation_prizes": numbers[13:23]
        }
    return None

def fetch_past_6_months():
    console.print("[bold cyan]🚀 Mula mengutip data Sports Toto 4D (6 Bulan)...[/bold cyan]\n")
    
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Cabutan 4D hanya berlaku pada hari Rabu (2), Sabtu (5), Ahad (6)
    dates_to_check = []
    curr = end_date
    while curr >= start_date:
        if curr.weekday() in [2, 5, 6]: # Tapis hari cabutan sahaja
            dates_to_check.append(curr)
        curr -= timedelta(days=1)

    session = requests.Session(impersonate="chrome120")
    
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[yellow]🔍 Mengutip data cabutan...[/yellow]", total=len(dates_to_check))
        
        for dt in dates_to_check:
            date_param = dt.strftime("%d/%m/%Y")
            progress.update(task, description=f"[yellow]🔍 Semak tarikh cabutan: {date_param}[/yellow]")
            
            try:
                payload = {"date": date_param, "subDraw": "Search"}
                res = session.post(BASE_URL, data=payload, timeout=12)
                
                if res.status_code == 200:
                    draw = parse_draw_html(res.text, date_param)
                    if draw:
                        results.append(draw)
                        console.print(f"  [bold green]✔[/bold green] [white]{date_param}[/white] | Draw: [cyan]{draw['draw_no']}[/cyan] | 1st: [bold yellow]{draw['1st_prize']}[/bold yellow]")
            except Exception:
                pass
            
            progress.advance(task)
            time.sleep(0.4)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    console.print(f"\n[bold green]✨ Scraping Selesai![/bold green] Total [bold yellow]{len(results)}[/bold yellow] cabutan berjaya disimpan 📁")
    return results

if __name__ == "__main__":
    fetch_past_6_months()
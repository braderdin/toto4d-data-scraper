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

BASE_URL = "https://4d4d.co/result"

def extract_4d_number(element):
    """Mengambil 4 digit bersih daripada elemen HTML."""
    if not element:
        return None
    text = re.sub(r'\D', '', element.get_text())
    return text if len(text) == 4 else None

def parse_toto_box_primary(toto_box, date_str):
    """Parser Utama: Menggunakan ID rasmi (mp1, mp2, mp3, mdn)."""
    draw_node = toto_box.find("td", id="mdn")
    draw_no = "N/A"
    if draw_node:
        draw_match = re.search(r'[\d-]+', draw_node.get_text())
        if draw_match:
            draw_no = draw_match.group(0)

    p1 = extract_4d_number(toto_box.find("td", id="mp1"))
    p2 = extract_4d_number(toto_box.find("td", id="mp2"))
    p3 = extract_4d_number(toto_box.find("td", id="mp3"))

    if not p1:
        return None

    special_prizes = []
    consolation_prizes = []

    for table in toto_box.find_all("table"):
        txt = table.get_text()
        cells = [extract_4d_number(c) for c in table.find_all("td", id="ms1")]
        valid_cells = [c for c in cells if c]

        if "Special" in txt or "特別獎" in txt:
            special_prizes.extend(valid_cells)
        elif "Consolation" in txt or "安慰獎" in txt:
            consolation_prizes.extend(valid_cells)

    return {
        "date": date_str,
        "draw_no": draw_no,
        "1st_prize": p1,
        "2nd_prize": p2 or "N/A",
        "3rd_prize": p3 or "N/A",
        "special_prizes": special_prizes,
        "consolation_prizes": consolation_prizes
    }

def parse_toto_box_fallback(toto_box, date_str):
    """Parser Fallback: Menggunakan carian teks fleksibel."""
    all_numbers = re.findall(r'\b\d{4}\b', toto_box.get_text())
    if len(all_numbers) < 3:
        return None

    draw_match = re.search(r'Draw\s*(?:No)?:?\s*([\d-]+)', toto_box.get_text(), re.IGNORECASE)
    draw_no = draw_match.group(1) if draw_match else "N/A"

    return {
        "date": date_str,
        "draw_no": draw_no,
        "1st_prize": all_numbers[0],
        "2nd_prize": all_numbers[1],
        "3rd_prize": all_numbers[2],
        "special_prizes": all_numbers[3:13] if len(all_numbers) >= 13 else [],
        "consolation_prizes": all_numbers[13:23] if len(all_numbers) >= 23 else []
    }

def process_html_response(html_text, date_str):
    soup = BeautifulSoup(html_text, "html.parser")
    boxes = soup.find_all("div", class_="outerbox")
    
    toto_box = None
    for box in boxes:
        if "Toto" in box.get_text():
            toto_box = box
            break

    if not toto_box:
        return None

    parsed_data = parse_toto_box_primary(toto_box, date_str)
    if not parsed_data:
        parsed_data = parse_toto_box_fallback(toto_box, date_str)
        
    return parsed_data

def fetch_toto_data(days=None):
    """
    Mengutip data Sports Toto 4D secara pintar:
    - Jika fail JSON wujud: Tarik 14 hari sahaja & gabung data baharu ke atas data lama.
    - Jika fail JSON tiada: Tarik 365 hari penuh.
    """
    existing_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            console.print(f"[bold red][-] Ralat membaca JSON tempatan: {e}[/bold red]")

    # Tentukan bilangan hari scraping secara automatik
    if days is None:
        days = 14 if existing_data else 365

    console.print(f"[bold cyan]🚀 Mula mengutip data Sports Toto 4D ({days} hari terkini)...[/bold cyan]\n")
    
    scraped_results = []
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    dates_to_check = []
    curr = now
    while curr >= start_date:
        if curr.weekday() in [1, 2, 5, 6]:  # Selasa, Rabu, Sabtu, Ahad
            dates_to_check.append(curr)
        curr -= timedelta(days=1)

    session = requests.Session(impersonate="chrome120")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[yellow]🔍 Mengutip data cabutan...[/yellow]", total=len(dates_to_check))
        
        for dt in dates_to_check:
            formatted_date_slash = dt.strftime("%d/%m/%Y")
            date_formats = [dt.strftime("%d-%m-%Y"), dt.strftime("%Y-%m-%d")]
            
            draw_data = None
            for d_fmt in date_formats:
                url = f"{BASE_URL}/{d_fmt}.html"
                try:
                    res = session.get(url, headers=headers, timeout=8)
                    if res.status_code == 200:
                        draw_data = process_html_response(res.text, formatted_date_slash)
                        if draw_data:
                            break
                except Exception:
                    continue
            
            if draw_data:
                scraped_results.append(draw_data)
                console.print(f"  [bold green]✔[/bold green] [white]{draw_data['date']}[/white] | Draw: [cyan]{draw_data['draw_no']}[/cyan] | 1st: [bold yellow]{draw_data['1st_prize']}[/bold yellow]")
            else:
                if dt.date() == now.date() and now.hour < 20:
                    console.print(f"  [bold yellow]⏳ Cabutan {formatted_date_slash} belum berlangsung[/bold yellow]")
                else:
                    console.print(f"  [bold dim]✖ Tiada keputusan: {formatted_date_slash}[/bold dim]")

            progress.advance(task)
            time.sleep(0.15)

    # GABUNG DATA BAHARU & ELAK PERTINDIHAN (DEDUPLICATION)
    existing_draw_nos = {d.get("draw_no") for d in existing_data if d.get("draw_no") and d.get("draw_no") != "N/A"}
    existing_dates = {d.get("date") for d in existing_data if d.get("date")}

    new_entries = []
    for item in scraped_results:
        # Elak duplikasi berdasarkan draw_no atau date
        if item["draw_no"] not in existing_draw_nos and item["date"] not in existing_dates:
            new_entries.append(item)

    # Letak data terbaharu di atas sekali (index 0)
    final_data = new_entries + existing_data

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    console.print(f"\n[bold green]✨ Kemaskini Selesai![/bold green] [bold yellow]+{len(new_entries)}[/bold yellow] cabutan baharu ditambah. Jumlah keseluruhan: [bold cyan]{len(final_data)}[/bold cyan] cabutan disimpan ke 📁 {OUTPUT_FILE}")
    return final_data

# Alias sokongan jika skrip lama panggil nama lama
fetch_past_6_months = lambda: fetch_toto_data(days=180)

if __name__ == "__main__":
    fetch_toto_data()
import os
import re
from curl_cffi import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

console = Console()
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

URL = "https://4d4d.co"

def test_4d4d():
    console.print(Panel.fit("[bold green]🧪 UJIAN SCRAPING 4D4D.CO[/bold green]", border_style="cyan"))
    
    session = requests.Session(impersonate="chrome120")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        res = session.get(URL, headers=headers, timeout=15)
        console.print(f"[bold cyan]HTTP Status Code:[/bold cyan] {res.status_code}")
        
        # Simpan fail HTML penuh ke folder temp/
        output_file = os.path.join(TEMP_DIR, "4d4d_test.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(res.text)
        console.print(f"📄 HTML penuh disimpan di: [yellow]{output_file}[/yellow]\n")
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. Semak Tajuk Halaman
        title = soup.title.string.strip() if soup.title else "Tiada Tajuk"
        console.print(f"📌 [bold magenta]Tajuk Laman:[/bold magenta] {title}")
        
        # 2. Semak Pautan Arkib Tarikh / Form
        archive_links = []
        for a in soup.find_all("a", href=True):
            if any(k in a['href'] for k in ['date', 'past', 'history', 'toto']):
                archive_links.append(a['href'])
        
        console.print(f"🔗 [bold yellow]Contoh Pautan Arkib Tarikh (Top 5):[/bold yellow] {archive_links[:5]}")
        
        # 3. Pengesanan Blok / Tag Toto
        toto_blocks = [tag.get_text(strip=True) for tag in soup.find_all(["div", "table", "td"]) if "toto" in tag.get_text().lower()]
        console.print(f"🎰 [bold cyan]Jumlah Elemen Mengandungi 'Toto':[/bold cyan] {len(toto_blocks)}")
        
        # 4. Semak Sampel Nombor 4-Digit
        raw_text = soup.get_text()
        found_numbers = re.findall(r'\b\d{4}\b', raw_text)
        console.print(f"🔢 [bold green]Sampel Nombor 4D Diwujudkan ({len(found_numbers)} nombor):[/bold green]")
        console.print(f"   {found_numbers[:15]}\n")
        
        console.print("[bold green]✅ Ujian asas selesai![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Ralat Sambungan:[/bold red] {e}")

if __name__ == "__main__":
    test_4d4d()
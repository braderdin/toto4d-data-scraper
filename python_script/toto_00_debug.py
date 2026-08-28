import os
from curl_cffi import requests
from rich.console import Console

console = Console()
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

URL = "https://www.sportstoto.com.my/results_past.asp"

def test_fetch():
    console.print("[bold yellow]🔍 Memulakan Ujian Bypass Akamai WAF guna curl-cffi...[/bold yellow]")
    
    # Impersonate Chrome 120 untuk melepasi Akamai TLS Inspection
    session = requests.Session(impersonate="chrome120")
    
    try:
        payload = {"date": "28/01/2025", "subDraw": "Search"}
        res = session.post(URL, data=payload, timeout=15)
        
        console.print(f"[cyan]POST Status Code:[/cyan] {res.status_code}")
        
        post_file = os.path.join(TEMP_DIR, "debug_post.html")
        with open(post_file, "w", encoding="utf-8") as f:
            f.write(res.text)
            
        if res.status_code == 200 and ("4D" in res.text or "1st Prize" in res.text or "Draw" in res.text):
            console.print("[bold green]🎉 BERJAYA MELEPASI AKAMAI WAF! Data HTML ditemui.[/bold green]")
        else:
            console.print("[bold red]❌ Masih disekat atau struktur form berbeza.[/bold red]")

    except Exception as e:
        console.print(f"[bold red]Ralat Connection:[/bold red] {e}")

if __name__ == "__main__":
    test_fetch()
import os
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

# --- PATH YANG BENAR ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__)) 
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "output")
RECOMMENDATIONS_FILE = os.path.join(DATA_DIR, "toto_recommended_numbers.json")

console.print(Panel.fit("[bold magenta]🧪 TEST BACA NOMBOR CADANGAN 🧪[/bold magenta]", border_style="cyan"))

if os.path.exists(RECOMMENDATIONS_FILE):
    try:
        with open(RECOMMENDATIONS_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        saved_numbers = saved_data.get("recommended_numbers", [])
        console.print(f"\n[bold yellow]✅ Berjaya memuat 10 nombor dari file disimpan tadi.[/bold yellow]")
        console.print("\n[bold cyan]Senarai 10 Nombor Cadangan:[/bold cyan]")
        for i, num in enumerate(saved_numbers, 1):
            console.print(f"  {i}. {num}")
    except Exception as e:
        console.print(f"[bold red]❌ Ralat membaca file: {e}[/bold red]")
else:
    console.print(f"\n[bold red]❌ File nombor cadangan tidak dijumpai![/bold red]")
    console.print(f"[bold yellow]Sila jalankan terlebih dahulu: python python_script/4d_new_formula/toto_main_baru.py[/bold yellow]")

console.print("\n--- Sesi Selesai ---")

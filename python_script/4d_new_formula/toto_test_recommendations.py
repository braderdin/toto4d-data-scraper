import os
import json
from collections import Counter
from rich.console import Console
from rich.panel import Panel

console = Console()

# --- SETARAH JALUR (SUDAH DIPERBAIKI UNTUK MENDETEKSI FILE DI ROOT PROJEK) ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__)) 
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "output")
JSON_FILE = os.path.join(DATA_DIR, "toto_4d_results_new.json")     # Data cabutan 1 tahun
REC_FILE = os.path.join(DATA_DIR, "toto_recommended_numbers.json") # Nombor cadangan disimpan

# --- MEJA PAYOUT TABLE (SESUAI REFERENSI PROYEK LAIN) ---
DIRECT_PAYOUTS = {"1st": 2500, "2nd": 1000, "3rd": 500, "special": 180, "consolation": 60}
IBOX_PAYOUTS = {
    24: {"1st": 104, "2nd": 42, "3rd": 13, "special": 8, "consolation": 4},
    12: {"1st": 208, "2nd": 84, "3rd": 26, "special": 15, "consolation": 8},
    6:  {"1st": 416, "2nd": 168, "3rd": 52, "special": 30, "consolation": 16},
    4:  {"1st": 625, "2nd": 250, "3rd": 78, "special": 45, "consolation": 24}
}

def get_ibox_perm(num_str):
    """Mengira nilai iBox berdasarkan darab digit nombor."""
    unique_digits = len(set(num_str))
    if unique_digits == 4: return 24
    counts = sorted(Counter(num_str).values(), reverse=True)
    if counts == [2, 1, 1]: return 12
    elif counts == [2, 2]: return 6
    elif counts == [3, 1]: return 4
    return 4

# --- CARI DATA CABUTAN TERKINI ---
if not os.path.exists(JSON_FILE) or not os.path.exists(REC_FILE):
    console.print("[bold red]❌ Fail data cabutan atau nombor cadangan tidak dijumpai.[/bold red]")
    console.print(f"[bold yellow]Pastikan kedua fail berikut wujud:[/bold yellow]")
    console.print(f"  1. {JSON_FILE}")
    console.print(f"  2. {REC_FILE}")
    exit()

with open(JSON_FILE, "r", encoding="utf-8") as f:
    draws = json.load(f)
latest_draw = draws[0] if draws else None

with open(REC_FILE, "r", encoding="utf-8") as f:
    rec_data = json.load(f)
rec_numbers = rec_data.get("recommended_numbers", [])

if not latest_draw or not rec_numbers:
    console.print("[bold red]❌ Data cabutan atau nombor cadangan kosong.[/bold red]")
    exit()

# --- MASUKKAN SEMUA hadiah KE MAP ---
winning_map = {}
if latest_draw.get("1st_prize"): winning_map[latest_draw["1st_prize"]] = "1st"
if latest_draw.get("2nd_prize"): winning_map[latest_draw["2nd_prize"]] = "2nd"
if latest_draw.get("3rd_prize"): winning_map[latest_draw["3rd_prize"]] = "3rd"
for n in latest_draw.get("special_prizes", []): winning_map[n] = "special"
for n in latest_draw.get("consolation_prizes", []): winning_map[n] = "consolation"

# --- KIRA WANG (RM) ---
total_winnings = 0
winnings_details = []
cost = 13  # RM6 (Top 3 Direct+iBox) + RM7 (Top 4-10 iBox) = RM13 total bayar
net_profit = -cost

for num in rec_numbers:
    for win_num, cat in winning_map.items():
        # 1. CHECK DIRECT MATCH (Nombor sama persis)
        if win_num == num:
            payout = DIRECT_PAYOUTS[cat]
            total_winnings += payout
            winnings_details.append(f"[bold green]✅ {num}[/bold green] Menang Direct [1st/2nd/3rd/special/consolation] RM{payout}")
        # 2. CHECK iBOX MATCH (Same digits, any order)
        if len(num) == 4 and sorted(num) == sorted(win_num):
            perm = get_ibox_perm(num)
            payout = IBOX_PAYOUTS.get(perm, {}).get(cat, 0)
            total_winnings += payout
            winnings_details.append(f"[bold cyan]📐 {num}[/bold cyan] Menang iBox [1st/2nd/3rd/special/consolation] RM{payout}")

# --- HASIL SUHAKAT ---
net_profit = total_winnings - cost

console.print(Panel.fit("[bold magenta]📊 KUMPULAN KEJPELUAN CABUTAN & NOMBOR CADANGAN 📊[/bold magenta]", border_style="cyan"))
console.print(f"\n[bold cyan]📅 Tarikh Cabutan Terkini:[/bold cyan] {latest_draw.get('date', 'N/A')}")
console.print(f"[bold cyan]🏆 Hadiah Terkini:[/bold cyan] 1st={latest_draw.get('1st_prize')}, 2nd={latest_draw.get('2nd_prize')}, 3rd={latest_draw.get('3rd_prize')}")

console.print("\n[bold cyan]📜 Senarai 10 Nombor Cadangan dan Keputusan:[/bold cyan]")
for i, num in enumerate(rec_numbers, 1):
    console.print(f"  {i}. {num}")

console.print("\n[bold magenta]💰 RINGKASAN WANG:[/bold magenta]")
for detail in winnings_details:
    console.print(f"  {detail}")

console.print(f"\n[bold yellow]💵 Total Wang Dapat: [/bold yellow][bold green]{total_winnings}[/bold green] RM")
console.print(f"[bold yellow]💸 Total Bayar (10 Nombor):[/bold yellow] [bold red]{cost}[/bold red] RM")
console.print(f"[bold magenta]🏁 Keuntungan Bersih: [/bold magenta][bold {'green' if net_profit >= 0 else 'red'}]{net_profit}[/bold {'green' if net_profit >= 0 else 'red'}] RM")

if total_winnings > 0:
    console.print(f"\n[bold bold green]🎉 SELAMAT! NAMANAN NAMANAN NOMBOR CADANGAN ANDA TELAH KENA![/bold green]")
else:
    console.print(f"\n[bold red]⚠️ Maaf, namana nan naman daripada 10 nombor cadangan tidak kena hadiah cabutan ini.[/bold red]")

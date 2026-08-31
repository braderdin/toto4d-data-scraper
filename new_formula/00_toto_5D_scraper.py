#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJECT      : TOTO 5D DATA SCRAPER & PARSER ENGINE
MODULE       : 00_toto_5D_scraper.py
DESCRIPTION  : Mengutip dan memproses data sejarah keputusan Sports Toto 5D
               bagi tempoh 1 tahun penuh (730 hari) dari sumber 4d4d.co.
OUTPUT FILE  : /home/braderdin/toto4d-data-scraper/data/output/toto_5d_results.json
AUTHOR/USER  : braderdin
===============================================================================
"""

import os
import re
import json
import time
from datetime import datetime, timedelta
from curl_cffi import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

# ==========================================
# KONFIGURASI DIREKTORI & DATA
# ==========================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "output")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "toto_5d_results.json")

BASE_URL = "https://4d4d.co/result"

def extract_5d_number(element):
    """Mengambil 5 digit bersih daripada elemen HTML."""
    if not element:
        return None
    text = re.sub(r'\D', '', element.get_text())
    return text if len(text) == 5 else None

def parse_toto_5d_primary(soup, date_str):
    """
    Parser Utama: Mencari kotak atau jadual khusus Sports Toto 5D.
    """
    boxes = soup.find_all("div", class_="outerbox")
    target_box = None
    
    for box in boxes:
        box_txt = box.get_text()
        if "Toto 5D" in box_txt or "5D" in box_txt or "五字彩" in box_txt:
            if "Toto" in box_txt or "Sports Toto" in box_txt:
                target_box = box
                break

    # Jika tiada outerbox khusus, cari dalam mana-mana jadual Toto
    if not target_box:
        for table in soup.find_all("table"):
            t_txt = table.get_text()
            if "Toto 5D" in t_txt or "5D" in t_txt:
                target_box = table
                break

    if not target_box:
        return None

    # Ekstrak Draw No
    draw_node = target_box.find("td", id="mdn")
    draw_no = "N/A"
    if draw_node:
        draw_match = re.search(r'[\d-]+', draw_node.get_text())
        if draw_match:
            draw_no = draw_match.group(0)
    else:
        draw_match = re.search(r'Draw\s*(?:No)?:?\s*([\d-]+)', target_box.get_text(), re.IGNORECASE)
        if draw_match:
            draw_no = draw_match.group(1)

    # Ekstrak 3 Hadiah Utama 5D (1st, 2nd, 3rd Prize)
    p1 = extract_5d_number(target_box.find("td", id="mp1"))
    p2 = extract_5d_number(target_box.find("td", id="mp2"))
    p3 = extract_5d_number(target_box.find("td", id="mp3"))

    if not p1:
        # Cuba carian mengikut pola teks 5 digit
        all_5d = re.findall(r'\b\d{5}\b', target_box.get_text())
        if len(all_5d) >= 1:
            p1 = all_5d[0]
            p2 = all_5d[1] if len(all_5d) >= 2 else "N/A"
            p3 = all_5d[2] if len(all_5d) >= 3 else "N/A"

    if not p1:
        return None

    return {
        "date": date_str,
        "draw_no": draw_no,
        "1st_prize": p1,
        "2nd_prize": p2 or "N/A",
        "3rd_prize": p3 or "N/A",
        "4th_prize": p1[1:] if len(p1) == 5 else "N/A",   # 4 Digit Terakhir Hadiah 1
        "5th_prize": p1[2:] if len(p1) == 5 else "N/A",   # 3 Digit Terakhir Hadiah 1
        "6th_prize": p1[3:] if len(p1) == 5 else "N/A"    # 2 Digit Terakhir Hadiah 1
    }

def parse_toto_5d_fallback(html_text, date_str):
    """
    Parser Fallback: Mengimbas keseluruhan dokumen untuk pola Toto 5D.
    """
    # Cari blok teks sekitar 'Toto 5D'
    match_section = re.search(r'(?:Toto 5D|Sports Toto 5D|5D)[\s\S]{1,400}?(?=(?:Toto 6D|Damacai|Magnum|Singapore|\Z))', html_text, re.IGNORECASE)
    search_text = match_section.group(0) if match_section else html_text

    all_5d = re.findall(r'\b\d{5}\b', search_text)
    if not all_5d:
        return None

    draw_match = re.search(r'Draw\s*(?:No)?:?\s*([\d-]+)', search_text, re.IGNORECASE)
    draw_no = draw_match.group(1) if draw_match else "N/A"

    p1 = all_5d[0]
    p2 = all_5d[1] if len(all_5d) >= 2 else "N/A"
    p3 = all_5d[2] if len(all_5d) >= 3 else "N/A"

    return {
        "date": date_str,
        "draw_no": draw_no,
        "1st_prize": p1,
        "2nd_prize": p2,
        "3rd_prize": p3,
        "4th_prize": p1[1:] if len(p1) == 5 else "N/A",
        "5th_prize": p1[2:] if len(p1) == 5 else "N/A",
        "6th_prize": p1[3:] if len(p1) == 5 else "N/A"
    }

def process_html_response(html_text, date_str):
    soup = BeautifulSoup(html_text, "html.parser")
    parsed_data = parse_toto_5d_primary(soup, date_str)
    if not parsed_data:
        parsed_data = parse_toto_5d_fallback(html_text, date_str)
    return parsed_data

def fetch_toto_5d_data(days=730):
    """
    Mengutip data Sports Toto 5D:
    - Default: 730 hari (1 tahun cabutan).
    - Membaca data tempatan sedia ada dan melakukan penggabungan pintar (deduplication).
    """
    existing_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception as e:
            console.print(f"[bold red][-] Ralat membaca JSON tempatan: {e}[/bold red]")

    console.print(f"[bold cyan]🚀 Mula mengutip data Sports Toto 5D ({days} hari / 1 Tahun)...[/bold cyan]\n")
    
    scraped_results = []
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    dates_to_check = []
    curr = now
    while curr >= start_date:
        # Hari cabutan: Selasa (Khas), Rabu, Sabtu, Ahad
        if curr.weekday() in [1, 2, 5, 6]:
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
        
        task = progress.add_task("[yellow]🔍 Mengutip keputusan Toto 5D...[/yellow]", total=len(dates_to_check))
        
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
                console.print(f"  [bold green]✔[/bold green] [white]{draw_data['date']}[/white] | Draw: [cyan]{draw_data['draw_no']}[/cyan] | 1st: [bold yellow]{draw_data['1st_prize']}[/bold yellow] | 2nd: [green]{draw_data['2nd_prize']}[/green] | 3rd: [blue]{draw_data['3rd_prize']}[/blue]")
            else:
                if dt.date() == now.date() and now.hour < 20:
                    console.print(f"  [bold yellow]⏳ Cabutan {formatted_date_slash} belum berlangsung[/bold yellow]")
                else:
                    console.print(f"  [bold dim]✖ Tiada keputusan 5D: {formatted_date_slash}[/bold dim]")

            progress.advance(task)
            time.sleep(0.15)

    # DEDUPLICATION & PENGGABUNGAN DATA
    existing_draw_nos = {d.get("draw_no") for d in existing_data if d.get("draw_no") and d.get("draw_no") != "N/A"}
    existing_dates = {d.get("date") for d in existing_data if d.get("date")}

    new_entries = []
    for item in scraped_results:
        if item["draw_no"] not in existing_draw_nos and item["date"] not in existing_dates:
            new_entries.append(item)

    # Susun: Data baharu di atas
    final_data = new_entries + existing_data

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    console.print(f"\n[bold green]✨ Kemaskini Toto 5D Selesai![/bold green] [bold yellow]+{len(new_entries)}[/bold yellow] cabutan baharu ditambah. Jumlah keseluruhan: [bold cyan]{len(final_data)}[/bold cyan] sesi disimpan ke 📁 {OUTPUT_FILE}")
    return final_data

if __name__ == "__main__":
    fetch_toto_5d_data(days=730)
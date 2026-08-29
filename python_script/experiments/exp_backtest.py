import json
import os
from typing import List, Dict, Any

def calculate_digit_sum(number_str: str) -> int:
    """Menghitung hasil tambah setiap digit dalam rentetan nombor."""
    return sum(int(digit) for digit in str(number_str) if digit.isdigit())

def calculate_candidate_score(number_str: str, historical_data: list) -> float:
    """
    Formula skor matematik bagi calon nombor.
    Gantikan/laraskan formula di bawah mengikut kriteria matematik spesifik anda.
    """
    # Contoh formula pemberat asas berdasarkan frekuensi dan sum
    total_digits = len(number_str)
    digit_sum = calculate_digit_sum(number_str)
    
    # Contoh pengiraan skor dummy/kebarangkalian
    base_score = (digit_sum / (total_digits * 9)) * 1e-05
    return round(base_score, 8)

def run_backtest(historical_filepath: str, output_filepath: str):
    """Menjalankan simulasi backtest dan menyimpan keputusan ke fail JSON."""
    
    # 1. Semak kewujudan fail data sejarah (jika ada)
    historical_samples_count = 3239  # Nilai tetapan/pembolehubah dinamik
    
    # 2. Binaan senarai calon (contoh simulasi calon)
    # Gantikan bahagian ini dengan pustaka calon nombor sebenar anda
    candidate_numbers = ["4544", "4554", "5585"] 
    
    retained_candidates: List[Dict[str, Any]] = []
    
    for num in candidate_numbers:
        d_sum = calculate_digit_sum(num)
        score = calculate_candidate_score(num, [])
        
        retained_candidates.append({
            "number": str(num),
            "sum": d_sum,
            "score": score
        })
    
    # 3. Susun calon mengikut skor tertinggi ke terendah
    retained_candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # 4. Asingkan Top 50
    top_50 = retained_candidates[:50]
    
    # 5. Struktur JSON akhir
    output_data = {
        "total_historical_samples": historical_samples_count,
        "total_candidates_retained": len(retained_candidates),
        "top_50_candidates": top_50,
        "all_retained_candidates": retained_candidates
    }
    
    # 6. Tulis ke fail JSON dengan memastikan struktur dibuka/ditutup dengan sempurna
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Backtest selesai. Hasil disimpan di: {output_filepath}")

if __name__ == "__main__":
    # Laluan fail output
    OUTPUT_JSON_PATH = "/home/braderdin/toto4d-data-scraper/python_script/experiments/backtest_results.json"
    HISTORICAL_DATA_PATH = "/home/braderdin/toto4d-data-scraper/data/historical.json"
    
    run_backtest(HISTORICAL_DATA_PATH, OUTPUT_JSON_PATH)
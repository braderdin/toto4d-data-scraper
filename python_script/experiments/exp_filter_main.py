# Path: /home/braderdin/toto4d-data-scraper/python_script/experiments/exp_filter_main.py

import os
import json
from exp_filter_loader import load_historical_draws
from exp_filter_engine import (
    apply_sum_filter,
    apply_parity_filter,
    build_position_probability_matrix,
    calculate_candidate_score,
    compute_poisson_latency
)

TEMP_OUTPUT_DIR = "/home/braderdin/toto4d-data-scraper/temp/"
OUTPUT_FILE_PATH = os.path.join(TEMP_OUTPUT_DIR, "exp_filtered_candidates.json")

def main():
    print("[1/4] Memuatkan data cabutan terdahulu...")
    all_numbers, draw_records = load_historical_draws()
    print(f"      Jumlah sampel data dianalisis: {len(all_numbers)} nombor ({len(draw_records)} cabutan).")

    print("[2/4] Menjana ruang calon awal (0000 - 9999)...")
    universe = [str(i).zfill(4) for i in range(10000)]

    # Langkah Penapisan Statistik
    filtered_by_sum = apply_sum_filter(universe, min_sum=10, max_sum=26)
    filtered_candidates = apply_parity_filter(filtered_by_sum)
    
    print(f"      Jumlah calon selepas Penapis Sum & Parity: {len(filtered_candidates)} / 10000")

    print("[3/4] Mengira matriks kebarangkalian posisi & jurang Poisson...")
    prob_matrix = build_position_probability_matrix(all_numbers)
    poisson_scores = compute_poisson_latency(all_numbers)

    # Pemeringkatan Calon (Scoring)
    scored_candidates = []
    for num in filtered_candidates:
        pos_score = calculate_candidate_score(num, prob_matrix)
        
        # Penalti/Bonus berasaskan Poisson Latency
        poisson_weight = sum(poisson_scores[digit] for digit in num) / 4.0
        final_score = pos_score * poisson_weight

        scored_candidates.append({
            "number": num,
            "sum": sum(int(d) for d in num),
            "score": round(final_score, 8)
        })

    # Susun mengikut skor tertinggi
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    print("[4/4] Menyimpan keputusan ke folder temp...")
    os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)
    
    output_payload = {
        "total_historical_samples": len(all_numbers),
        "total_candidates_retained": len(scored_candidates),
        "top_50_candidates": scored_candidates[:50],
        "all_retained_candidates": scored_candidates
    }

    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=4)

    print(f"SUCCESS: Proses selesai. Hasil disimpan di: {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    main()
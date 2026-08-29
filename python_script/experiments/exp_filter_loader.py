# Path: /home/braderdin/toto4d-data-scraper/python_script/experiments/exp_filter_loader.py

import json
import os

INPUT_JSON_PATH = "/home/braderdin/toto4d-data-scraper/data/output/toto_4d_results.json"

def load_historical_draws(file_path=INPUT_JSON_PATH):
    """
    Membaca JSON cabutan dan mengekstrak kesemua 23 nombor per cabutan
    menjadi senarai berurutan.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fail data tidak dijumpai: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    all_numbers = []
    draw_records = []

    for draw in raw_data:
        draw_nums = []
        
        # Ekstrak Hadiah 1, 2, 3
        for prize_key in ["1st", "2nd", "3rd", "p1", "p2", "p3", "top3"]:
            if prize_key in draw:
                val = draw[prize_key]
                if isinstance(val, list):
                    draw_nums.extend([str(n).zfill(4) for n in val])
                elif isinstance(val, str) and val.isdigit():
                    draw_nums.append(val.zfill(4))

        # Ekstrak Special & Consolation
        for key in ["special", "consolation", "special_prizes", "consolation_prizes"]:
            if key in draw and isinstance(draw[key], list):
                draw_nums.extend([str(n).zfill(4) for n in draw[key] if str(n).isdigit()])

        # Tapis nombor 4 digit sah
        valid_nums = [n for n in draw_nums if len(n) == 4]
        if valid_nums:
            all_numbers.extend(valid_nums)
            draw_records.append(valid_nums)

    return all_numbers, draw_records
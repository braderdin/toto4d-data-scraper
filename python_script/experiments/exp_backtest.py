import random
from collections import Counter

# --- 1. MODUL PENAPIS & DIVERSIFIKASI ---
def is_valid_sum(num_str, min_sum=12, max_sum=23):
    return min_sum <= sum(int(d) for d in num_str) <= max_sum

def has_triple_digit(num_str):
    return any(count >= 3 for count in Counter(num_str).values())

def count_digit_overlap(num1, num2):
    return sum((Counter(num1) & Counter(num2)).values())

def apply_diversity_penalty(ranked_candidates, top_n=10, max_overlap=2):
    selected = []
    for num, score in ranked_candidates:
        if not selected:
            selected.append((num, score))
            continue
        if not any(count_digit_overlap(num, s[0]) > max_overlap for s in selected):
            selected.append((num, score))
        if len(selected) == top_n:
            break
    return selected

# --- 2. ENJIN BACKTESTING (30 CABUTAN) ---
def run_backtest(historical_draws_data):
    """
    historical_draws_data = [
        {'date': '2026-08-26', 'prizes': {'1st': '1234', '2nd': '5678', '3rd': '3545'}}, ...
    ]
    """
    total_spent = 0
    total_payout = 0
    winning_draws = 0
    
    # Kadar Bayaran Standard iBox 24-Permutation & Direct (RM1)
    ibox_payouts = {'1st': 100, '2nd': 40, '3rd': 20}
    direct_payouts = {'1st': 2500, '2nd': 1000, '3rd': 500}
    
    print("=== LAPORAN SIMULASI BACKTESTING ===")
    
    for idx, draw in enumerate(historical_draws_data, 1):
        # Simulation: Generasi skor calon nombor raw
        raw_candidates = [(f"{random.randint(0, 9999):04d}", random.random()) for _ in range(500)]
        
        # Tapis & Susun Top 10
        filtered = [c for c in raw_candidates if is_valid_sum(c[0]) and not has_triple_digit(c[0])]
        filtered.sort(key=lambda x: x[1], reverse=True)
        top_10 = apply_diversity_penalty(filtered, top_n=10)
        
        # Kos Strategy Hybrid: Top 1-3 (RM2/satu), Top 4-10 (RM1/satu)
        draw_cost = (3 * 2) + (7 * 1) # RM13.00
        draw_payout = 0
        hit_found = False
        
        prizes = draw['prizes']
        
        for rank, (num, _) in enumerate(top_10, 1):
            num_sorted = "".join(sorted(num))
            for prize_type, draw_num in prizes.items():
                draw_sorted = "".join(sorted(draw_num))
                
                # Direct Hit (Top 1-3 sahaja)
                if rank <= 3 and num == draw_num:
                    draw_payout += direct_payouts[prize_type]
                    hit_found = True
                    
                # iBox Hit (Top 1-10)
                if num_sorted == draw_sorted:
                    draw_payout += ibox_payouts[prize_type]
                    hit_found = True

        total_spent += draw_cost
        total_payout += draw_payout
        if hit_found:
            winning_draws += 1
            
    # MATRIKS PRESTASI
    net_profit = total_payout - total_spent
    overall_roi = ((net_profit) / total_spent) * 100 if total_spent > 0 else 0
    win_rate = (winning_draws / len(historical_draws_data)) * 100
    
    print(f"Jumlah Cabutan Diuji : {len(historical_draws_data)}")
    print(f"Jumlah Modal Pertaruhan: RM {total_spent:.2f}")
    print(f"Jumlah Pulangan Hadiah : RM {total_payout:.2f}")
    print(f"Untung/Rugi Bersih    : RM {net_profit:.2f}")
    print(f"Kadar Kemenangan      : {win_rate:.1f}% ({winning_draws}/{len(historical_draws_data)} cabutan)")
    print(f"Nisbah ROI            : {overall_roi:.2f}%")

# Mock data 30 cabutan untuk pengujian
sample_30_draws = [
    {'date': f'Draw-{i}', 'prizes': {'1st': f"{random.randint(0, 9999):04d}", '2nd': f"{random.randint(0, 9999):04d}", '3rd': f"{random.randint(0, 9999):04d}"}}
    for i in range(1, 31)
]

if __name__ == "__main__":
    run_backtest(sample_30_draws)
import itertools
from collections import Counter

# 1. PENAPISAN BAHARU (FILTERS)
def is_valid_sum(num_str, min_sum=12, max_sum=23):
    """Mengetatkan julat jumlah digit"""
    return min_sum <= sum(int(d) for d in num_str) <= max_sum

def has_triple_digit(num_str):
    """Membuang nombor dengan 3 digit serupa (Cth: 4555, 4445)"""
    counts = Counter(num_str)
    return any(count >= 3 for count in counts.values())

def count_digit_overlap(num1, num2):
    """Mengira persamaan digit antara dua nombor"""
    c1, c2 = Counter(num1), Counter(num2)
    return sum((c1 & c2).values())

def apply_diversity_penalty(ranked_candidates, top_n=10, max_overlap=2):
    """Memastikan Top 10 tidak dipenuhi nombor yang hampir serupa"""
    selected = []
    for num, score in ranked_candidates:
        if not selected:
            selected.append((num, score))
            continue
        
        # Semak jika nombor terlalu serupa dengan nombor yang dah dipilih
        too_similar = any(count_digit_overlap(num, s[0]) > max_overlap for s in selected)
        if not too_similar:
            selected.append((num, score))
            
        if len(selected) == top_n:
            break
            
    return selected

# 2. SIMULATOR STRATEGI PERTARUHAN
def calculate_hybrid_roi(top_10_list, actual_prizes):
    """
    actual_prizes = {'1st': '1234', '2nd': '5678', '3rd': '3545'}
    Strategy: Top 1-3 (RM1 Direct + RM1 iBox), Top 4-10 (RM1 iBox)
    """
    total_cost = (3 * 2) + (7 * 1)  # RM13.00
    payout = 0
    
    # Anggaran struktur hadiah Toto iBox (24-Permutation)
    ibox_payouts = {'1st': 100, '2nd': 40, '3rd': 20}
    direct_payouts = {'1st': 2500, '2nd': 1000, '3rd': 500}

    for rank, (num, _) in enumerate(top_10_list, 1):
        num_sorted = "".join(sorted(num))
        
        for prize_type, draw_num in actual_prizes.items():
            draw_sorted = "".join(sorted(draw_num))
            
            # Semak Direct Hit
            if rank <= 3 and num == draw_num:
                payout += direct_payouts[prize_type]
            
            # Semak iBox Hit
            if num_sorted == draw_sorted:
                payout += ibox_payouts[prize_type]

    roi = ((payout - total_cost) / total_cost) * 100
    return total_cost, payout, roi

# --- STRUKTUR UTAMA UTK DIHUBUNGKAN KE DATASET ---
if __name__ == "__main__":
    # Contoh simulasi calon nombor dan skor raw
    raw_candidates = [
        ("4544", 0.001), ("4554", 0.0009), ("4545", 0.0008), 
        ("3545", 0.0007), ("4546", 0.0006), ("0544", 0.0005),
        ("4555", 0.0004), ("1234", 0.0003), ("8765", 0.0002)
    ]
    
    # Guna penapis baharu
    filtered = [c for c in raw_candidates if is_valid_sum(c[0]) and not has_triple_digit(c[0])]
    top_10_diverse = apply_diversity_penalty(filtered, top_n=10)
    
    print("Top 10 Selepas Diversiti & Penapisan Ketat:")
    for rank, (num, score) in enumerate(top_10_diverse, 1):
        print(f"{rank}. {num} (Score: {score})")
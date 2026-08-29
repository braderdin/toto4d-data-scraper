def apply_diversity_penalty(ranked_candidates, top_n=10, max_overlap=3):
    selected = []
    for num, score in ranked_candidates:
        if not selected:
            selected.append((num, score))
            continue
        
        # Mengelakkan nombor yang 100% serupa sahaja (melonggarkan julat)
        too_similar = any(count_digit_overlap(num, s[0]) >= 4 for s in selected)
        if not too_similar:
            selected.append((num, score))
            
        if len(selected) == top_n:
            break
            
    return selected
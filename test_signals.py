import sys
from signals import (
    analyze_semantic_coherence,
    analyze_sentence_length_variance,
    analyze_lexical_diversity,
    combine_signals
)

# Target test cases provided by the user
test_cases = {
    "Clearly AI-Generated": (
        "Artificial intelligence represents a transformative paradigm shift in modern society. "
        "It is important to note that while the benefits of AI are numerous, it is equally "
        "essential to consider the ethical implications. Furthermore, stakeholders across "
        "various sectors must collaborate to ensure responsible deployment."
    ),
    "Clearly Human-Written": (
        "ok so i finally tried that new ramen place downtown and honestly? "
        "underwhelming. the broth was fine but they put WAY too much sodium in it and "
        "i was thirsty for like three hours after. my friend got the spicy version and "
        "said it was better. probably won't go back unless someone drags me there"
    ),
    "Borderline: Formal Human Writing": (
        "The relationship between monetary policy and asset price inflation has been "
        "extensively studied in the literature. Central banks face a fundamental tension "
        "between their mandate for price stability and the unintended consequences of "
        "prolonged low interest rates on equity and real estate valuations."
    ),
    "Borderline: Lightly Edited AI Output": (
        "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
        "flexibility and no commute on one side, isolation and blurred work-life boundaries "
        "on the other. Studies show productivity varies widely by individual and role type."
    )
}

def map_label(score: float) -> str:
    if score <= 0.35:
        return "likely_human (Verified Authentic)"
    elif score <= 0.70:
        return "uncertain (Stylistically Mixed)"
    else:
        return "likely_ai (Automated Patterns Detected)"

def run_tests():
    print("=" * 100)
    print(f"{'TEST CASE':<40} | {'S_llm':<6} | {'S_slv':<6} | {'S_ttr':<6} | {'Combined':<8} | {'Attribution'}")
    print("=" * 100)
    
    for label, text in test_cases.items():
        s_llm = analyze_semantic_coherence(text)
        s_slv = analyze_sentence_length_variance(text)
        s_ttr = analyze_lexical_diversity(text)
        combined = combine_signals(s_llm, s_slv, s_ttr)
        
        category = map_label(combined)
        
        print(f"{label:<40} | {s_llm:<6.2f} | {s_slv:<6.2f} | {s_ttr:<6.2f} | {combined:<8.2f} | {category}")
        
    print("=" * 100)

if __name__ == "__main__":
    run_tests()

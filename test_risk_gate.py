import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))

from agent.orchestrator import full_scan_with_orchestration

def test_aapl():
    print("Testing AAPL scan...")
    log = full_scan_with_orchestration(
        symbol="AAPL",
        start_date="2026-03-01",
        end_date="2026-06-01",
        top_n=5,
        portfolio=[],
        policy_mode="tight"
    )
    
    print(f"Final Picks: {len(log.final_picks)}")
    if log.rejections_risk:
        print("\n--- Risk Rejections ---")
        for idx, (cand, reason) in enumerate(log.rejections_risk[:5]):
            print(f"[{idx+1}] Reason: {reason}")
            
if __name__ == "__main__":
    test_aapl()

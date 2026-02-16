# 🛡️ Desk Command — User Walkthrough

## Your Trading Day With The System

### 🌅 Monday Morning — You Log In

You open the dashboard. First thing you see:

```
🛡️ Desk Command
Vol Regime: HIGH | SPY Trend: Uptrend | Macro Risk: FOMC in 3 days ⚠️ | Policy: Tight ($1,000)
```

**What you're thinking:**
- "Volatility is elevated. Good environment for credit spreads."
- "But FOMC in 3 days — stay away from short expirations."
- "My policy is tight ($1K max loss per trade) — no swinging for the fences."

→ *You immediately know: Be conservative. Short premium in 35+ DTE only.*

---

### 🔍 You Decide to Scan: "Find me NVDA setups"

You enter:
- **Symbol**: NVDA
- **Expirations**: 35-55 DTE (avoids FOMC surprise)
- **Portfolio**: Current positions: 2x QQQ short calls, 1x SMH bull call spread
- **Policy**: Tight

You hit: **"Run Full Desk Scan"**

---

### ⏳ System Does Its Thing (Behind The Scenes)

While you wait, the system:

1. **Checks blocking events**
   - ✓ No NVDA earnings in 35-55 DTE window
   - ✓ No macro blackout dates

2. **Detects vol regime**: HIGH
   - Suggests credit spreads (sell premium into high vol)

3. **Scans candidates**: 12 bull call spreads found
   - Strike combinations that fit your Greeks preferences

4. **Runs risk gate**: Rejected 3
   - "Sector concentration: Already 40% in Tech. This would push you to 45%"
   - "Portfolio drawdown protection: Max loss $1,500 exceeds your $1,000 limit"
   - "Sector: Already exposed to SMH + QQQ short calls"

5. **Runs gatekeeper**: Rejected 3 more
   - "Leg 1 bid/ask spread 2.1% — exceeds 1.5% threshold (too wide)"
   - "Open interest 450 contracts on short strike — below 1,000 minimum"

6. **Runs correlation**: Rejected 2 more
   - "Correlation 0.78 with QQQ — exceeds 0.70 threshold"
   - "Correlation 0.72 with SMH — exceeds 0.70 threshold"

7. **Ranks remaining**: 4 candidates → shows top 3

---

### 📊 Results Come Back — You See The Funnel

```
Generated:      ████████████  12
Risk Gate:      █████████     9   ← Lost 3 to concentration
Gatekeeper:     ██████        6   ← Lost 3 to spreads/OI
Correlation:    ████          4   ← Lost 2 to overlap
Final Picks:    ███           3   ← Top candidates
```

**What this tells you:**
- "The system filtered hard. Only 25% survived. That's quality."
- "I trust these 3 picks."

---

### 📈 You See Your Final Picks

| Rank | Strategy | Exp | Cost | Max Loss | Max Profit | Score |
|------|----------|-----|------|----------|-----------|-------|
| 1 | Bull Call Debit | Mar 20 | $1.20 | $120 | $380 | **84** |
| 2 | Bull Call Debit | Mar 20 | $1.00 | $100 | $250 | **79** |
| 3 | Bull Call Debit | Mar 20 | $0.85 | $85 | $180 | **73** |

**You're scanning the table:**
- ✓ All under my $1,000 max loss
- ✓ Ranked by gatekeeper score (84 > 79 > 73)
- ✓ All expire after FOMC
- ✓ Risk/reward looks reasonable (3x-4x potential)

**You click Rank #1 to drill down:**

---

### 🔬 Detailed Trade View (Drill-Down Modal)

```
TRADE: Bull Call Debit Spread

Trade Overview            Leg Details              Gatekeeper Assessment
──────────────            ───────────              ─────────────────────
Expiration: Mar 20        LONG CALL 420            ✓ PASSED
Cost: $1.20               Delta: 0.65
Max Loss: $120            IV: 22%
Max Profit: $380          Bid/Ask: 2.50/2.65
Breakeven: $425.20        OI: 12,400
DTE: 35 days              
                          SHORT CALL 425           Warnings: None
                          Delta: 0.45
                          IV: 21%
                          Bid/Ask: 1.30/1.45
                          OI: 8,900
```

**You're checking:**
- ✓ 35 DTE — perfect for high vol capture
- ✓ Long call delta 0.65 — good directional exposure
- ✓ Short call delta 0.45 — realistic probability of profit
- ✓ Spreads tight (2.5-3%): 2.50/2.65 on long, 1.30/1.45 on short
- ✓ Open interest solid (12k+ contracts)
- ✓ No gatekeeper warnings

**You think:** *"This is clean. Low friction. Can execute at mid-market easy."*

---

### ❓ But Wait — You Want to Know: Why Were The Others Rejected?

You click: **"❌ Rejections"** tab

```
❌ RISK REJECTIONS
· Max loss $1,500 exceeds limit $1,000
· Sector Technology cap (40%) + this trade = 45% > 40% limit
· Concentration: Already 3x NVDA exposure via QQQ short calls

❌ GATEKEEPER REJECTIONS  
· Leg 1 bid/ask spread 2.1% exceeds 1.5% threshold
· Market impact 3.2% exceeds 2% threshold
· Open interest 450 contracts below 1,000 minimum on short strike

❌ CORRELATION REJECTIONS
· Correlation 0.78 with QQQ exceeds 0.70 threshold
· Correlation 0.72 with SMH exceeds 0.70 threshold
```

**You're learning:**
- "OK, the system rejected those because they'd blow my portfolio limits."
- "The gatekeeper ones were too illiquid to trade efficiently."
- "The correlated ones would create hidden risk I didn't see."

**You think:** *"This isn't a black box. I understand the rules. I agree with the rules."*

---

### 📋 You Check The Decision Log

You click: **"📋 Decision Log"**

```
SCAN COMPLETED: 2026-02-16 09:47:32 AM

Market Regime:      HIGH
Strategy Hint:      BULL_CALL_DEBIT
Blocking Events:    None
Portfolio Context:  Tech 40%, All sectors balanced

GATE PROGRESSION:
  Generated       12 candidates
  Risk Gate       9 survived (3 rejected: concentration/limits)
  Gatekeeper      6 survived (3 rejected: spreads/OI)
  Correlation     4 survived (2 rejected: overlap)
  Final Picks     3 top-ranked

Timestamp: 2026-02-16T09:47:32Z
```

**You're thinking:**
- "Perfect audit trail for my paper trading journal."
- "If this trade goes against me, I can review exactly why the system chose it."
- "If I backtest this, I can compare: did my thresholds work?"

---

### ✅ You Execute Trade #1

You decide: **"I'm taking Rank #1."**

You think:
- Max loss $120 — I can afford that
- Max profit $380 — 3:1 reward/risk, not greedy
- Score 84/100 — highest confidence pick
- No warnings from gatekeeper
- Good liquidity (OI 8,900+)

You:
1. Open your broker
2. Enter the spread: Long 420 Call / Short 425 Call
3. Execute at $1.20 debit (mid-market)
4. Submit order

**✓ Trade filled.**

---

### 📊 Later That Week — You Check Positions

You open the dashboard. Now you see a new tab: **"💼 Live Positions"**

```
Symbol  Strategy             Entry   Current P/L   Expected Move   DTE   Status
──────  ────────────────     ─────   ────────────  ──────────────  ───   ──────
NVDA    Bull Call Debit      $1.20   +$0.35 (+29%) $2.10           31    ✓ Active
QQQ     Short Call (x2)      $1.50   -$0.12 (-8%)  $1.80           28    ⚠️ DTE<30
SMH     Bull Call Debit      $0.85   +$0.18 (+21%) $1.50           45    ✓ Active
```

**What the system tells you:**
- Your NVDA trade is up 29% already (nice!)
- Your QQQ short calls are getting close to expiration (28 DTE) — **⚠️ Warning**
- SMH spread still has time (45 DTE)

You click the QQQ warning and the system suggests:
- "DTE < 30: Consider closing position or rolling to 45+ DTE"
- "Current P/L -8%: If you roll, you'll lock in loss. Or hold for decay."

---

### 🎯 Day 5 — NVDA Hits Max Profit

NVDA rallies past $425. Your spread is now worth $0.00 (max loss on long leg).

**You're thinking:** Should I close?

The system shows:
- **Expected Move**: Moved from $2.10 to $1.40 (volatility collapsing)
- **Current P/L**: +$0.80 (+67% return on $1.20 cost)
- **DTE**: 30 days left
- **Suggestion**: "Scale out 50%? Theta decay in your favor for remaining time."

You decide: **Close half. Let half ride.**

✓ Close 50 contracts at $0.80 credit → Lock in +$0.40 profit per contract
✓ Keep 50 contracts running

---

### 📊 End of Month — You Review Performance

You want to check: **Did this system work?**

You pull the decision log for all trades taken:
- NVDA Bull Call Debit: +67% (closed half)
- QQQ Short Call: -8% (rolled to April)
- SMH Bull Call Debit: +21% (still running)

**You're analyzing:**
- All 3 picks had gatekeeper score > 78
- All 3 avoided correlation overlaps
- All 3 survived risk gates
- **Net performance**: +27% average return

You think:
- "The system rejected 9 trades that would have blown my risk limits."
- "The funnel visualization meant I only spent time on quality setups."
- "The rejections tab meant I understood the rules — no surprise failures."
- "The decision log let me audit the logic — I trust the system."

---

### 🔄 Next Month — You Run Another Scan

Vol has dropped to MEDIUM.

The system now suggests: **IRON CONDOR** (different strategy for lower vol)

You scan and get:
- 18 candidates generated
- 14 pass risk gate
- 9 pass gatekeeper
- 6 pass correlation
- 3 final picks ranked by score

**Same funnel. Same transparency. Different opportunity.**

---

## Your Workflow

```
MORNING
  ↓
Check Market Context Bar
  ↓ "What regime am I in?"
Run Scan for Symbol + Dates + Portfolio
  ↓ "What are my best options?"
Review Gate Funnel
  ↓ "How many survived filtering?"
Look at Final Picks Table
  ↓ "Which rank should I take?"
Drill Into Top Pick
  ↓ "Legs, Greeks, spreads look good?"
Check Rejections Tab
  ↓ "Why was the other one rejected?"
View Decision Log
  ↓ "What was the system thinking?"
EXECUTE
  ↓
Monitor Live Positions
  ↓ "How's my P/L? Any warnings?"
Scale Out / Roll / Close
  ↓
REVIEW
  ↓
Check performance vs. decision log
  ↓ "Did my system rules work?"
Adjust thresholds for next month
```

---

## What You're NOT Doing

❌ Scrolling through 100 contracts wondering which one to pick  
❌ Second-guessing why a trade was rejected  
❌ Stacking correlated bets by accident  
❌ Blowing risk limits on oversized trades  
❌ Wondering "what's the regime again?"  
❌ Executing retail scanner picks with no risk control  

---

## What You ARE Doing

✅ Seeing your market context in 2 seconds  
✅ Getting 3 vetted, ranked picks instead of 100 choices  
✅ Understanding exactly why 9 were rejected  
✅ Executing high-confidence trades with clear risk limits  
✅ Tracking P/L + warnings on live positions  
✅ Auditing your decision logic in the decision log  
✅ **Trading like a structured desk, not a retail gambler**  

---

**This is your day with Desk Command.** 🛡️

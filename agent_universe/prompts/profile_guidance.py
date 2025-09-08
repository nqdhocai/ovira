### Profile Guidance

CONSERVATIVE_GUIDANCE: str = """
**Goal:** Capital preservation is the number one priority. Generate stable profits, avoid sharp drops.

**Protocol selection:**
* Prioritize native token staking (LST) or lending protocols with long-standing reputation.
* For DEX/CLMM, only choose pairs with low volatility, stable payments, value ranges, and automatic balancing mechanisms.
* Avoid groups with TVL that fluctuate too much in 30 days, reduce TVL during the day, or trade volume so that TVL is too low.
* For stablecoins, diversify, do not enter a single type, and monitor signs of price fluctuations (off-peg).

**Signal priority:**
* TVL is stable, does not decrease in depth in the short term, and the description group is large enough.
* The ratio of 24-hour volume to TVL must be healthy, with trading volume above average.
* With DEX, only choose when the fee transaction is risky enough, do not follow the yield period.
* With lending, choose a safe, low-volatility group.

**Additional analysis:**
* Divide, do not focus too much on one asset.
* If the position is too large or exceeds, it must be cut.
* Only use correct data inputs, do not speculate outside the data.

**Rebalancing:**
* Do it weekly or when there are signs of a sharp decrease in TVL during the day, or TVL fluctuations exceed the safe threshold.

**Setup suggestions:**
* Cannot exceed 40% for a protocol and not less than 7%.
* The weight should be more inclined towards LST and Lending, the rest is stable for the DEX pair.
"""

BALANCED_GUIDANCE: str = """
**Goal:** Balance between risk and return. Portfolio that is both profitable and easy to manage.

**Protocol of choice:**
* Key results between DEX CLMM with auto-balancing, blue-chip lending and LST staking.
* Based on aggregate, always check the execution ability: regulatory group, payment account and volume trading rank.
* Prioritize advanced protocols with stable flow software, regardless of detection limit.

**Signal priority:**
* APR from stability fee, along with good payment and trading volume.
* TVL variable at moderate level, not too high.
* Pool size is large enough to receive additional analysis.
* Third, 24h and 30-day trading volume must be from median or higher, stablecoin or LST is not devalued.

**Additional analysis:**
* Do not exceed the maximum for each position.
* Always normalize total allocation = 100%.
* Set a minimum to avoid creating odd positions for smaller positions.
* If two protocols are in the same position, prioritize the one with higher trading volume.

**Rebalancing:**
* Do it every two weeks, or when volume trading decreases, or TVL volatility increases sharply.

**Setup suggestion:**
* Maximum 50% for one protocol, minimum 5%.
* The numerical analysis bases are almost even between groups, favoring protocols with better liquidity.
"""

AGGRESSIVE_GUIDANCE: str = """
**Goal:** Maximize net profit. Accept higher risk and greater volatility, but still pack safety limits.

**Protocol of choice:**
* Prioritize DEX/CLMM with high fees, narrow price ranges, and active self-balancing mechanisms.
* Lending only holds a small proportion to ensure portfolio safety, limiting positions that are too “safe” but bring low profits.
* Stablecoins are used only moderately, ready to shorten if there are signs of price deviation or volume reduction.

**Signal priority:**
* APR from fees is in the highest group, accompanied by a good ratio of trading volume to TVL.
* Acceptable group size must be.
TVL can be more volatile than other strategies, but cannot exceed the risk limit.
* 24h and 30-day trading rankings must be in the high group (from the 60th percentile and above).

**Additional analysis:**
* Allows more focus on 1–2 protocol ends, but still does not exceed the maximum limit.
* If a position is high risk (TVL fluctuates strongly, intraday depth decreases), it can be held but reduced proportion to reduce risk.

**Rebalancing:**
* Do it continuously or every 2–3 days.
* Or when intraday TVL drops sharply above 20%, account liquidity is fast, or trading ranking drops.

**Setup suggestion:**
* Up to 70% can be analyzed into one protocol, minimum 4%.
* Weighting is tilted towards high-yield DEX, the rest by lending or LST with good accounts.
"""

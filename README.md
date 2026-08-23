# 🏰 Age of Enteland — Hackathon Solutions

> **Entelect Hackathon** · Age of Enteland · Python 3  
> Optimal economic strategy engine for all 4 levels of the competition.

---

## 🗺️ What is Age of Enteland?

You are the Mayor of a region. Towns are falling on quiet times. Your job is to write a program that generates the **optimal sequence of actions** a character takes during a timed simulation run.

The world is a **weighted graph** — towns and resource nodes connected by routes. Every action costs **ticks** (time). You have a fixed tick budget per level. Spend wisely.

```
Travel → Gather → Buy → Craft → Sell → Build
```

The currency is **Enteloot** 💰. But hoarding it scores less than investing it into infrastructure.

---

## ⚙️ Core Mechanics

### 🕐 The Tick Clock
Every action consumes ticks. The run ends at `total_ticks`. Actions that would exceed the limit are skipped — and still cost 1 tick as a penalty.

| Action | Cost |
|--------|------|
| Travel | Edge weight (ticks) |
| Buy / Sell | 1 tick |
| Craft | 2 ticks/item (1 at affinity town) |
| Gather | 2 ticks (3 at mines) |
| Build | 3–5 ticks depending on upgrade |

### 🏘️ Passive Trickle
Towns generate **Enteloot and resources automatically** on a cycle, regardless of where you are. Formula:
```
accumulated = floor(current_tick / rate) × amount
```
Building upgrades early means more passive income for the rest of the run.

### 🔨 Crafting Affinity
Some towns have **crafting affinity** — craft time drops from 2 ticks/item to **1 tick/item**. Always craft at affinity towns.

### 🏗️ Upgrades
| Type | Effect | Prereq |
|------|--------|--------|
| Production (6 types) | Doubles resource trickle | None |
| Rec-center | +20% Enteloot amount | 1 production upgrade |
| Fire-station | Boost duration +50% | 2 production upgrades |
| School | +50% Enteloot amount | Rec-center |
| Library | +50% Enteloot amount | School |
| Police-station *(L3+)* | Rate −2 ticks | Fire-station |

> 📌 **Spread upgrades across all towns** — the scoring multiplier rewards distribution.

---

## 📊 Level Overview

| Level | Ticks | Towns | Nodes | Key Feature | Score |
|-------|-------|-------|-------|-------------|-------|
| 1 | 1,000 | 5 | 7 | Gather & sell raw resources | 6,892,600 |
| 2 | 5,000 | 10 | 14 | Crafting + Building introduced | 12,177,735 |
| 3 | 50,000 | 15 | 21 | Fast routes + Mines + Tools | **14,182,504** |
| 4 | 100,000 | 30 | 28 | Upkeep boosts | — |

---

## 🧠 Strategy per Level

### 🟢 Level 1 — Gather & Sell
No crafting. No building. Pure resource arbitrage.

**Strategy:** Travel to N1 (sheep, yield=8, best raw value at 5 Enteloot/unit = **20 Enteloot/tick**). Gather 489 times. Sell all at Piltover.

```
Demacia → N3 → N6 → N1 [gather × 489] → N2 → Piltover [sell]
```

---

### 🟡 Level 2 — Craft & Build
Crafting and building are unlocked. Wood only exists at node N11 — **no town sells it**.

**Strategy:**
1. 🐟 **Capital phase** — buy fish + wheat both at Ixtal (produces both, pays 49/fish-n-chips). Craft at Demacia (affinity). Net profit: **33 Enteloot/item**.
2. 🪵 **Wood phase** — travel to N11, gather 110× (660 wood).
3. 🛒 **Buy phase** — sheep + clay at Noxus, stone at Shurima. Wheat comes from passive trickle.
4. ⚒️ **Craft phase** — all 9 component types at Demacia.
5. 🏗️ **Build phase** — all 10 towns × 10 upgrades. One mid-build top-up trade bridges the Enteloot gap.

```
Capital loop (7t overhead):
  Ixtal [buy fish+wheat] → Demacia [craft] → Ixtal [sell @ 49]
```

---

### 🔴 Level 3 — Fast Routes + Tools
Fast routes, mine nodes, ore, iron-fittings, boots and pickaxe are unlocked.

**Strategy:**
1. 🐟 **Capital** — 6 exponential fish-n-chips batches (50→5000). Sell at Demacia (48/item).
2. ⛏️ **Ore** — 13 gathers at N9 mine (yield=6) = 78 ore.
3. 🛒 **Buy resources** — wood at Piltover, wheat at Shurima, sheep at Targon, clay at Ixtal, stone at Zaun.
4. ⚒️ **Craft** — all components + boots + pickaxe at Demacia.
5. 🥾 **Boots activated** — all subsequent travel costs −1 tick/edge.
6. 🏗️ **Build** — all 15 towns × 11 upgrades (includes police-station).
7. 🐟 **Fill** — dynamic final trading batches to consume remaining ticks exactly.

**Fast route usage:** N9↔Borealis fast route (1 tick + 30 Enteloot toll vs 3 ticks standard) used 34 times throughout.

```
Score improvement vs baseline: 3,913,300 → 14,182,504 (+262%)
```

---

## 🗂️ File Structure

```
├── solution.py          # Level 3 (main submission)
├── solution_level1.py   # Level 1
├── solution_level2.py   # Level 2
├── 1.txt                # Level 1 map data
├── 2.txt                # Level 2 map data
├── 3.txt                # Level 3 map data
├── 4.txt                # Level 4 map data
├── resources.json       # Global constants (recipes, upgrades, tools)
├── specification.md     # Full game specification
├── output.txt           # Level 3 action output (submitted)
├── output_level2.txt    # Level 2 action output (submitted)
├── output_level1.txt    # Level 1 action output (submitted)
├── code.zip             # Level 3 submission zip
├── code_level2.zip      # Level 2 submission zip
└── submission_log_level_*.txt  # Engine feedback logs
```

---

## 🚀 Running the Solutions

```bash
# Level 1
python3 solution_level1.py > output_level1.txt

# Level 2
python3 solution_level2.py > output_level2.txt

# Level 3
python3 solution.py > output.txt
```

Requirements: **Python 3.9+**, no external dependencies.

---

## 🔑 Key Technical Decisions

**Dijkstra for all routing** — both pre-boots and post-boots graphs are pre-computed. After crafting boots, the post-boots graph (all edges −1 tick, min 1) is automatically used.

**Dynamic final batch** — instead of hardcoding quantities, remaining ticks are computed after all mandatory actions and the final trading batch fills exactly to `total_ticks`.

**Exponential capital ramp** — trading batches grow geometrically (e.g. 50→150→450→1350→4000→5000) to compound Enteloot quickly while amortizing travel overhead.

**Component math** — all construction requirements are derived from first principles, including the full dependency chain (nets need fencing, fencing needs rope, rope needs sheep, etc.).

---

## 📜 License

MIT — do whatever you want with it.

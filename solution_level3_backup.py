#!/usr/bin/env python3
"""Optimised Level 3 strategy — fast routes, better routing, dynamic final batch."""

import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVEL = json.loads((ROOT / "3.txt").read_text())
TOTAL_TICKS = LEVEL["run"]["total_ticks"]
TOWNS = list(LEVEL["towns"].keys())

# ── Build cost constants ──────────────────────────────────────────────────────
# civic chain build times per town
CIVIC_BUILD_TICKS  = 3 + 3 + 4 + 4 + 5 + 5 + 5   # farmhouse+fertilised+rec+fire+school+library+police
PROD_BUILD_TICKS   = 3 + 3 + 3 + 3                  # pier+quarry+woodlands+pottery-house
TOTAL_BUILD_PER_TOWN = CIVIC_BUILD_TICKS + PROD_BUILD_TICKS  # 41


def build_graph(boots=False):
    """Adjacency list: node -> [(neighbour, weight, toll)]
    Includes BOTH standard and fast edges so Dijkstra can choose the cheapest."""
    g = {}
    for edge in LEVEL["routes"]:
        a, b = edge["between"]
        w = max(1, edge["weight"] - (1 if boots else 0))
        t = edge["toll"]
        g.setdefault(a, []).append((b, w, t))
        g.setdefault(b, []).append((a, w, t))
    return g


def dijkstra(graph, src, dst):
    """Return (ticks, path) where path is list of action-dicts."""
    ctr = 0
    q = [(0, ctr, src, [])]
    seen = set()
    while q:
        cost, _, cur, path = heapq.heappop(q)
        if cur in seen:
            continue
        seen.add(cur)
        if cur == dst:
            return cost, path
        for nb, w, toll in graph.get(cur, []):
            if nb not in seen:
                ctr += 1
                step = {"destination": nb}
                if toll > 0:
                    step["fast"] = True
                heapq.heappush(q, (cost + w, ctr, nb, path + [step]))
    raise RuntimeError(f"No path {src} -> {dst}")


# Pre-compute graphs (fast routes included in both — Dijkstra picks lowest weight)
G_PRE  = build_graph(boots=False)
G_POST = build_graph(boots=True)


def main() -> None:
    actions = []
    location = [LEVEL["run"]["starting_town"]]
    tick = [0]
    boots_crafted = [False]

    def G():
        return G_POST if boots_crafted[0] else G_PRE

    def add(kind, **fields):
        actions.append({"type": kind, **fields})

    def travel_to(dst):
        if location[0] == dst:
            return
        cost, path = dijkstra(G(), location[0], dst)
        tick[0] += cost
        for step in path:
            actions.append({"type": "travel", **step})
        location[0] = dst

    def buy(item, qty, town):
        travel_to(town)
        tick[0] += 1
        add("buy", item=item, quantity=qty)

    def craft(item, qty):
        tick[0] += qty   # crafting affinity at Demacia = 1 tick/item
        add("craft", item=item, quantity=qty)

    def sell_item(item, qty):
        tick[0] += 1
        add("sell", item=item, quantity=qty)

    # ── Phase 1: Capital via fish-n-chips ─────────────────────────────────────
    for qty in (50, 150, 450, 1350, 4000, 5000):
        buy("fish", qty * 2, "Demacia")
        buy("wheat", qty, "Shurima")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # ── Phase 2: Gather ore at N9 (13 × yield-6 = 78 ore) ────────────────────
    travel_to("N9")
    for _ in range(13):
        tick[0] += 3   # mine gather-time, no pickaxe yet
        add("gather")

    # ── Phase 3: Buy construction materials ───────────────────────────────────
    # Material requirements (all 15 towns × 11 upgrades + 2 tools):
    #   planks     347  (345 upgrades + 2 pickaxe)
    #   thatch      60
    #   rope       197  (75 direct + 90 for fencing + 30 for nets + 2 boots)
    #   fencing     90  (60 direct + 30 for nets)
    #   mortar     435
    #   bricks     435
    #   stone-blocks 150
    #   kiln-glass  60
    #   nets        30
    #   iron-fittings 34  (30 police-stations + 2 boots + 2 pickaxe)
    #   -- input resources --
    #   wood  1028  (planks×694 + kiln-glass×120 + fencing×180 + iron-fittings×34)
    #   wheat  120  (thatch×60×2)
    #   sheep  394  (rope×197×2)
    #   clay  1425  (bricks×870 + mortar×435 + kiln-glass×120)
    #   stone  885  (mortar×435 + stone-blocks×450)
    #   ore     76  (iron-fittings×34×2 + boots×4 [already gathered 78])
    travel_to("Demacia")
    buy("wood",  1028, "Piltover")
    buy("wheat",  120, "Shurima")
    buy("sheep",  394, "Targon")
    buy("clay",  1425, "Ixtal")
    buy("stone",  885, "Zaun")
    travel_to("Demacia")

    # ── Phase 4: Craft all components and tools at Demacia ────────────────────
    for item, qty in [
        ("planks",        347),
        ("thatch",         60),
        ("mortar",        435),
        ("bricks",        435),
        ("stone-blocks",  150),
        ("kiln-glass",     60),
        ("rope",          197),
        ("fencing",        90),
        ("nets",           30),
        ("iron-fittings",  34),
        ("boots",           1),
        ("pickaxe",         1),
    ]:
        craft(item, qty)

    boots_crafted[0] = True

    # ── Phase 5: Build all upgrades in every town ─────────────────────────────
    for town in TOWNS:
        travel_to(town)
        for upgrade in ("farmhouse", "fertilised-fields", "rec-center",
                        "fire-station", "school", "library", "police-station",
                        "pier", "quarry", "woodlands", "pottery-house"):
            tick[0] += {"farmhouse": 3, "fertilised-fields": 3, "rec-center": 4,
                        "fire-station": 4, "school": 5, "library": 5,
                        "police-station": 5, "pier": 3, "quarry": 3,
                        "woodlands": 3, "pottery-house": 3}[upgrade]
            add("build", upgrade=upgrade)

    # ── Phase 6: Fill remaining ticks with fish-n-chips trading ───────────────
    # Each loop: travel Demacia↔Shurima (round-trip = 22 ticks post-boots via fast route)
    # + 1 buy fish + 1 buy wheat + qty craft + 1 sell = 25 + qty ticks overhead
    travel_to("Demacia")

    c_dem_shu, _ = dijkstra(G_POST, "Demacia", "Shurima")
    c_shu_dem, _ = dijkstra(G_POST, "Shurima", "Demacia")
    loop_overhead = 1 + c_dem_shu + 1 + c_shu_dem + 1  # buy_fish + travel + buy_wheat + travel_back + sell

    used_ticks = tick[0]
    remaining = TOTAL_TICKS - used_ticks

    # Use fixed large batches then compute exact final batch
    batches = [6000, 15000]
    for qty in batches:
        cost = loop_overhead + qty
        if remaining - cost < loop_overhead + 1:
            break
        remaining -= cost
        buy("fish", qty * 2, "Demacia")
        buy("wheat", qty, "Shurima")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # Final batch — fill exactly
    final_qty = remaining - loop_overhead
    if final_qty > 0:
        buy("fish", final_qty * 2, "Demacia")
        buy("wheat", final_qty, "Shurima")
        travel_to("Demacia")
        craft("fish-n-chips", final_qty)
        sell_item("fish-n-chips", final_qty)

    import sys
    print(f"[INFO] total tracked ticks: {tick[0]}", file=sys.stderr)
    print(json.dumps({"actions": actions}, indent=2))


if __name__ == "__main__":
    main()

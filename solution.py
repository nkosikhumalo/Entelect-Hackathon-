#!/usr/bin/env python3
"""Optimised Level 3 strategy — fast routes, better routing, dynamic final batch."""

import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVEL = json.loads((ROOT / "3.txt").read_text())
TOTAL_TICKS = LEVEL["run"]["total_ticks"]
TOWNS = list(LEVEL["towns"].keys())

CIVIC_BUILD_TICKS = 3 + 3 + 4 + 4 + 5 + 5 + 5
PROD_BUILD_TICKS  = 3 + 3 + 3 + 3


def build_graph(boots=False):
    """Adjacency list including both standard and fast edges."""
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
        tick[0] += qty  # crafting affinity at Demacia = 1 tick/item
        add("craft", item=item, quantity=qty)

    def sell_item(item, qty):
        tick[0] += 1
        add("sell", item=item, quantity=qty)

    # ── Phase 1: Capital via fish-n-chips ─────────────────────────────────────
    # Demacia buys fish (produces fish), Shurima sells wheat.
    # Craft fish-n-chips at Demacia (affinity = 1 tick), sell at 48 each.
    for qty in (50, 150, 450, 1350, 4000, 5000):
        buy("fish", qty * 2, "Demacia")
        buy("wheat", qty, "Shurima")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # ── Phase 2: Gather ore at N9 (mine, yield=6, 3t each) ───────────────────
    # Need 68 ore for iron-fittings (34×2) + 4 for tools (2+2) = 76 total
    # 13 gathers × 6 = 78 ore (2 spare)
    travel_to("N9")
    for _ in range(13):
        tick[0] += 3
        add("gather")

    # ── Phase 3: Buy construction materials ───────────────────────────────────
    # All 15 towns × 11 upgrades + 2 tools:
    #   wood:  1028  |  wheat: 120  |  sheep: 394
    #   clay:  1425  |  stone: 885
    travel_to("Demacia")
    buy("wood",  1028, "Piltover")
    buy("wheat",  120, "Shurima")
    buy("sheep",  394, "Targon")
    buy("clay",  1425, "Ixtal")
    buy("stone",  885, "Zaun")
    travel_to("Demacia")

    # ── Phase 4: Craft all components and tools at Demacia (affinity) ─────────
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
    BUILD_TIMES = {
        "farmhouse": 3, "fertilised-fields": 3, "rec-center": 4,
        "fire-station": 4, "school": 5, "library": 5, "police-station": 5,
        "pier": 3, "quarry": 3, "woodlands": 3, "pottery-house": 3,
    }
    for town in TOWNS:
        travel_to(town)
        for upgrade in ("farmhouse", "fertilised-fields", "rec-center",
                        "fire-station", "school", "library", "police-station",
                        "pier", "quarry", "woodlands", "pottery-house"):
            tick[0] += BUILD_TIMES[upgrade]
            add("build", upgrade=upgrade)

    # ── Phase 6: Fill remaining ticks with fish-n-chips trading ───────────────
    travel_to("Demacia")
    c_dem_shu, _ = dijkstra(G_POST, "Demacia", "Shurima")
    c_shu_dem, _ = dijkstra(G_POST, "Shurima", "Demacia")
    # overhead per loop: buy_fish(1) + travel_to_shurima + buy_wheat(1) + travel_back + sell(1)
    loop_overhead = 1 + c_dem_shu + 1 + c_shu_dem + 1

    remaining = TOTAL_TICKS - tick[0]

    for qty in (6000, 15000):
        cost = loop_overhead + qty
        if remaining - cost < loop_overhead + 1:
            break
        remaining -= cost
        buy("fish", qty * 2, "Demacia")
        buy("wheat", qty, "Shurima")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # Final batch fills exactly to tick limit
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

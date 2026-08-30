#!/usr/bin/env python3
"""Level 2 — fish-n-chips capital, gather wood at N11, build all 10 towns."""

import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVEL = json.loads((ROOT / "2.txt").read_text())
TOTAL_TICKS = LEVEL["run"]["total_ticks"]   # 5000
TOWNS = list(LEVEL["towns"].keys())

BUILD_TIMES = {
    "farmhouse": 3, "fertilised-fields": 3, "pier": 3, "quarry": 3,
    "woodlands": 3, "pottery-house": 3,
    "rec-center": 4, "fire-station": 4, "school": 5, "library": 5,
}
ENTELOOT_COSTS = {
    "farmhouse": 500, "fertilised-fields": 500, "pier": 600, "quarry": 600,
    "woodlands": 500, "pottery-house": 700,
    "rec-center": 1200, "fire-station": 1800, "school": 2000, "library": 2500,
}
UPGRADES = list(BUILD_TIMES.keys())


def build_graph():
    g = {}
    for edge in LEVEL["routes"]:
        a, b = edge["between"]
        g.setdefault(a, []).append((b, edge["weight"]))
        g.setdefault(b, []).append((a, edge["weight"]))
    return g


def dijkstra(graph, src, dst):
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
        for nb, w in graph.get(cur, []):
            if nb not in seen:
                ctr += 1
                heapq.heappush(q, (cost + w, ctr, nb, path + [nb]))
    raise RuntimeError(f"No path {src} -> {dst}")


def main():
    G = build_graph()
    actions = []
    tick = [0]
    loc = [LEVEL["run"]["starting_town"]]  # Demacia

    def travel_to(dst):
        if loc[0] == dst:
            return
        cost, path = dijkstra(G, loc[0], dst)
        tick[0] += cost
        for step in path:
            actions.append({"type": "travel", "destination": step})
        loc[0] = dst

    def buy(item, qty, town):
        travel_to(town)
        tick[0] += 1
        actions.append({"type": "buy", "item": item, "quantity": qty})

    def craft(item, qty):
        tick[0] += qty  # Demacia crafting affinity = 1 tick/item
        actions.append({"type": "craft", "item": item, "quantity": qty})

    def sell_item(item, qty):
        tick[0] += 1
        actions.append({"type": "sell", "item": item, "quantity": qty})

    def trade_loop(qty):
        """Buy fish+wheat at Ixtal (produces both), craft at Demacia, sell at Ixtal.
        Overhead: 2 buys + Ixtal→Demacia(2t) + Demacia→Ixtal(2t) + 1 sell = 7 ticks."""
        travel_to("Ixtal")
        tick[0] += 1; actions.append({"type": "buy", "item": "fish",  "quantity": qty * 2})
        tick[0] += 1; actions.append({"type": "buy", "item": "wheat", "quantity": qty})
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        travel_to("Ixtal")
        sell_item("fish-n-chips", qty)

    # ── Phase 1: Capital ──────────────────────────────────────────────────────
    # Ixtal produces fish+wheat and pays 49/fish-n-chips. Net profit: 33/item.
    for qty in (30, 93, 284, 870):
        trade_loop(qty)

    # ── Phase 2: Gather wood at N11 ───────────────────────────────────────────
    # N11 is the only wood source in L2 (yield=6, 2t each).
    # 110 gathers × 6 = 660 wood needed for all 10 towns.
    travel_to("N11")
    for _ in range(110):
        tick[0] += 2
        actions.append({"type": "gather"})

    # ── Phase 3: Buy clay+sheep at Noxus, stone at Shurima ───────────────────
    # Wheat (80 needed for thatch) covered by passive trickle — skip buying.
    # Route: N11→Noxus(5t)→Shurima(17t)→Demacia(1t)
    buy("sheep",  260, "Noxus")
    buy("clay",   770, "Noxus")
    buy("stone",  410, "Shurima")
    travel_to("Demacia")

    # ── Phase 4: Craft and build the first four towns early ──────────────────
    # Early civic construction earns passive Enteloot for most of the run.
    components_per_town = [
        ("planks",       230),
        ("thatch",        40),
        ("mortar",       230),
        ("bricks",       230),
        ("stone-blocks",  60),
        ("kiln-glass",    40),
        ("rope",         130),
        ("fencing",       60),
        ("nets",          20),
    ]

    # ── Phase 5: Build all 10 towns with one mid-build top-up ─────────────────
    # Build the first batch early so its civic bonuses accrue longer.
    tour = ["Ixtal", "Noxus", "Bilgewater", "Freljord", "Shurima",
            "Demacia", "Piltover", "Ionia", "Zaun", "Targon"]

    # Components for four towns, crafted at Demacia.
    for item, total_qty in components_per_town:
        craft(item, total_qty * 4 // 10)

    # Build first 4 towns.
    for town in tour[:4]:
        travel_to(town)
        for upgrade in UPGRADES:
            tick[0] += BUILD_TIMES[upgrade]
            actions.append({"type": "build", "upgrade": upgrade})

    # After mid-trade we end at Ixtal, also a crafting-affinity town.
    travel_remaining = dijkstra(G, "Ixtal", tour[4])[0] + sum(
        dijkstra(G, tour[i], tour[i + 1])[0] for i in range(4, 9)
    )
    build_remaining = sum(BUILD_TIMES.values()) * 6
    component_remaining = sum(total_qty * 6 // 10 for _, total_qty in components_per_town)
    loc_to_ixtal = dijkstra(G, loc[0], "Ixtal")[0]
    loops = 4
    loop_overhead = 7  # two buys, Ixtal→Demacia→Ixtal, and one sell
    mid_qty = (TOTAL_TICKS - tick[0] - loc_to_ixtal
               - loops * loop_overhead - component_remaining
               - travel_remaining - build_remaining)

    # The early construction spend leaves enough cash for only 119 meals.
    # Reinvest each sale into three further batches; their overhead is already
    # included in the exact tick budget above.
    mid_batches = (80, 250, 760, mid_qty - 80 - 250 - 760)
    for qty in mid_batches:
        if qty > 0:
            trade_loop(qty)

    # Craft the remaining batches at Ixtal, retaining the affinity and avoiding
    # an unnecessary return trip to Demacia.
    for item, total_qty in components_per_town:
        craft(item, total_qty * 6 // 10)

    # Build remaining 6 towns
    for town in tour[4:]:
        travel_to(town)
        for upgrade in UPGRADES:
            tick[0] += BUILD_TIMES[upgrade]
            actions.append({"type": "build", "upgrade": upgrade})

    import sys
    print(f"[INFO] ticks used: {tick[0]}, actions: {len(actions)}", file=sys.stderr)
    print(json.dumps({"actions": actions}, indent=2))


if __name__ == "__main__":
    main()

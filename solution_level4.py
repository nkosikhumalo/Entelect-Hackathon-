#!/usr/bin/env python3
"""Level 4 strategy — build every upgrade across all 30 towns."""

import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVEL = json.loads((ROOT / "4.txt").read_text())
TOTAL_TICKS = LEVEL["run"]["total_ticks"]
TOWNS = list(LEVEL["towns"].keys())

# Exact construction totals for the eleven upgrades at each Level 4 town, plus
# the two one-off tools.  All crafting occurs at Demacia's affinity workshop.
TOWN_COUNT = len(TOWNS)
COMPONENTS = {
    "planks": 23 * TOWN_COUNT,
    "thatch": 4 * TOWN_COUNT,
    "rope": 13 * TOWN_COUNT + 2,
    "fencing": 6 * TOWN_COUNT,
    "mortar": 29 * TOWN_COUNT,
    "bricks": 29 * TOWN_COUNT,
    "stone-blocks": 10 * TOWN_COUNT,
    "kiln-glass": 4 * TOWN_COUNT,
    "nets": 2 * TOWN_COUNT,
    "iron-fittings": 2 * TOWN_COUNT + 2,
}

# Raw inputs after expanding the component dependency chain.
RAW = {
    "wood": 2 * COMPONENTS["planks"] + 2 * COMPONENTS["fencing"]
            + 2 * COMPONENTS["kiln-glass"] + COMPONENTS["iron-fittings"],
    "wheat": 2 * COMPONENTS["thatch"],
    "sheep": 2 * COMPONENTS["rope"],
    "clay": COMPONENTS["mortar"] + 2 * COMPONENTS["bricks"]
            + 2 * COMPONENTS["kiln-glass"],
    "stone": COMPONENTS["mortar"] + 3 * COMPONENTS["stone-blocks"],
    "ore": 2 * COMPONENTS["iron-fittings"],
}


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
    for qty in (100, 200, 500, 1200, 3000, 7000, 16000):
        buy("fish", qty * 2, "Noxus")
        buy("wheat", qty, "Marrowfen")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # ── Phase 2: Gather the required ore (N1 yields 5 per action) ────────────
    travel_to("N1")
    for _ in range((RAW["ore"] + 4) // 5):
        tick[0] += 3   # mine gather-time, no pickaxe yet
        add("gather")

    # ── Phase 3: Buy construction materials ───────────────────────────────────
    travel_to("Demacia")
    buy("wood",  RAW["wood"], "Piltover")
    buy("wheat", RAW["wheat"], "Marrowfen")
    buy("sheep", RAW["sheep"], "Zaun")
    buy("clay",  RAW["clay"], "Aurora")
    buy("stone", RAW["stone"], "Demacia")
    travel_to("Demacia")

    # ── Phase 4: Craft all components and tools at Demacia ────────────────────
    for item, qty in [
        ("planks",        COMPONENTS["planks"]),
        ("thatch",        COMPONENTS["thatch"]),
        ("mortar",        COMPONENTS["mortar"]),
        ("bricks",        COMPONENTS["bricks"]),
        ("stone-blocks",  COMPONENTS["stone-blocks"]),
        ("kiln-glass",    COMPONENTS["kiln-glass"]),
        ("rope",          COMPONENTS["rope"]),
        ("fencing",       COMPONENTS["fencing"]),
        ("nets",          COMPONENTS["nets"]),
        ("iron-fittings", COMPONENTS["iron-fittings"]),
        ("boots",           1),
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

    c_dem_nox, _ = dijkstra(G_POST, "Demacia", "Noxus")
    c_nox_mar, _ = dijkstra(G_POST, "Noxus", "Marrowfen")
    c_mar_dem, _ = dijkstra(G_POST, "Marrowfen", "Demacia")
    loop_overhead = 1 + c_dem_nox + 1 + c_nox_mar + c_mar_dem + 1

    used_ticks = tick[0]
    remaining = TOTAL_TICKS - used_ticks

    # Use fixed large batches then compute exact final batch
    batches = [6000, 15000]
    for qty in batches:
        cost = loop_overhead + qty
        if remaining - cost < loop_overhead + 1:
            break
        remaining -= cost
        buy("fish", qty * 2, "Noxus")
        buy("wheat", qty, "Marrowfen")
        travel_to("Demacia")
        craft("fish-n-chips", qty)
        sell_item("fish-n-chips", qty)

    # Final batch — fill exactly
    final_qty = remaining - loop_overhead
    if final_qty > 0:
        buy("fish", final_qty * 2, "Noxus")
        buy("wheat", final_qty, "Marrowfen")
        travel_to("Demacia")
        craft("fish-n-chips", final_qty)
        sell_item("fish-n-chips", final_qty)

    import sys
    print(f"[INFO] total tracked ticks: {tick[0]}", file=sys.stderr)
    print(json.dumps({"actions": actions}, indent=2))


if __name__ == "__main__":
    main()

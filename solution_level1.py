#!/usr/bin/env python3
"""Level 1 solution — gather sheep at N1, sell at Piltover, fill all 1000 ticks."""

import heapq
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVEL = json.loads((ROOT / "1.txt").read_text())
TOTAL_TICKS = LEVEL["run"]["total_ticks"]  # 1000


def build_graph():
    g = {}
    for edge in LEVEL["routes"]:
        a, b = edge["between"]
        w = edge["weight"]
        g.setdefault(a, []).append((b, w))
        g.setdefault(b, []).append((a, w))
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
    g = build_graph()
    actions = []
    tick = 0
    loc = LEVEL["run"]["starting_town"]  # Demacia

    def travel_to(dst):
        nonlocal loc, tick
        if loc == dst:
            return
        cost, path = dijkstra(g, loc, dst)
        tick += cost
        for step in path:
            actions.append({"type": "travel", "destination": step})
        loc = dst

    # Best node: N1 (sheep, yield=8, gather=2t) — 20 Enteloot/tick raw
    # Sell at Piltover (N1->N2->Piltover = 5 ticks, cheapest sell town to reach)
    # Route to N1: Demacia->N3(6)->N6(5)->N1(4) = 15 ticks

    # Travel to N1
    travel_to("N1")
    # Remaining ticks after arriving: 1000 - 15 = 985
    # Need 6 ticks at end to travel N1->Piltover(5) + sell(1)
    gather_ticks = TOTAL_TICKS - tick - 6  # 979 ticks
    n_gathers = gather_ticks // 2           # 489 full gathers

    for _ in range(n_gathers):
        tick += 2
        actions.append({"type": "gather"})

    # Travel to Piltover and sell all sheep
    travel_to("Piltover")
    tick += 1
    actions.append({"type": "sell", "item": "sheep", "quantity": n_gathers * 8})

    import sys
    print(f"[INFO] ticks used: {tick}, gathers: {n_gathers}, sheep: {n_gathers*8}", file=sys.stderr)
    print(json.dumps({"actions": actions}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Small local validator for Level 2 action plans."""
import json
from collections import Counter, defaultdict

level = json.load(open("2.txt"))
data = json.load(open("/tmp/level2-fixed.json"))
constants = json.load(open("resources.json"))["constants"]
all_data = json.load(open("resources.json"))
recipes = {**all_data["recipes"], **all_data["components"]}
upgrades = {**all_data["upgrades"]["production"], **all_data["upgrades"]["civic"]}
prices = {k: v["buy_price"] for k, v in all_data["resources"].items()}

graph = defaultdict(list)
for e in level["routes"]:
    a, b = e["between"]
    graph[a].append((b, e["weight"]))
    graph[b].append((a, e["weight"]))

tick = 0
loc = level["run"]["starting_town"]
cash = level["run"]["starting_enteloot"]
inventory = Counter()
built = defaultdict(set)
resource_cycles = defaultdict(int)
cash_cycles = defaultdict(int)
errors = []

def apply_passive(new_tick):
    global cash
    for town, town_data in level["towns"].items():
        for resource, amount in town_data["production"]["resources"].items():
            completed = new_tick // town_data["production"]["rate"]
            extra = completed - resource_cycles[(town, resource)]
            if extra:
                if any(upgrades[u].get("boosts") == resource for u in built[town]):
                    amount *= 2
                inventory[resource] += extra * amount
                resource_cycles[(town, resource)] = completed
        completed = new_tick // town_data["enteloot"]["rate"]
        extra = completed - cash_cycles[town]
        if extra:
            bonus = sum(upgrades[u].get("effect", {}).get("value", 0)
                        for u in built[town]
                        if upgrades[u].get("effect", {}).get("type") == "enteloot_amount_pct")
            cash += extra * int(town_data["enteloot"]["amount"] * (1 + bonus))
            cash_cycles[town] = completed

def advance(cost):
    global tick
    tick += cost
    apply_passive(tick)

for i, action in enumerate(data["actions"]):
    kind = action["type"]
    ok = True
    cost = 1
    if kind == "travel":
        dest = action["destination"]
        edges = [w for n, w in graph[loc] if n == dest]
        ok = bool(edges)
        if ok:
            cost = min(edges)
    elif kind == "gather":
        ok = loc in level["nodes"]
        if ok:
            node = level["nodes"][loc]
            cost = node["gather-time"]
    elif kind == "buy":
        item, qty = action["item"], action["quantity"]
        ok = loc in level["towns"] and item in level["towns"][loc]["production"]["resources"] and cash >= prices[item] * qty
    elif kind == "craft":
        item, qty = action["item"], action["quantity"]
        cost = qty * (1 if loc in level["towns"] and "crafting" in level["towns"][loc]["affinities"] else 2)
        ok = item in recipes and all(inventory[x] >= n * qty for x, n in recipes[item]["inputs"].items())
    elif kind == "sell":
        item, qty = action["item"], action["quantity"]
        ok = loc in level["towns"] and inventory[item] >= qty
    elif kind == "build":
        u = action["upgrade"]
        spec = upgrades[u]
        cost = spec["build_time"]
        req = spec.get("prerequisite")
        ok = u not in built[loc] and cash >= spec["enteloot_cost"] and all(inventory[x] >= n for x, n in spec["components"].items())
        if ok and req:
            if req["type"] == "any_production_upgrades":
                ok = sum(x in all_data["upgrades"]["production"] for x in built[loc]) >= req["count"]
            else:
                ok = req["upgrade"] in built[loc]
    if not ok:
        errors.append((i, action, tick, cash))
        advance(1)
        continue
    advance(cost)
    if kind == "travel": loc = action["destination"]
    elif kind == "gather": inventory[level["nodes"][loc]["resource"]] += level["nodes"][loc]["yield"]
    elif kind == "buy":
        cash -= prices[action["item"]] * action["quantity"]
        inventory[action["item"]] += action["quantity"]
    elif kind == "craft":
        for x, n in recipes[action["item"]]["inputs"].items(): inventory[x] -= n * action["quantity"]
        inventory[action["item"]] += action["quantity"]
    elif kind == "sell":
        inventory[action["item"]] -= action["quantity"]
        cash += action["quantity"] * (level["towns"][loc]["item-rates"].get(action["item"], 0))
    elif kind == "build":
        for x, n in upgrades[action["upgrade"]]["components"].items(): inventory[x] -= n
        cash -= upgrades[action["upgrade"]]["enteloot_cost"]
        built[loc].add(action["upgrade"])

print(f"tick={tick} cash={cash} valid_builds={sum(map(len,built.values()))} errors={len(errors)}")
for error in errors[:20]: print(error)

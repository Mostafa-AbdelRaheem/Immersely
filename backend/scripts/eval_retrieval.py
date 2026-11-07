import asyncio, uuid
from app.core.db import AsyncSessionLocal
from app.services.conversation_retrieval import find_similar_sentences

USER = uuid.UUID("eca856fe-f22b-4870-bce1-5dfd700dae13")

CASES = [
    ("cafe", "Herzlich willkommen! Was möchten Sie trinken?", ["Tasse Tee"]),
    ("cafe", "Möchten Sie Milch oder Zucker dazu?", ["ohne Zucker"]),
    ("cafe", "Möchten Sie noch etwas? Oder wollen Sie bezahlen?", ["Rechnung"]),
    ("cafe", "Hat es Ihnen geschmeckt?", ["Essen war sehr lecker"]),
    ("work", "Hast du morgen Zeit für das Meeting?", ["Treffen mit meiner Chefin"]),
    ("work", "Bis wann musst du das fertig haben?", ["Aufgabe bis Freitag"]),
    ("work", "Sollen wir zusammen Mittag essen?", ["Mittagspause"]),
    ("friend", "Hey, lange nicht gesehen! Wie geht es dir?", ["lange nichts von dir"]),
    ("friend", "Was hast du am Wochenende gemacht?", ["Wochenende?", "Samstag"]),
    ("friend", "Hast du Pläne für heute Abend?", ["ins Kino"]),
    ("friend", "Fährst du bald in den Urlaub?", ["nach Berlin"]),
    ("nonsense", "Quantencomputer arbeiten mit Qubits.", []),
    ("nonsense", "Der Vertrag über die Ölförderung wurde verlängert.", []),
]

async def main():
    hits, nonsense = [], []
    async with AsyncSessionLocal() as db:
        for label, query, expect in CASES:
            found = await find_similar_sentences(db, USER, query, k=18)
            print(f"\n[{label}] {query}")
            for i, (s, d) in enumerate(found[:4], 1):
                mark = "*" if any(e in s.de for e in expect) else " "
                print(f"  {i}{mark} {d:.3f}  {s.de}")
            if expect:
                ranks = [(i, d) for i, (s, d) in enumerate(found, 1)
                         if any(e in s.de for e in expect)]
                rank, dist = ranks[0]
                print(f"  expected: best rank={rank} dist={dist:.3f}")
                hits.append((rank, dist))
            else:
                nonsense.append(found[0][1])
    print("\nSUMMARY")
    print("hit@1:", sum(1 for r, _ in hits if r == 1), "/", len(hits))
    print("hit@3:", sum(1 for r, _ in hits if r <= 3), "/", len(hits))
    print("expected dist min/max: %.3f / %.3f" % (min(d for _, d in hits), max(d for _, d in hits)))
    print("nonsense top1 dist:", [round(d, 3) for d in nonsense])

asyncio.run(main())

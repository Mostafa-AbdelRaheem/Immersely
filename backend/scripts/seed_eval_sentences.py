# scripts/seed_eval_sentences.py
"""Seed the eval account with a fixed sentence set for testing Conversations.

Run from backend/:  PYTHONPATH=. python scripts/seed_eval_sentences.py
Safe to re-run: sentences whose German text already exists are skipped.
Goes through create_sentence(), so embeddings and tags are generated.
"""
import asyncio
import uuid

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.sentence import Sentence
from app.schemas.sentence import SentenceCreate
from app.services.sentences import create_sentence

EVAL_USER_ID = uuid.UUID("eca856fe-f22b-4870-bce1-5dfd700dae13")

SEED: list[tuple[str, str]] = [
    # cafe / food
    ("Ich hätte gern eine Tasse Tee.", "I would like a cup of tea."),
    ("Können wir bitte die Rechnung haben?", "Could we have the bill, please?"),
    ("Haben Sie auch etwas ohne Zucker?", "Do you also have something without sugar?"),
    ("Das Essen war sehr lecker.", "The food was very tasty."),
    # work / friend
    ("Ich habe morgen ein Treffen mit meiner Chefin.", "I have a meeting with my boss tomorrow."),
    ("Kannst du mir bei diesem Projekt helfen?", "Can you help me with this project?"),
    ("Ich muss die Aufgabe bis Freitag abgeben.", "I have to hand in the task by Friday."),
    ("Wir machen um eins Mittagspause.", "We take our lunch break at one."),
    ("Wie war dein Wochenende?", "How was your weekend?"),
    ("Am Samstag war ich mit meiner Schwester im Park.", "On Saturday I was in the park with my sister."),
    ("Ich habe lange nichts von dir gehört.", "I haven't heard from you in a long time."),
    ("Hast du Lust, heute Abend ins Kino zu gehen?", "Do you feel like going to the cinema tonight?"),
    ("Ich fahre nächste Woche nach Berlin.", "I'm going to Berlin next week."),
    # distractors
    ("Der Arzt sagt, ich soll mehr Wasser trinken.", "The doctor says I should drink more water."),
    ("Die Wohnung hat zwei Zimmer und einen Balkon.", "The apartment has two rooms and a balcony."),
    ("Es regnet seit gestern ohne Pause.", "It has been raining without a break since yesterday."),
    ("Ich lerne seit zwei Jahren Deutsch.", "I have been learning German for two years."),
    ("Das Zimmer kostet vierhundert Euro im Monat.", "The room costs four hundred euros a month."),
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Sentence.de).where(Sentence.user_id == EVAL_USER_ID)
        )
        existing = set(result.scalars().all())
        seed_de = {de for de, _ in SEED}
        print(f"existing: {len(existing)}; not in seed set: {sorted(existing - seed_de)}")

        created = skipped = 0
        for de, en in SEED:
            if de in existing:
                skipped += 1
                continue
            sentence = await create_sentence(
                db, EVAL_USER_ID, SentenceCreate(de=de, en=en)
            )
            created += 1
            print(f"  + {sentence.topics} {sentence.de}")
        print(f"created={created} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
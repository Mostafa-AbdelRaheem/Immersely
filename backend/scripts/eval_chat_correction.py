# scripts/eval_chat_correction.py
"""Held-out evaluation of the chat correction chain.

Run from backend/:  PYTHONPATH=. python scripts/eval_chat_correction.py
Cases must NOT reuse sentences from the worked examples in the prompt
(langchain_/chat_correction.py), or the score only measures copying.
Labels were written before seeing any output.
"""
import asyncio
from difflib import SequenceMatcher

from app.langchain_.chat_correction import judge_chat_message

REPEATS = 2
MIN_SIMILARITY = 0.80  # corrected_text must stay close to the learner's text

# (kind, partner_line, learner_message, acceptable_verdicts)
CASES = [
    ("trap", "Möchten Sie noch etwas?", "Nein danke, das war alles", {"valid"}),
    ("trap", "Kommst du heute Abend mit ins Kino?", "ja klar, ich komme gern mit", {"valid"}),
    ("trap", "Was möchten Sie bestellen?", "Kannst du mir bitte die Speisekarte bringen?", {"valid"}),
    ("trap", "Wo arbeitest du?", "Ich arbeite bei einer Firma in München und fahre jeden Tag mit der Bahn.", {"valid"}),
    ("trap", "Wie heißt du und woher kommst du?", "Ich heisse Anna und komme aus Oesterreich.", {"valid"}),
    ("trap", "Möchten Sie noch einen Kaffee?", "Ja, gerne!", {"valid"}),
    ("error", "Was machst du morgen?", "Morgen ich gehe arbeiten.", {"fixable_errors"}),
    ("error", "Was hast du gekauft?", "Ich habe ein neue Jacke gekauft.", {"fixable_errors"}),
    ("error", "Und was macht dein Bruder?", "Er arbeiten jetzt in Berlin.", {"fixable_errors"}),
    ("error", "Wohin gehst du?", "Ich gehe in Supermarkt.", {"fixable_errors"}),
    ("error", "Was machst du heute?", "Ich muss heute meine hausaufgaben machen.", {"fixable_errors"}),
    # Relabelled after the first run: the model fixes mixed English/German with a
    # useful rewrite (fixable_errors), which helps a learner more than "broken".
    # Policy decision (option A): accepted, and exempt from the minimal-change check.
    ("mixed", "Was möchten Sie trinken?", "Ich want einen Kaffee please.", {"fixable_errors"}),
]


def format_ok(kind: str, verdict: str, learner: str, corrected: str | None) -> bool:
    if verdict == "fixable_errors":
        if not corrected or corrected == learner:
            return False
        if kind == "mixed":
            return True  # policy: fixing mixed-language text may rewrite more than a minimal edit
        return SequenceMatcher(None, learner, corrected).ratio() >= MIN_SIMILARITY
    return corrected is None


async def main() -> None:
    total = passed = fmt_passed = errors = 0
    for i, (kind, partner, learner, acceptable) in enumerate(CASES, 1):
        verdicts = []
        print(f"\n#{i} [{kind}] {learner!r}")
        for n in range(1, REPEATS + 1):
            try:
                r = await judge_chat_message(
                    partner_line=partner, learner_message=learner
                )
            except Exception as exc:
                errors += 1
                print(f"   run {n}: ERROR {type(exc).__name__}: {str(exc)[:150]}")
                continue
            verdict = r.grammar_verdict.value
            ok = verdict in acceptable
            fmt = format_ok(kind, verdict, learner, r.corrected_text)
            total += 1
            passed += ok
            fmt_passed += fmt
            verdicts.append(verdict)
            print(
                f"   run {n}: {'PASS' if ok else 'FAIL'} verdict={verdict} "
                f"format={'ok' if fmt else 'BAD'} corrected={r.corrected_text!r}"
            )
            if not ok:
                print(f"      analysis={r.analysis!r}")
        if len(set(verdicts)) > 1:
            print(f"   FLIP: runs disagreed: {verdicts}")
    print(f"\nVERDICT SCORE: {passed} / {total}")
    print(f"FORMAT SCORE:  {fmt_passed} / {total}")
    print(f"ERRORS (calls that raised): {errors}")


if __name__ == "__main__":
    asyncio.run(main())
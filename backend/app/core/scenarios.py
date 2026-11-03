# app/core/scenarios.py
"""Fixed role-play scenarios for Conversations.

App-wide config, not user data (same reasoning as core/topics.py).
Text fields are written in English because they go into an English
prompt; the partner itself speaks German.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    partner_role: str
    user_role: str
    situation: str
    formality: str  # "du" or "Sie": how the partner addresses the learner


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="cafe_waiter",
        title="At the café",
        partner_role="a friendly waiter at a café in Germany",
        user_role="a customer who has just sat down",
        situation=(
            "The customer orders drinks and maybe something to eat, asks "
            "about the menu, and eventually asks for the bill."
        ),
        formality="Sie",
    ),
    Scenario(
        id="work_colleague",
        title="Chatting with a colleague",
        partner_role="a friendly colleague at the same company",
        user_role="a colleague on a short break at the office",
        situation=(
            "The two colleagues talk about the workday, a current project, "
            "an upcoming meeting, and plans for lunch."
        ),
        formality="du",
    ),
    Scenario(
        id="friend_catchup",
        title="Catching up with a friend",
        partner_role="a close friend the learner has not seen for a few weeks",
        user_role="the friend who is catching up",
        situation=(
            "The friends ask how things have been and share news about "
            "work, plans and free time."
        ),
        formality="du",
    ),
)

SCENARIOS_BY_ID: dict[str, Scenario] = {s.id: s for s in SCENARIOS}
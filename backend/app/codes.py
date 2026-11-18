import json
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import FaultCard

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "codes.json"


def load_cards() -> Dict[str, FaultCard]:
    """Read codes.json and check every card has the right shape."""
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    return {card["code"].upper(): FaultCard(**card) for card in raw}


CARDS = load_cards()


def list_cards() -> List[FaultCard]:
    return list(CARDS.values())


def get_card(code: str) -> Optional[FaultCard]:
    return CARDS.get(code.strip().upper())
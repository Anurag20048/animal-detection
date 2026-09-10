import re
from typing import Dict


DEFAULT_PREFIXES = {
    "Cow": "C",
    "Buffalo": "B",
    "Sheep": "S",
    "Other Animals": "O",
}


class AnimalIDGenerator:
    def __init__(self, prefixes: Dict[str, str] | None = None) -> None:
        self.prefixes = prefixes or DEFAULT_PREFIXES
        self.counters = {prefix: 0 for prefix in self.prefixes.values()}

    def observe(self, animal_id: str) -> None:
        match = re.fullmatch(r"([A-Z])(\d+)", str(animal_id).strip())
        if not match:
            return
        prefix, number = match.groups()
        if prefix in self.counters:
            self.counters[prefix] = max(self.counters[prefix], int(number))

    def next_id(self, animal_type: str) -> str:
        prefix = self.prefixes.get(animal_type, self.prefixes["Other Animals"])
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}{self.counters[prefix]:05d}"

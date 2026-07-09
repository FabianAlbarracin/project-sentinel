import logging
import re
from typing import Optional

from app.domain.entities import Observation, WatchTerm

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, watch_terms: dict[int, list[WatchTerm]]):
        self._watch_terms = watch_terms

    def match_observation(
        self, observation: Observation
    ) -> Optional[int]:
        if not observation.title:
            return None

        title_lower = observation.title.lower()

        for watch_item_id, terms in self._watch_terms.items():
            if self._matches_item(title_lower, terms):
                return watch_item_id

        return None

    def _matches_item(
        self, title_lower: str, terms: list[WatchTerm]
    ) -> bool:
        anchors = [t for t in terms if t.term_type.value == "ANCHOR"]
        excludes = [t for t in terms if t.term_type.value == "EXCLUDE"]

        if not anchors:
            return False

        has_anchor = any(
            self._term_matches(title_lower, t.term) for t in anchors
        )
        if not has_anchor:
            return False

        has_exclude = any(
            self._term_matches(title_lower, t.term) for t in excludes
        )
        if has_exclude:
            return False

        return True

    @staticmethod
    def _term_matches(text: str, term: str) -> bool:
        pattern = re.escape(term.lower())
        return bool(re.search(rf"\b{pattern}\b", text))

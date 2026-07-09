import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities import TermType, WatchTerm, ObservationType
from app.domain.services import Processor


@pytest.fixture
def sample_anchor_terms():
    return [
        WatchTerm(
            id=1, watch_item_id=1, term="kindle",
            term_type=TermType.ANCHOR, created_at=None,
        ),
        WatchTerm(
            id=2, watch_item_id=1, term="paperwhite",
            term_type=TermType.ANCHOR, created_at=None,
        ),
        WatchTerm(
            id=3, watch_item_id=1, term="scribe",
            term_type=TermType.ANCHOR, created_at=None,
        ),
    ]


@pytest.fixture
def sample_exclude_terms():
    return [
        WatchTerm(
            id=4, watch_item_id=1, term="case",
            term_type=TermType.EXCLUDE, created_at=None,
        ),
        WatchTerm(
            id=5, watch_item_id=1, term="cover",
            term_type=TermType.EXCLUDE, created_at=None,
        ),
        WatchTerm(
            id=6, watch_item_id=1, term="ebook",
            term_type=TermType.EXCLUDE, created_at=None,
        ),
        WatchTerm(
            id=7, watch_item_id=1, term="screen protector",
            term_type=TermType.EXCLUDE, created_at=None,
        ),
    ]


@pytest.fixture
def watch_terms(sample_anchor_terms, sample_exclude_terms):
    return {1: sample_anchor_terms + sample_exclude_terms}


@pytest.fixture
def processor(watch_terms):
    return Processor(watch_terms)

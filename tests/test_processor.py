from datetime import datetime

from app.domain.entities import Observation, ObservationType


class TestProcessorMatchObservation:
    def test_match_by_anchor_term(self, processor):
        obs = Observation(
            title="Amazon Kindle Paperwhite on sale",
            observation_type=ObservationType.PRODUCT,
        )
        result = processor.match_observation(obs)
        assert result == 1

    def test_match_case_insensitive(self, processor):
        obs = Observation(
            title="KINDLE SCRIBE deal today",
            observation_type=ObservationType.POST,
        )
        result = processor.match_observation(obs)
        assert result == 1

    def test_no_match_without_anchor(self, processor):
        obs = Observation(
            title="Steam Deck on sale",
            observation_type=ObservationType.PRODUCT,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_exclude_case_cancels_match(self, processor):
        obs = Observation(
            title="Kindle Case leather cover",
            observation_type=ObservationType.PRODUCT,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_exclude_screen_protector_cancels_match(self, processor):
        obs = Observation(
            title="Kindle screen protector anti-glare",
            observation_type=ObservationType.PRODUCT,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_exclude_ebook_cancels_match(self, processor):
        obs = Observation(
            title="Free Kindle ebook download",
            observation_type=ObservationType.POST,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_anchor_with_exclude_in_different_field(self, processor):
        obs = Observation(
            title="Kindle Paperwhite",
            coupon="CASE25",
            observation_type=ObservationType.COUPON,
        )
        result = processor.match_observation(obs)
        assert result == 1

    def test_anchor_only_in_title_not_raw_content(self, processor):
        obs = Observation(
            title="Deal of the day",
            raw_content="This is about the Kindle Scribe",
            observation_type=ObservationType.POST,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_none_fields(self, processor):
        obs = Observation(
            title=None,
            observation_type=ObservationType.UNKNOWN,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_word_boundary_anchor(self, processor):
        obs = Observation(
            title="I love my kindle device",
            observation_type=ObservationType.POST,
        )
        result = processor.match_observation(obs)
        assert result == 1

    def test_no_partial_match(self, processor):
        obs = Observation(
            title="Kindling for the fireplace",
            observation_type=ObservationType.POST,
        )
        result = processor.match_observation(obs)
        assert result is None

    def test_multiple_watch_items_no_match(self, processor):
        from app.domain.entities import TermType, WatchTerm

        processor._watch_terms[2] = [
            WatchTerm(id=8, watch_item_id=2, term="steam deck",
                      term_type=TermType.ANCHOR, created_at=None),
        ]
        obs = Observation(
            title="Steam Deck OLED on sale",
            observation_type=ObservationType.PRODUCT,
        )
        result = processor.match_observation(obs)
        assert result == 2

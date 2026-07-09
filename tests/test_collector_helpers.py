from app.collectors.reddit.collector import (
    _is_deal_post,
    _classify_post,
    _extract_coupon_code,
)
from app.collectors.telegram.collector import (
    _is_deal_message,
    _classify_message,
    _extract_coupon_code as _telegram_extract_coupon,
    _parse_channels,
)
from app.domain.entities import ObservationType


class TestRedditDealFilter:
    def test_deal_with_sale_word(self):
        assert _is_deal_post("Kindle on sale today") is True

    def test_deal_with_price(self):
        assert _is_deal_post("Kindle Paperwhite $89.99") is True

    def test_deal_with_discount(self):
        assert _is_deal_post("50% off Kindle today") is True

    def test_deal_with_coupon(self):
        assert _is_deal_post("Kindle coupon code inside") is True

    def test_not_a_deal_question(self):
        assert _is_deal_post("Which font do you use on Kindle?") is False

    def test_not_a_deal_discussion(self):
        assert _is_deal_post("My Kindle arrived today") is False

    def test_case_insensitive(self):
        assert _is_deal_post("KINDLE ON SALE NOW") is True


class TestRedditClassification:
    def test_classify_coupon(self):
        assert _classify_post("Kindle coupon code WELCOME25", "") == ObservationType.COUPON

    def test_classify_post(self):
        assert _classify_post("Kindle on sale at Woot", "") == ObservationType.POST

    def test_classify_discount(self):
        assert _classify_post("20% off Kindle with promo code", "") == ObservationType.COUPON


class TestRedditCouponExtraction:
    def test_extract_coupon_code(self):
        code = _extract_coupon_code("Use code WELCOME25 for Kindle", "")
        assert code == "WELCOME25"

    def test_no_coupon(self):
        code = _extract_coupon_code("Kindle on sale", "")
        assert code is None

    def test_skip_words(self):
        code = _extract_coupon_code("Today KINDLE sale", "")
        assert code is None

    def test_skip_numeric_only(self):
        code = _extract_coupon_code("Save 12345 on Kindle", "")
        assert code is None


class TestTelegramDealFilter:
    def test_deal_with_joylink(self):
        assert _is_deal_message("Kindle Paperwhite https://joylink.io/abc") is True

    def test_deal_with_amazon(self):
        assert _is_deal_message("Comprar en Amazon Kindle") is True

    def test_deal_with_ad_hashtag(self):
        assert _is_deal_message("#ad Kindle deal") is True

    def test_deal_with_price(self):
        assert _is_deal_message("Kindle desde $49.99") is True

    def test_exclude_reporto(self):
        assert _is_deal_message("Reporto llegada de Kindle") is False

    def test_exclude_llego(self):
        assert _is_deal_message("Llegó mi Kindle hoy") is False

    def test_exclude_llegada(self):
        assert _is_deal_message("Llegada de Kindle Colorsoft") is False

    def test_just_conversation(self):
        assert _is_deal_message("K . Reporto llegada de Kindle") is False

    def test_deal_with_temu(self):
        assert _is_deal_message("Kindle 👉 Comprar en Temu: https://temu.to/abc") is True


class TestParseChannels:
    def test_single_channel(self):
        assert _parse_channels("Clubgratis") == ["Clubgratis"]

    def test_multiple_channels(self):
        assert _parse_channels("Clubgratis,kindle_deals") == ["Clubgratis", "kindle_deals"]

    def test_strip_at(self):
        assert _parse_channels("@Clubgratis,@kindle_deals") == ["Clubgratis", "kindle_deals"]

    def test_empty(self):
        assert _parse_channels("") == []

    def test_whitespace(self):
        assert _parse_channels("  Clubgratis , kindle_deals  ") == ["Clubgratis", "kindle_deals"]

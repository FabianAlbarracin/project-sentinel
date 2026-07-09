from decimal import Decimal

from app.domain.entities import Observation, ObservationType
from app.infrastructure.notifications import _escape, _format_price


class TestEscape:
    def test_escape_underscore(self):
        assert _escape("hello_world") == r"hello\_world"

    def test_escape_asterisk(self):
        assert _escape("bold *text*") == r"bold \*text\*"

    def test_escape_brackets(self):
        assert _escape("[link]") == r"\[link\]"

    def test_escape_parentheses(self):
        assert _escape("(text)") == r"\(text\)"

    def test_escape_period(self):
        assert _escape("hello.world") == r"hello\.world"

    def test_escape_dash(self):
        assert _escape("hello-world") == r"hello\-world"

    def test_escape_exclamation(self):
        assert _escape("hello!") == r"hello\!"

    def test_escape_multiple(self):
        text = "_Hello_ [world] (test)!"
        assert _escape(text) == r"\_Hello\_ \[world\] \(test\)\!"

    def test_normal_text_unchanged(self):
        assert _escape("Hello World") == "Hello World"


class TestFormatPrice:
    def test_integer_price(self):
        assert _format_price(Decimal("89")) == "89"

    def test_decimal_price(self):
        assert _format_price(Decimal("89.99")) == "89.99"

    def test_price_with_extra_zeros(self):
        assert _format_price(Decimal("89.9900")) == "89.99"

    def test_price_with_cents(self):
        assert _format_price(Decimal("49.50")) == "49.5"

    def test_whole_number(self):
        assert _format_price(Decimal("100.00")) == "100"

    def test_large_price(self):
        assert _format_price(Decimal("1234.56")) == "1,234.56"


class TestBuildMessage:
    def _make_obs(self, obs_type, title=None, price=None, url=None, coupon=None):
        return Observation(
            source_id=1,
            observation_type=obs_type,
            title=title,
            price=price,
            currency="USD",
            url=url,
            coupon=coupon,
        )

    def test_product_message(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle Paperwhite",
            price=Decimal("89.99"),
            url="https://example.com",
        )
        msg = notifier._build_message(obs, "Woot")
        assert "Producto detectado" in msg
        assert "Woot" in msg
        assert "Kindle Paperwhite" in msg
        assert "89.99 USD" in msg
        assert "Abrir publicacion" in msg

    def test_product_without_price(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle",
            url="https://example.com",
        )
        msg = notifier._build_message(obs, "Woot")
        assert "89.99" not in msg

    def test_product_without_url(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle",
        )
        msg = notifier._build_message(obs, "Woot")
        assert "Abrir publicacion" not in msg

    def test_coupon_message(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.COUPON,
            title="Kindle deal",
            coupon="KINDLE25",
            url="https://example.com",
        )
        msg = notifier._build_message(obs, "Reddit")
        assert "Cupon detectado" in msg
        assert "KINDLE25" in msg
        assert "Reddit" in msg

    def test_post_message(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.POST,
            title="Kindle discussion",
            url="https://reddit.com/r/kindle",
        )
        msg = notifier._build_message(obs, "Reddit")
        assert "Publicacion relevante" in msg
        assert "Reddit" in msg

    def test_unknown_type_uses_post_format(self):
        from app.infrastructure.notifications import TelegramNotifier
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        obs = self._make_obs(
            ObservationType.UNKNOWN,
            title="Some observation",
        )
        msg = notifier._build_message(obs, "Unknown")
        assert "Publicacion relevante" in msg

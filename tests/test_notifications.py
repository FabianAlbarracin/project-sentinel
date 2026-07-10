from decimal import Decimal

from app.domain.entities import Observation, ObservationType
from app.infrastructure.notifications import (
    TelegramNotifier,
    _escape,
    _extract_channel,
    _format_price,
)


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


class TestExtractChannel:
    def test_standard_url(self):
        assert _extract_channel("https://t.me/Clubgratis/123") == "Clubgratis"

    def test_simple_url(self):
        assert _extract_channel("https://t.me/kindle_deals") == "kindle_deals"

    def test_no_match(self):
        assert _extract_channel("https://reddit.com/r/kindle") is None

    def test_none(self):
        assert _extract_channel(None) is None

    def test_empty(self):
        assert _extract_channel("") is None


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

    def _build(self, obs, source_name):
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        return notifier._build_message(obs, source_name)

    def test_product_message_woot(self):
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle Paperwhite",
            price=Decimal("89.99"),
            url="https://example.com",
        )
        msg = self._build(obs, "woot")
        assert "Producto detectado" in msg
        assert "Fuente: Woot" in msg
        assert "Producto:" in msg
        assert "Kindle Paperwhite" in msg
        assert "Precio: 89.99 USD" in msg
        assert "Abrir publicacion" in msg

    def test_product_without_price(self):
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle",
            url="https://example.com",
        )
        msg = self._build(obs, "woot")
        assert "Precio:" not in msg

    def test_product_without_url(self):
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle",
        )
        msg = self._build(obs, "woot")
        assert "Abrir publicacion" not in msg

    def test_product_fuente_inline(self):
        obs = self._make_obs(ObservationType.PRODUCT, title="Kindle")
        msg = self._build(obs, "reddit")
        assert "Fuente: Reddit" in msg
        assert "\nFuente:\n" not in msg

    def test_product_producto_with_break(self):
        obs = self._make_obs(
            ObservationType.PRODUCT,
            title="Kindle Paperwhite Signature Edition 32GB",
        )
        msg = self._build(obs, "woot")
        assert "\nProducto:\n" in msg

    def test_coupon_message_reddit(self):
        obs = self._make_obs(
            ObservationType.COUPON,
            title="Kindle deal",
            coupon="KINDLE25",
            url="https://example.com",
        )
        msg = self._build(obs, "reddit")
        assert "Cupon detectado" in msg
        assert "Codigo: KINDLE25" in msg
        assert "Fuente: Reddit" in msg

    def test_coupon_without_code(self):
        obs = self._make_obs(
            ObservationType.COUPON,
            title="Kindle deal",
        )
        msg = self._build(obs, "reddit")
        assert "Codigo:" not in msg
        assert "Fuente: Reddit" in msg

    def test_coupon_titulo_with_break(self):
        obs = self._make_obs(
            ObservationType.COUPON,
            title="Woot with Kindles on sale today",
            coupon="KINDLE25",
        )
        msg = self._build(obs, "reddit")
        assert "\nTitulo:\n" in msg

    def test_post_message_reddit(self):
        obs = self._make_obs(
            ObservationType.POST,
            title="Kindle discussion",
            url="https://reddit.com/r/kindle",
        )
        msg = self._build(obs, "reddit")
        assert "Publicacion relevante" in msg
        assert "Fuente: Reddit" in msg

    def test_post_titulo_with_break(self):
        obs = self._make_obs(
            ObservationType.POST,
            title="Kindle Scribe 2022 Trade-in discussion",
        )
        msg = self._build(obs, "reddit")
        assert "\nTitulo:\n" in msg

    def test_post_fuente_inline(self):
        obs = self._make_obs(ObservationType.POST, title="Test")
        msg = self._build(obs, "reddit")
        assert "Fuente: Reddit" in msg
        assert "\nFuente:\n" not in msg

    def test_unknown_type_uses_post_format(self):
        obs = self._make_obs(
            ObservationType.UNKNOWN,
            title="Some observation",
        )
        msg = self._build(obs, "woot")
        assert "Publicacion relevante" in msg

    def test_telegram_message_format(self):
        obs = self._make_obs(
            ObservationType.POST,
            title="Kindle Paperwhite joylink.io/abc",
            url="https://t.me/Clubgratis/456",
        )
        msg = self._build(obs, "telegram")
        assert "Mensaje relevante" in msg
        assert "Grupo: Clubgratis" in msg
        assert "Mensaje:" in msg
        assert "Abrir mensaje" in msg

    def test_telegram_message_no_url(self):
        obs = self._make_obs(
            ObservationType.POST,
            title="Kindle Paperwhite",
        )
        msg = self._build(obs, "telegram")
        assert "Grupo: desconocido" in msg
        assert "Abrir mensaje" not in msg

    def test_telegram_coupon_goes_to_telegram_format(self):
        obs = self._make_obs(
            ObservationType.COUPON,
            title="Kindle coupon",
            coupon="KINDLE25",
            url="https://t.me/Clubgratis/456",
        )
        msg = self._build(obs, "telegram")
        assert "Mensaje relevante" in msg
        assert "Cupon detectado" not in msg
        assert "Grupo: Clubgratis" in msg

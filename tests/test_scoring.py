from app.collectors.scoring import score_text, is_deal, DEAL_THRESHOLD


class TestScorePositive:
    def test_price_signal(self):
        assert score_text("Kindle Paperwhite $89.99") >= DEAL_THRESHOLD

    def test_price_with_commas(self):
        assert score_text("MacBook $1,299.00 today") >= DEAL_THRESHOLD

    def test_price_no_decimals(self):
        assert score_text("Kindle Scribe $132 at Target") >= DEAL_THRESHOLD

    def test_percent_discount(self):
        assert score_text("50% off Kindle today") >= DEAL_THRESHOLD

    def test_percent_discount_lowercase(self):
        assert score_text("20% off kindle paperwhite") >= DEAL_THRESHOLD

    def test_sale_keyword(self):
        assert score_text("Kindle on sale today") >= DEAL_THRESHOLD

    def test_discount_keyword(self):
        assert score_text("Kindle discount code inside") >= DEAL_THRESHOLD

    def test_clearance(self):
        assert score_text("Kindle clearance all models") >= DEAL_THRESHOLD

    def test_refurbished(self):
        assert score_text("Refurbished Kindle Paperwhite") >= DEAL_THRESHOLD

    def test_price_drop(self):
        assert score_text("Kindle price drop alert") >= DEAL_THRESHOLD

    def test_marked_down(self):
        assert score_text("Kindle marked down 30%") >= DEAL_THRESHOLD

    def test_coupon_explicit(self):
        assert score_text("Kindle coupon code WELCOME25") >= DEAL_THRESHOLD

    def test_promo_code(self):
        assert score_text("Use promo code KINDLE25 for discount") >= DEAL_THRESHOLD

    def test_prime_day(self):
        assert score_text("Prime Day Deal on Kindle Scribe") >= DEAL_THRESHOLD

    def test_black_friday(self):
        assert score_text("Black Friday Kindle sale 2026") >= DEAL_THRESHOLD

    def test_store_context(self):
        assert score_text("Kindle at Target $132.99") >= DEAL_THRESHOLD

    def test_save_with_price(self):
        assert score_text("Save $50 on Kindle Paperwhite") >= DEAL_THRESHOLD

    def test_save_with_percent(self):
        assert score_text("Save 20% on Kindle Scribe today") >= DEAL_THRESHOLD

    def test_save_up_to(self):
        assert score_text("Save up to 30% on Kindle") >= DEAL_THRESHOLD

    def test_save_money(self):
        assert score_text("save money with woot") >= DEAL_THRESHOLD

    def test_save_big(self):
        assert score_text("Save big on Kindle this week") >= DEAL_THRESHOLD

    def test_save_now(self):
        assert score_text("Save now on refurbished Kindle") >= DEAL_THRESHOLD

    def test_saving_money(self):
        assert score_text("saving you money on Kindle accessories") >= DEAL_THRESHOLD


class TestScoreNegative:
    def test_false_positive_save_highlights(self):
        assert not is_deal(
            "Can I factory reset my kindle BUT save the highlights/notes "
            "and reload it back after?"
        )

    def test_save_battery(self):
        assert not is_deal("How to save battery life on my Kindle Paperwhite?")

    def test_save_notes(self):
        assert not is_deal("Best way to save annotations from Kindle to PC?")

    def test_save_bookmarks(self):
        assert not is_deal("Can I save my bookmarks after reset?")

    def test_question_about_device(self):
        assert not is_deal("Which font do you use on Kindle?")

    def test_factory_reset(self):
        assert not is_deal("My Kindle is frozen need factory reset help")

    def test_not_working(self):
        assert not is_deal("Kindle battery drain after update not working")

    def test_stuck_screen(self):
        assert not is_deal("Kindle screen stuck on tree logo help")

    def test_broken_screen(self):
        assert not is_deal("Dropped my Kindle screen is broken repair cost?")

    def test_issue_with_device(self):
        assert not is_deal("Refurbished paperwhite signature issues")

    def test_free_ebook(self):
        assert not is_deal("Free ebooks this week for Kindle")

    def test_kindle_edition(self):
        assert not is_deal("New release Kindle edition available")

    def test_app_or_software(self):
        assert not is_deal("Built an app that compiles your saved articles into PDF")

    def test_review_post(self):
        assert not is_deal("My review of Kindle Scribe after 6 months")

    def test_just_got_it(self):
        assert not is_deal("Just got my Kindle Paperwhite so excited!")


class TestScoreEdgeCases:
    def test_exactly_on_threshold_save_money_woot(self):
        assert score_text("save money with woot") == 3

    def test_below_threshold_new_save_woot(self):
        assert not is_deal("new save with woot")

    def test_save_with_discounts(self):
        assert is_deal("save with 4 july discounts")

    def test_empty_text(self):
        assert not is_deal("")

    def test_mixed_price_question(self):
        assert is_deal("Is $200CAD good for a Kindle?")

    def test_price_but_question(self):
        assert not is_deal("Should I buy Kindle Paperwhite $89.99 or Kobo?")

    def test_case_insensitivity(self):
        assert is_deal("KINDLE ON SALE NOW")

    def test_new_save_with_context(self):
        assert not is_deal("new save with woot")

    def test_save_alone_no_context(self):
        assert not is_deal("just save your money")

    def test_trade_comparison_question(self):
        assert is_deal(
            "Going from Kindle Paper White to Kobo Libra Color? Is $200CAD good?"
        )


class TestIsDealBackwardCompat:
    def test_original_tests_still_pass_sale(self):
        assert is_deal("Kindle on sale today")

    def test_original_tests_still_pass_price(self):
        assert is_deal("Kindle Paperwhite $89.99")

    def test_original_tests_still_pass_discount(self):
        assert is_deal("50% off Kindle today")

    def test_original_tests_still_pass_coupon(self):
        assert is_deal("Kindle coupon code inside")

    def test_original_tests_still_reject_question(self):
        assert not is_deal("Which font do you use on Kindle?")

    def test_original_tests_still_reject_discussion(self):
        assert not is_deal("My Kindle arrived today")

    def test_original_tests_still_case_insensitive(self):
        assert is_deal("KINDLE ON SALE NOW")

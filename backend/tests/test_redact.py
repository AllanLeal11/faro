from app.pipeline.redact import redact_sensitive


class TestRedactSensitive:
    def test_redacts_card_number(self):
        text = "My card number is 4111 1111 1111 1111, please charge it."
        redacted = redact_sensitive(text)
        assert "4111" not in redacted
        assert "[REDACTED-CARD]" in redacted

    def test_redacts_card_number_with_dashes(self):
        text = "Card: 4111-1111-1111-1111"
        redacted = redact_sensitive(text)
        assert "4111" not in redacted

    def test_redacts_otp_code_spanish(self):
        text = "Tu código de acceso es 483920, no lo compartas."
        redacted = redact_sensitive(text)
        assert "483920" not in redacted
        assert "[REDACTED-CODE]" in redacted

    def test_redacts_otp_code_english(self):
        text = "Your OTP is 719284, enter it now."
        redacted = redact_sensitive(text)
        assert "719284" not in redacted
        assert "[REDACTED-CODE]" in redacted

    def test_redacts_password(self):
        text = "password: hunter2secret please confirm"
        redacted = redact_sensitive(text)
        assert "hunter2secret" not in redacted
        assert "[REDACTED-PASSWORD]" in redacted

    def test_leaves_normal_text_untouched(self):
        text = "Hola, este es un mensaje normal de tu banco sobre tu cuenta."
        assert redact_sensitive(text) == text

    def test_short_numbers_are_not_touched(self):
        text = "Llamanos al 5551002000 o visita la sucursal 12."
        redacted = redact_sensitive(text)
        assert "5551002000" in redacted
        assert "12" in redacted

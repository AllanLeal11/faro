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

    def test_redacts_card_number_with_dots(self):
        text = "Confirm your card 4111.1111.1111.1111 to continue"
        redacted = redact_sensitive(text)
        assert "4111" not in redacted
        assert "[REDACTED-CARD]" in redacted

    def test_redacts_card_number_with_commas(self):
        text = "card number 4111,1111,1111,1111 please"
        redacted = redact_sensitive(text)
        assert "4111" not in redacted
        assert "[REDACTED-CARD]" in redacted

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

    def test_redacts_otp_code_when_digits_come_before_keyword(self):
        # The far more common real-world phrasing in actual bank OTP texts.
        text = "123456 is your OneBank verification code. Do not share it."
        redacted = redact_sensitive(text)
        assert "123456" not in redacted
        assert "[REDACTED-CODE]" in redacted

    def test_redacts_otp_code_digits_before_keyword_spanish(self):
        text = "483920 es tu código de verificación, no lo compartas."
        redacted = redact_sensitive(text)
        assert "483920" not in redacted
        assert "[REDACTED-CODE]" in redacted

    def test_redacts_password(self):
        text = "password: hunter2secret please confirm"
        redacted = redact_sensitive(text)
        assert "hunter2secret" not in redacted
        assert "[REDACTED-PASSWORD]" in redacted

    def test_redacts_password_with_equals_separator(self):
        text = "Your account password=hunter2 was used to log in"
        redacted = redact_sensitive(text)
        assert "hunter2" not in redacted
        assert "[REDACTED-PASSWORD]" in redacted

    def test_redacts_password_with_dash_separator(self):
        text = "contraseña-hunter2 detectada"
        redacted = redact_sensitive(text)
        assert "hunter2" not in redacted
        assert "[REDACTED-PASSWORD]" in redacted

    def test_leaves_normal_text_untouched(self):
        text = "Hola, este es un mensaje normal de tu banco sobre tu cuenta."
        assert redact_sensitive(text) == text

    def test_short_numbers_are_not_touched(self):
        text = "Llamanos al 5551002000 o visita la sucursal 12."
        redacted = redact_sensitive(text)
        assert "5551002000" in redacted
        assert "12" in redacted

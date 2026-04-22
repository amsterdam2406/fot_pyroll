from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from payroll.password_validators import ComplexPasswordValidator

User = get_user_model()


class ComplexPasswordValidatorTests(TestCase):
    def setUp(self):
        self.v = ComplexPasswordValidator()

    def test_help_text(self):
        self.assertIn('uppercase', self.v.get_help_text().lower())

    def test_valid_password(self):
        self.v.validate('SecurePass1!')

    def test_too_short(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('Sh0rt!')
        self.assertIn('password_too_short', [e.code for e in ctx.exception.error_list])

    def test_no_uppercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('nouppercase1!')
        self.assertIn('password_no_upper', [e.code for e in ctx.exception.error_list])

    def test_no_lowercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('NOLOWER123!')
        self.assertIn('password_no_lower', [e.code for e in ctx.exception.error_list])

    def test_no_digit(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('NoDigitPass!')
        self.assertIn('password_no_number', [e.code for e in ctx.exception.error_list])

    def test_no_special(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('NoSpecial123')
        self.assertIn('password_no_special', [e.code for e in ctx.exception.error_list])

    def test_contains_username(self):
        user = User(username='johndoe')
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('Johndoe123!', user=user)
        self.assertIn('password_contains_username', [e.code for e in ctx.exception.error_list])

    def test_user_none_skips_username_check(self):
        self.v.validate('ValidPass1!', user=None)

    def test_username_not_in_password_passes(self):
        self.v.validate('ValidPass1!', user=User(username='alice'))

    def test_multiple_failures(self):
        with self.assertRaises(ValidationError) as ctx:
            self.v.validate('short')
        codes = [e.code for e in ctx.exception.error_list]
        self.assertIn('password_too_short', codes)
        self.assertIn('password_no_upper', codes)
        self.assertIn('password_no_number', codes)
        self.assertIn('password_no_special', codes)
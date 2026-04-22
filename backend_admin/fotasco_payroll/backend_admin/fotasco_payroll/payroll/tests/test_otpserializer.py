from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from payroll.serializers import OTPSerializer
from payroll.models import OTP


class OTPSerializerTests(TestCase):

    # ------------------------------------------------------------------
    # Valid input
    # ------------------------------------------------------------------

    def test_valid_otp_data(self):
        data = {
            'email': 'user@example.com',
            'reference': 'ref_unique_001',
        }
        serializer = OTPSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_email_normalised_to_lowercase(self):
        data = {'email': 'User@Example.COM', 'reference': 'ref002'}
        serializer = OTPSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['email'], 'user@example.com')

    # ------------------------------------------------------------------
    # Invalid input
    # ------------------------------------------------------------------

    def test_empty_email_rejected(self):
        data = {'email': '', 'reference': 'ref003'}
        serializer = OTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_whitespace_email_rejected(self):
        data = {'email': '   ', 'reference': 'ref004'}
        serializer = OTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_email_format_rejected(self):
        data = {'email': 'notanemail', 'reference': 'ref005'}
        serializer = OTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    # ------------------------------------------------------------------
    # Read-only fields
    # ------------------------------------------------------------------

    def test_code_is_read_only(self):
        data = {'email': 'a@b.com', 'reference': 'ref006', 'code': '999999'}
        serializer = OTPSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('code', serializer.validated_data)

    def test_expires_at_is_read_only(self):
        data = {
            'email': 'a@b.com',
            'reference': 'ref007',
            'expires_at': '2099-01-01T00:00:00Z',
        }
        serializer = OTPSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('expires_at', serializer.validated_data)

    # ------------------------------------------------------------------
    # Instance (update) validation — expired OTP
    # ------------------------------------------------------------------

    def test_expired_otp_instance_is_invalid(self):
        otp = OTP.objects.create(
            email='old@example.com',
            code='111111',
            reference='ref_expired',
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        # Pass the expired instance so the serializer's validate() fires
        serializer = OTPSerializer(
            otp,
            data={'email': 'old@example.com', 'reference': 'ref_expired'},
        )
        self.assertFalse(serializer.is_valid())

    def test_fresh_otp_instance_is_valid(self):
        otp = OTP.objects.create(
            email='fresh@example.com',
            code='222222',
            reference='ref_fresh',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        serializer = OTPSerializer(
            otp,
            data={'email': 'fresh@example.com', 'reference': 'ref_fresh'},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # ------------------------------------------------------------------
    # Serialization of existing OTP model instance
    # ------------------------------------------------------------------

    def test_serializes_existing_otp(self):
        otp = OTP.objects.create(
            email='view@example.com',
            code='333333',
            reference='ref_view',
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        data = OTPSerializer(otp).data
        self.assertEqual(data['email'], 'view@example.com')
        self.assertIn('reference', data)
        self.assertIn('expires_at', data)
        # code is in the Meta.fields list and is read_only, so it IS serialised
        # for output — verify it appears
        self.assertEqual(data['code'], '333333')

    # ------------------------------------------------------------------
    # OTP model helper methods
    # ------------------------------------------------------------------

    def test_has_expired_false_for_future_otp(self):
        otp = OTP(expires_at=timezone.now() + timedelta(minutes=5))
        self.assertFalse(otp.has_expired())

    def test_has_expired_true_for_past_otp(self):
        otp = OTP(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(otp.has_expired())
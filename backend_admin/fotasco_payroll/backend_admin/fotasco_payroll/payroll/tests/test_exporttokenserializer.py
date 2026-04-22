from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from payroll.serializers import ExportTokenSerializer
from payroll.models import ExportToken

User = get_user_model()


class ExportTokenSerializerTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='admin', password='Pass123!', role='admin',
        )

    # ------------------------------------------------------------------
    # Valid input
    # ------------------------------------------------------------------

    def test_valid_attendance_type(self):
        serializer = ExportTokenSerializer(data={'data_type': 'attendance'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_payment_type(self):
        serializer = ExportTokenSerializer(data={'data_type': 'payment'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_deduction_type(self):
        serializer = ExportTokenSerializer(data={'data_type': 'deduction'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_with_filters(self):
        data = {'data_type': 'attendance', 'filters': {'date': '2024-01-01'}}
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # ------------------------------------------------------------------
    # Invalid input
    # ------------------------------------------------------------------

    def test_invalid_data_type_rejected(self):
        serializer = ExportTokenSerializer(data={'data_type': 'employees'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('data_type', serializer.errors)

    def test_empty_data_type_rejected(self):
        serializer = ExportTokenSerializer(data={'data_type': ''})
        self.assertFalse(serializer.is_valid())

    # ------------------------------------------------------------------
    # Read-only fields
    # ------------------------------------------------------------------

    def test_token_is_read_only(self):
        """Supplying `token` in input must be silently ignored."""
        data = {'data_type': 'payment', 'token': 'hacked_token_xyz'}
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # validated_data must not contain `token`
        self.assertNotIn('token', serializer.validated_data)

    def test_expires_at_is_read_only(self):
        data = {'data_type': 'deduction', 'expires_at': '2099-01-01T00:00:00Z'}
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('expires_at', serializer.validated_data)

    # ------------------------------------------------------------------
    # Serialization of existing instance
    # ------------------------------------------------------------------

    def test_serializes_existing_token(self):
        token = ExportToken.objects.create(
            user=self.user,
            token='abc123token',
            data_type='attendance',
            filters={'status': 'present'},
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        data = ExportTokenSerializer(token).data
        self.assertEqual(data['token'], 'abc123token')
        self.assertEqual(data['data_type'], 'attendance')
        self.assertIn('expires_at', data)
        self.assertIn('filters', data)

    def test_is_expired_false_for_fresh_token(self):
        token = ExportToken.objects.create(
            user=self.user,
            token='freshtoken',
            data_type='payment',
            filters={},
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        self.assertFalse(token.is_expired())

    def test_is_expired_true_for_old_token(self):
        token = ExportToken.objects.create(
            user=self.user,
            token='oldtoken',
            data_type='deduction',
            filters={},
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.assertTrue(token.is_expired())
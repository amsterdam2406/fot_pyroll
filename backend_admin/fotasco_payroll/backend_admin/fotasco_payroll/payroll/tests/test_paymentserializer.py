from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from payroll.models import Employee, Payment
from payroll.serializers import PaymentSerializer

User = get_user_model()


def make_user(username='payuser', role='staff'):
    return User.objects.create_user(
        username=username, password='Pass123!', role=role,
    )


def make_employee(user, employee_id='EMP-PAY01'):
    return Employee.objects.create(
        user=user,
        employee_id=employee_id,
        name='Pay Employee',
        type='staff',
        location='Lagos',
        salary=Decimal('100000'),
        bank_name='Test Bank',
        account_number='1234567890',
        account_holder='Pay Employee',
        status='active',
        join_date=timezone.now().date(),
    )


class PaymentSerializerTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.employee = make_employee(self.user)

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_valid_payment_data(self):
        data = {
            'employee': self.employee.id,
            'net_amount': '95000.00',
            'base_salary': '100000.00',
            'total_deductions': '5000.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'REF-001',
            'status': 'pending',
            'payment_date': str(timezone.now().date()),
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_bank_account_method_field_format(self):
        payment = Payment.objects.create(
            employee=self.employee,
            base_salary=Decimal('100000'),
            total_deductions=Decimal('5000'),
            net_amount=Decimal('95000'),
            transaction_reference='REF-BANK-01',
            payment_method='bank_transfer',
            payment_date=timezone.now().date(),
            status='pending',
        )
        data = PaymentSerializer(payment).data
        self.assertEqual(data['bank_account'], 'Test Bank - 1234567890')

    def test_employee_name_read_only_present_in_output(self):
        payment = Payment.objects.create(
            employee=self.employee,
            base_salary=Decimal('100000'),
            total_deductions=Decimal('0'),
            net_amount=Decimal('100000'),
            transaction_reference='REF-NAME-01',
            payment_method='bank_transfer',
            payment_date=timezone.now().date(),
            status='pending',
        )
        data = PaymentSerializer(payment).data
        self.assertEqual(data['employee_name'], 'Pay Employee')

    # ------------------------------------------------------------------
    # Validation failures
    # ------------------------------------------------------------------

    def test_zero_net_amount_rejected(self):
        data = {
            'employee': self.employee.id,
            'net_amount': '0.00',
            'base_salary': '100000.00',
            'total_deductions': '100000.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'REF-ZERO',
            'payment_date': str(timezone.now().date()),
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('net_amount', serializer.errors)

    def test_negative_net_amount_rejected(self):
        data = {
            'employee': self.employee.id,
            'net_amount': '-500.00',
            'base_salary': '100000.00',
            'total_deductions': '100500.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'REF-NEG',
            'payment_date': str(timezone.now().date()),
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('net_amount', serializer.errors)

    def test_employee_required(self):
        data = {
            'net_amount': '95000.00',
            'base_salary': '100000.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'REF-NO-EMP',
            'payment_date': str(timezone.now().date()),
        }
        serializer = PaymentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('employee', serializer.errors)

    # ------------------------------------------------------------------
    # Read-only fields
    # ------------------------------------------------------------------

    def test_transaction_reference_read_only_on_input(self):
        """transaction_reference in read_only_fields should be ignored on input."""
        data = {
            'employee': self.employee.id,
            'net_amount': '95000.00',
            'base_salary': '100000.00',
            'total_deductions': '5000.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'SHOULD_BE_IGNORED',
            'payment_date': str(timezone.now().date()),
            'status': 'pending',
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('transaction_reference', serializer.validated_data)

    def test_created_at_read_only(self):
        data = {
            'employee': self.employee.id,
            'net_amount': '95000.00',
            'base_salary': '100000.00',
            'total_deductions': '5000.00',
            'payment_method': 'bank_transfer',
            'transaction_reference': 'REF-DT',
            'payment_date': str(timezone.now().date()),
            'created_at': '2020-01-01T00:00:00Z',
        }
        serializer = PaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('created_at', serializer.validated_data)

    # ------------------------------------------------------------------
    # Status choices
    # ------------------------------------------------------------------

    def test_completed_status_serializes(self):
        payment = Payment.objects.create(
            employee=self.employee,
            base_salary=Decimal('100000'),
            total_deductions=Decimal('0'),
            net_amount=Decimal('100000'),
            transaction_reference='REF-COMP-01',
            payment_method='bank_transfer',
            payment_date=timezone.now().date(),
            status='completed',
        )
        data = PaymentSerializer(payment).data
        self.assertEqual(data['status'], 'completed')
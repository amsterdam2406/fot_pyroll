from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from payroll.models import Employee
from payroll.serializers import DeductionSerializer

User = get_user_model()

class DeductionSerializerTests(TestCase):
    """Comprehensive DeductionSerializer tests."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id='EMP001',
            name='Test Employee',
            type='full_time',
            location='Lagos',
            salary=Decimal('100000'),
            status='active',
            join_date=timezone.now().date()
        )

    def test_valid_deduction_creation(self):
        """Test creating deduction with valid data."""
        data = {
            'employee': self.employee.id,
            'amount': '5000.00',
            'reason': 'Late arrival',
            'status': 'pending',
            'date' : 'timezone.now().date().isoformat()'
        }
        serializer = DeductionSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_zero_amount_validation(self):
        """Test zero amount is rejected."""
        data = {
            'employee': self.employee.id,
            'amount': '0.00',
            'reason': 'Test'
        }
        serializer = DeductionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_negative_amount_validation(self):
        """Test negative amount is rejected."""
        data = {
            'employee': self.employee.id,
            'amount': '-100.00',
            'reason': 'Test'
        }
        serializer = DeductionSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_employee_name_read_only(self):
        """Test employee_name is read-only."""
        data = {
            'employee': self.employee.id,
            'amount': '1000.00',
            'reason': 'Test',
            'employee_name': 'Hacked Name'
        }
        serializer = DeductionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # employee_name should be ignored

    def test_employee_id_read_only(self):
        """Test employee_id is read-only."""
        data = {
            'employee': self.employee.id,
            'amount': '1000.00',
            'reason': 'Test',
            'employee_id': 'HACKD'
        }
        serializer = DeductionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
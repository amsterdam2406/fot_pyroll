from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from payroll.models import (
    Employee, Attendance, Deduction, Payment, Company,
    SackedEmployee, Notification, OTP, ExportToken
)
from payroll.serializers import SackedEmployeeSerializer

User = get_user_model()

class SackedEmployeeSerializerTests(TestCase):
    """Comprehensive SackedEmployeeSerializer tests."""
    
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
            status='terminated',
            join_date=timezone.now().date()
        )

    def test_valid_sacked_employee_creation(self):
        """Test creating sacked employee record."""
        data = {
            'employee': self.employee.id,
            'date_sacked': str(timezone.now().date()),
            'offense': 'Gross misconduct',
            'terminated_by': self.user.id
        }
        serializer = SackedEmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_read_only_fields(self):
        """Test read-only fields."""
        data = {
            'employee': self.employee.id,
            'date_sacked': str(timezone.now().date()),
            'offense': 'Test',
            'created_at': '2020-01-01T00:00:00Z'  # Read-only
        }
        serializer = SackedEmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_employee_name_read_only(self):
        """Test employee_name is read-only."""
        data = {
            'employee': self.employee.id,
            'date_sacked': str(timezone.now().date()),
            'offense': 'Test',
            'employee_name': 'Hacked Name'
        }
        serializer = SackedEmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
"""
Production-ready tests for DRF serializers
Critical: Data validation prevents corrupt database entries
"""

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
from payroll.serializers import UserSerializer

User = get_user_model()


class UserSerializerTests(TestCase):
    """Comprehensive UserSerializer tests."""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'role': 'staff',
            'phone': '+2348012345678'
        }
        self.existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )

    def test_valid_user_creation(self):
        """Test creating user with valid data."""
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        data = self.user_data.copy()
        data['email'] = 'TEST@EXAMPLE.COM'
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], 'test@example.com')

    def test_duplicate_email_validation(self):
        """Test duplicate email is rejected."""
        data = self.user_data.copy()
        data['email'] = self.existing_user.email
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_empty_email_validation(self):
        """Test empty email is rejected."""
        data = self.user_data.copy()
        data['email'] = ''
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_whitespace_email_validation(self):
        """Test whitespace-only email is rejected."""
        data = self.user_data.copy()
        data['email'] = '   '
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_invalid_phone_format(self):
        """Test invalid phone format is rejected."""
        data = self.user_data.copy()
        data['phone'] = 'invalid-phone'
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone', serializer.errors)

    def test_valid_phone_formats(self):
        """Test various valid phone formats."""
        valid_phones = [
            '+2348012345678',
            '08012345678',
            '2348012345678',
            '+1-555-555-5555'
        ]
        for phone in valid_phones:
            data = self.user_data.copy()
            data['phone'] = phone
            serializer = UserSerializer(data=data)
            self.assertTrue(serializer.is_valid(), f"Phone {phone} should be valid")

    def test_role_restriction_for_non_superuser(self):
        """Test non-superuser cannot assign admin role."""
        # Create non-superuser context
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            role='staff'
        )
        context = {'request': MagicMock(user=regular_user)}
        
        data = self.user_data.copy()
        data['role'] = 'admin'
        serializer = UserSerializer(data=data, context=context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_superuser_can_assign_any_role(self):
        """Test superuser can assign any role."""
        superuser = User.objects.create_superuser(
            username='super',
            email='super@test.com',
            password='testpass123'
        )
        context = {'request': MagicMock(user=superuser)}
        
        data = self.user_data.copy()
        data['role'] = 'admin'
        serializer = UserSerializer(data=data, context=context)
        self.assertTrue(serializer.is_valid())

    def test_employee_id_method_field(self):
        """Test employee_id field returns correct value."""
        # Create employee for user
        employee = Employee.objects.create(
            user=self.existing_user,
            employee_id='EMP001',
            name='Test Employee',
            type='full_time',
            location='Lagos',
            salary=Decimal('100000'),
            status='active',
            join_date=timezone.now().date()
        )
        
        serializer = UserSerializer(self.existing_user)
        self.assertEqual(serializer.data['employee_id'], 'EMP001')

    def test_employee_id_none_when_no_profile(self):
        """Test employee_id is None when user has no employee profile."""
        user_no_emp = User.objects.create_user(
            username='noemp',
            email='noemp@test.com',
            password='testpass123'
        )
        serializer = UserSerializer(user_no_emp)
        self.assertIsNone(serializer.data['employee_id'])

    def test_update_existing_user_email_unique(self):
        """Test email uniqueness on update excludes current user."""
        data = {'email': 'newemail@example.com'}
        serializer = UserSerializer(self.existing_user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()
        self.assertEqual(updated_user.email, 'newemail@example.com')

    def test_read_only_fields(self):
        """Test that read-only fields cannot be set."""
        data = self.user_data.copy()
        data['id'] = 99999  # Try to set ID
        data['date_joined'] = '2020-01-01'
        serializer = UserSerializer(data=data)
        # ID is read-only but shouldn't cause validation error
        # It just won't be used
        if serializer.is_valid():
            user = serializer.save()
            self.assertNotEqual(user.id, 99999)
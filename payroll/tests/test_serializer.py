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
from payroll.serializers import (
    UserSerializer, EmployeeSerializer, AttendanceSerializer,
    DeductionSerializer, PaymentSerializer, CompanySerializer,
    SackedEmployeeSerializer, NotificationSerializer, OTPSerializer,
    ExportTokenSerializer
)

User = get_user_model()


# class UserSerializerTests(TestCase):
#     """Comprehensive UserSerializer tests."""
    
#     def setUp(self):
#         self.user_data = {
#             'username': 'testuser',
#             'email': 'test@example.com',
#             'password': 'TestPass123!',
#             'role': 'staff',
#             'phone': '+2348012345678'
#         }
#         self.existing_user = User.objects.create_user(
#             username='existing',
#             email='existing@example.com',
#             password='testpass123'
#         )

#     def test_valid_user_creation(self):
#         """Test creating user with valid data."""
#         serializer = UserSerializer(data=self.user_data)
#         self.assertTrue(serializer.is_valid())
#         user = serializer.save()
#         self.assertEqual(user.email, 'test@example.com')
#         self.assertEqual(user.username, 'testuser')

#     def test_email_normalization(self):
#         """Test email is normalized to lowercase."""
#         data = self.user_data.copy()
#         data['email'] = 'TEST@EXAMPLE.COM'
#         serializer = UserSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         self.assertEqual(serializer.validated_data['email'], 'test@example.com')

#     def test_duplicate_email_validation(self):
#         """Test duplicate email is rejected."""
#         data = self.user_data.copy()
#         data['email'] = self.existing_user.email
#         serializer = UserSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('email', serializer.errors)

#     def test_empty_email_validation(self):
#         """Test empty email is rejected."""
#         data = self.user_data.copy()
#         data['email'] = ''
#         serializer = UserSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('email', serializer.errors)

#     def test_whitespace_email_validation(self):
#         """Test whitespace-only email is rejected."""
#         data = self.user_data.copy()
#         data['email'] = '   '
#         serializer = UserSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_invalid_phone_format(self):
#         """Test invalid phone format is rejected."""
#         data = self.user_data.copy()
#         data['phone'] = 'invalid-phone'
#         serializer = UserSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('phone', serializer.errors)

#     def test_valid_phone_formats(self):
#         """Test various valid phone formats."""
#         valid_phones = [
#             '+2348012345678',
#             '08012345678',
#             '2348012345678',
#             '+1-555-555-5555'
#         ]
#         for phone in valid_phones:
#             data = self.user_data.copy()
#             data['phone'] = phone
#             serializer = UserSerializer(data=data)
#             self.assertTrue(serializer.is_valid(), f"Phone {phone} should be valid")

#     def test_role_restriction_for_non_superuser(self):
#         """Test non-superuser cannot assign admin role."""
#         # Create non-superuser context
#         regular_user = User.objects.create_user(
#             username='regular',
#             email='regular@test.com',
#             password='testpass123',
#             role='staff'
#         )
#         context = {'request': MagicMock(user=regular_user)}
        
#         data = self.user_data.copy()
#         data['role'] = 'admin'
#         serializer = UserSerializer(data=data, context=context)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('role', serializer.errors)

#     def test_superuser_can_assign_any_role(self):
#         """Test superuser can assign any role."""
#         superuser = User.objects.create_superuser(
#             username='super',
#             email='super@test.com',
#             password='testpass123'
#         )
#         context = {'request': MagicMock(user=superuser)}
        
#         data = self.user_data.copy()
#         data['role'] = 'admin'
#         serializer = UserSerializer(data=data, context=context)
#         self.assertTrue(serializer.is_valid())

#     def test_employee_id_method_field(self):
#         """Test employee_id field returns correct value."""
#         # Create employee for user
#         employee = Employee.objects.create(
#             user=self.existing_user,
#             employee_id='EMP001',
#             name='Test Employee',
#             type='full_time',
#             location='Lagos',
#             salary=Decimal('100000'),
#             status='active',
#             join_date=timezone.now().date()
#         )
        
#         serializer = UserSerializer(self.existing_user)
#         self.assertEqual(serializer.data['employee_id'], 'EMP001')

#     def test_employee_id_none_when_no_profile(self):
#         """Test employee_id is None when user has no employee profile."""
#         user_no_emp = User.objects.create_user(
#             username='noemp',
#             email='noemp@test.com',
#             password='testpass123'
#         )
#         serializer = UserSerializer(user_no_emp)
#         self.assertIsNone(serializer.data['employee_id'])

#     def test_update_existing_user_email_unique(self):
#         """Test email uniqueness on update excludes current user."""
#         data = {'email': 'newemail@example.com'}
#         serializer = UserSerializer(self.existing_user, data=data, partial=True)
#         self.assertTrue(serializer.is_valid())
#         updated_user = serializer.save()
#         self.assertEqual(updated_user.email, 'newemail@example.com')

#     def test_read_only_fields(self):
#         """Test that read-only fields cannot be set."""
#         data = self.user_data.copy()
#         data['id'] = 99999  # Try to set ID
#         data['date_joined'] = '2020-01-01'
#         serializer = UserSerializer(data=data)
#         # ID is read-only but shouldn't cause validation error
#         # It just won't be used
#         if serializer.is_valid():
#             user = serializer.save()
#             self.assertNotEqual(user.id, 99999)


# class EmployeeSerializerTests(TestCase):
#     """Comprehensive EmployeeSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
#         self.employee_data = {
#             'employee_id': 'EMP001',
#             'name': 'Test Employee',
#             'type': 'full_time',
#             'location': 'Lagos',
#             'salary': '100000.00',
#             'email': 'employee@company.com',
#             'phone': '08012345678',
#             'bank_name': 'Test Bank',
#             'account_number': '1234567890',
#             'status': 'active',
#             'join_date': str(timezone.now().date())
#         }

#     def test_valid_employee_creation(self):
#         """Test creating employee with valid data."""
#         data = self.employee_data.copy()
#         data['user'] = self.user.id
#         serializer = EmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid(), serializer.errors)
#         employee = serializer.save()
#         self.assertEqual(employee.name, 'Test Employee')

#     def test_user_field_optional(self):
#         """Test that user field is optional (required=False)."""
#         serializer = EmployeeSerializer(data=self.employee_data)
#         self.assertTrue(serializer.is_valid())
#         # User can be set later by view

#     def test_user_null_allowed(self):
#         """Test that user can be explicitly null."""
#         data = self.employee_data.copy()
#         data['user'] = None
#         serializer = EmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_empty_name_validation(self):
#         """Test empty name is rejected."""
#         data = self.employee_data.copy()
#         data['name'] = ''
#         serializer = EmployeeSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('name', serializer.errors)

#     def test_whitespace_name_validation(self):
#         """Test whitespace-only name is rejected."""
#         data = self.employee_data.copy()
#         data['name'] = '   '
#         serializer = EmployeeSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_negative_salary_validation(self):
#         """Test negative salary is rejected."""
#         data = self.employee_data.copy()
#         data['salary'] = '-1000.00'
#         serializer = EmployeeSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('salary', serializer.errors)

#     def test_zero_salary_validation(self):
#         """Test zero salary is allowed (edge case)."""
#         data = self.employee_data.copy()
#         data['salary'] = '0.00'
#         serializer = EmployeeSerializer(data=data)
#         # Zero might be valid for unpaid internships
#         self.assertTrue(serializer.is_valid())

#     def test_read_only_fields(self):
#         """Test that read-only fields are enforced."""
#         data = self.employee_data.copy()
#         data['created_at'] = '2020-01-01T00:00:00Z'
#         data['updated_at'] = '2020-01-01T00:00:00Z'
#         serializer = EmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # Read-only fields should be ignored during creation

#     def test_employee_id_auto_generated(self):
#         """Test that employee_id is auto-generated if not provided."""
#         # This depends on model implementation
#         # If model auto-generates, serializer should handle it
#         pass  # Implementation-specific


# class AttendanceSerializerTests(TestCase):
#     """Comprehensive AttendanceSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='staffuser',
#             email='staff@test.com',
#             password='testpass123',
#             role='staff'
#         )
#         self.employee = Employee.objects.create(
#             user=self.user,
#             employee_id='EMP001',
#             name='Test Employee',
#             type='full_time',
#             location='Lagos',
#             salary=Decimal('100000'),
#             status='active',
#             join_date=timezone.now().date()
#         )
#         self.attendance_data = {
#             'employee': self.employee.id,
#             'date': str(timezone.now().date()),
#             'status': 'present',
#             'clock_in': '09:00:00'
#         }

#     def test_valid_attendance_creation(self):
#         """Test creating attendance with valid data."""
#         serializer = AttendanceSerializer(data=self.attendance_data)
#         self.assertTrue(serializer.is_valid(), serializer.errors)

#     def test_employee_required_validation(self):
#         """Test employee is required."""
#         data = self.attendance_data.copy()
#         del data['employee']
#         serializer = AttendanceSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('employee', serializer.errors)

#     def test_date_required_validation(self):
#         """Test date is required."""
#         data = self.attendance_data.copy()
#         del data['date']
#         serializer = AttendanceSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('date', serializer.errors)

#     def test_duplicate_attendance_validation(self):
#         """Test duplicate attendance for same employee/date is rejected."""
#         # Create existing attendance
#         Attendance.objects.create(
#             employee=self.employee,
#             date=timezone.now().date(),
#             status='present'
#         )
        
#         serializer = AttendanceSerializer(data=self.attendance_data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('non_field_errors', serializer.errors)

#     def test_valid_base64_photo(self):
#         """Test valid base64 photo is accepted."""
#         import base64
#         valid_base64 = base64.b64encode(b'fakeimagedata').decode()
#         data = self.attendance_data.copy()
#         data['clock_in_photo_base64'] = valid_base64
#         serializer = AttendanceSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_invalid_base64_photo(self):
#         """Test invalid base64 photo is rejected."""
#         data = self.attendance_data.copy()
#         data['clock_in_photo_base64'] = 'not-valid-base64!!!'
#         serializer = AttendanceSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('clock_in_photo_base64', str(serializer.errors))

#     def test_clock_out_before_clock_in_validation(self):
#         """Test clock-out before clock-in is rejected."""
#         data = self.attendance_data.copy()
#         data['clock_in'] = '17:00:00'
#         data['clock_out'] = '09:00:00'
#         serializer = AttendanceSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('non_field_errors', serializer.errors)

#     def test_valid_clock_times(self):
#         """Test valid clock-in before clock-out."""
#         data = self.attendance_data.copy()
#         data['clock_in'] = '09:00:00'
#         data['clock_out'] = '17:00:00'
#         serializer = AttendanceSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_update_already_clocked_in(self):
#         """Test updating when already clocked in is rejected."""
#         attendance = Attendance.objects.create(
#             employee=self.employee,
#             date=timezone.now().date(),
#             clock_in='09:00:00',
#             clock_in_timestamp=timezone.now(),
#             status='present'
#         )
        
#         data = {'clock_in': '10:00:00'}
#         serializer = AttendanceSerializer(attendance, data=data, partial=True)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('non_field_errors', serializer.errors)

#     def test_update_already_clocked_out(self):
#         """Test updating when already clocked out is rejected."""
#         attendance = Attendance.objects.create(
#             employee=self.employee,
#             date=timezone.now().date(),
#             clock_in='09:00:00',
#             clock_out='17:00:00',
#             clock_in_timestamp=timezone.now(),
#             clock_out_timestamp=timezone.now(),
#             status='present'
#         )
        
#         data = {'clock_out': '18:00:00'}
#         serializer = AttendanceSerializer(attendance, data=data, partial=True)
#         self.assertFalse(serializer.is_valid())

#     def test_read_only_fields(self):
#         """Test read-only fields cannot be written."""
#         data = self.attendance_data.copy()
#         data['id'] = 99999
#         data['created_at'] = '2020-01-01T00:00:00Z'
#         serializer = AttendanceSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # Read-only fields should be ignored

#     def test_employee_name_read_only(self):
#         """Test employee_name is read-only."""
#         data = self.attendance_data.copy()
#         data['employee_name'] = 'Hacked Name'
#         serializer = AttendanceSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # employee_name should be ignored

#     def test_clock_in_display_format(self):
#         """Test clock_in_display format."""
#         attendance = Attendance.objects.create(
#             employee=self.employee,
#             date=timezone.now().date(),
#             clock_in_timestamp=timezone.now(),
#             status='present'
#         )
#         serializer = AttendanceSerializer(attendance)
#         self.assertIsNotNone(serializer.data['clock_in_display'])
#         # Should be formatted datetime string

#     def test_clock_out_display_none_when_not_clocked_out(self):
#         """Test clock_out_display is None when not clocked out."""
#         attendance = Attendance.objects.create(
#             employee=self.employee,
#             date=timezone.now().date(),
#             clock_in_timestamp=timezone.now(),
#             status='present'
#         )
#         serializer = AttendanceSerializer(attendance)
#         self.assertIsNone(serializer.data['clock_out_display'])


# class DeductionSerializerTests(TestCase):
#     """Comprehensive DeductionSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@test.com',
#             password='testpass123'
#         )
#         self.employee = Employee.objects.create(
#             user=self.user,
#             employee_id='EMP001',
#             name='Test Employee',
#             type='full_time',
#             location='Lagos',
#             salary=Decimal('100000'),
#             status='active',
#             join_date=timezone.now().date()
#         )

#     def test_valid_deduction_creation(self):
#         """Test creating deduction with valid data."""
#         data = {
#             'employee': self.employee.id,
#             'amount': '5000.00',
#             'reason': 'Late arrival',
#             'status': 'pending'
#         }
#         serializer = DeductionSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_zero_amount_validation(self):
#         """Test zero amount is rejected."""
#         data = {
#             'employee': self.employee.id,
#             'amount': '0.00',
#             'reason': 'Test'
#         }
#         serializer = DeductionSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('amount', serializer.errors)

#     def test_negative_amount_validation(self):
#         """Test negative amount is rejected."""
#         data = {
#             'employee': self.employee.id,
#             'amount': '-100.00',
#             'reason': 'Test'
#         }
#         serializer = DeductionSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_employee_name_read_only(self):
#         """Test employee_name is read-only."""
#         data = {
#             'employee': self.employee.id,
#             'amount': '1000.00',
#             'reason': 'Test',
#             'employee_name': 'Hacked Name'
#         }
#         serializer = DeductionSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # employee_name should be ignored

#     def test_employee_id_read_only(self):
#         """Test employee_id is read-only."""
#         data = {
#             'employee': self.employee.id,
#             'amount': '1000.00',
#             'reason': 'Test',
#             'employee_id': 'HACKED'
#         }
#         serializer = DeductionSerializer(data=data)
#         self.assertTrue(serializer.is_valid())


# class PaymentSerializerTests(TestCase):
#     """Comprehensive PaymentSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@test.com',
#             password='testpass123'
#         )
#         self.employee = Employee.objects.create(
#             user=self.user,
#             employee_id='EMP001',
#             name='Test Employee',
#             type='full_time',
#             location='Lagos',
#             salary=Decimal('100000'),
#             bank_name='Test Bank',
#             account_number='1234567890',
#             status='active',
#             join_date=timezone.now().date()
#         )

#     def test_valid_payment_creation(self):
#         """Test creating payment with valid data."""
#         data = {
#             'employee': self.employee.id,
#             'net_amount': '95000.00',
#             'base_salary': '100000.00',
#             'total_deductions': '5000.00',
#             'status': 'pending'
#         }
#         serializer = PaymentSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_zero_net_amount_validation(self):
#         """Test zero net amount is rejected."""
#         data = {
#             'employee': self.employee.id,
#             'net_amount': '0.00',
#             'base_salary': '100000.00',
#             'total_deductions': '100000.00'
#         }
#         serializer = PaymentSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('net_amount', serializer.errors)

#     def test_negative_net_amount_validation(self):
#         """Test negative net amount is rejected."""
#         data = {
#             'employee': self.employee.id,
#             'net_amount': '-1000.00',
#             'base_salary': '100000.00',
#             'total_deductions': '101000.00'
#         }
#         serializer = PaymentSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_employee_required_validation(self):
#         """Test employee is required."""
#         data = {
#             'net_amount': '95000.00',
#             'base_salary': '100000.00'
#         }
#         serializer = PaymentSerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('employee', serializer.errors)

#     def test_bank_account_method_field(self):
#         """Test bank_account field format."""
#         payment = Payment.objects.create(
#             employee=self.employee,
#             base_salary=Decimal('100000'),
#             total_deductions=Decimal('5000'),
#             net_amount=Decimal('95000'),
#             transaction_reference='REF001',
#             payment_date=timezone.now().date(),
#             status='pending'
#         )
#         serializer = PaymentSerializer(payment)
#         self.assertEqual(
#             serializer.data['bank_account'],
#             'Test Bank - 1234567890'
#         )

#     def test_transaction_reference_read_only(self):
#         """Test transaction_reference is read-only."""
#         data = {
#             'employee': self.employee.id,
#             'net_amount': '95000.00',
#             'transaction_reference': 'HACKED_REF'
#         }
#         serializer = PaymentSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # transaction_reference should be ignored


# class CompanySerializerTests(TestCase):
#     """Comprehensive CompanySerializer tests."""
    
#     def test_valid_company_creation(self):
#         """Test creating company with valid data."""
#         data = {
#             'name': 'Test Company Ltd',
#             'address': '123 Test Street',
#             'contact_email': 'contact@testcompany.com'
#         }
#         serializer = CompanySerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_empty_name_validation(self):
#         """Test empty company name is rejected."""
#         data = {
#             'name': '',
#             'address': '123 Test Street'
#         }
#         serializer = CompanySerializer(data=data)
#         self.assertFalse(serializer.is_valid())
#         self.assertIn('name', serializer.errors)

#     def test_whitespace_name_validation(self):
#         """Test whitespace-only name is rejected."""
#         data = {
#             'name': '   ',
#             'address': '123 Test Street'
#         }
#         serializer = CompanySerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_read_only_fields(self):
#         """Test read-only fields are enforced."""
#         data = {
#             'name': 'Test Company',
#             'total_payment_to_guards': '999999.00',  # Read-only
#             'profit': '999999.00',  # Read-only
#             'created_at': '2020-01-01T00:00:00Z'  # Read-only
#         }
#         serializer = CompanySerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # Read-only fields should be ignored


# class SackedEmployeeSerializerTests(TestCase):
#     """Comprehensive SackedEmployeeSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@test.com',
#             password='testpass123'
#         )
#         self.employee = Employee.objects.create(
#             user=self.user,
#             employee_id='EMP001',
#             name='Test Employee',
#             type='full_time',
#             location='Lagos',
#             salary=Decimal('100000'),
#             status='terminated',
#             join_date=timezone.now().date()
#         )

#     def test_valid_sacked_employee_creation(self):
#         """Test creating sacked employee record."""
#         data = {
#             'employee': self.employee.id,
#             'date_sacked': str(timezone.now().date()),
#             'offense': 'Gross misconduct',
#             'terminated_by': self.user.id
#         }
#         serializer = SackedEmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_read_only_fields(self):
#         """Test read-only fields."""
#         data = {
#             'employee': self.employee.id,
#             'date_sacked': str(timezone.now().date()),
#             'offense': 'Test',
#             'created_at': '2020-01-01T00:00:00Z'  # Read-only
#         }
#         serializer = SackedEmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_employee_name_read_only(self):
#         """Test employee_name is read-only."""
#         data = {
#             'employee': self.employee.id,
#             'date_sacked': str(timezone.now().date()),
#             'offense': 'Test',
#             'employee_name': 'Hacked Name'
#         }
#         serializer = SackedEmployeeSerializer(data=data)
#         self.assertTrue(serializer.is_valid())


# class NotificationSerializerTests(TestCase):
#     """Comprehensive NotificationSerializer tests."""
    
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@test.com',
#             password='testpass123'
#         )

#     def test_valid_notification_creation(self):
#         """Test creating notification."""
#         data = {
#             'user': self.user.id,
#             'message': 'Test notification message',
#             'type': 'info',
#             'is_read': False
#         }
#         serializer = NotificationSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_read_only_created_at(self):
#         """Test created_at is read-only."""
#         data = {
#             'user': self.user.id,
#             'message': 'Test',
#             'created_at': '2020-01-01T00:00:00Z'
#         }
#         serializer = NotificationSerializer(data=data)
#         self.assertTrue(serializer.is_valid())


# class OTPSerializerTests(TestCase):
#     """Comprehensive OTPSerializer tests."""
    
#     def test_valid_otp_serialization(self):
#         """Test OTP serialization."""
#         otp = OTP.objects.create(
#             email='test@example.com',
#             code='123456',
#             reference='REF001',
#             expires_at=timezone.now() + timedelta(minutes=5)
#         )
#         serializer = OTPSerializer(otp)
#         self.assertEqual(serializer.data['email'], 'test@example.com')
#         self.assertEqual(serializer.data['code'], '123456')

#     def test_email_normalization(self):
#         """Test email is normalized to lowercase."""
#         data = {'email': 'TEST@EXAMPLE.COM'}
#         serializer = OTPSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         self.assertEqual(serializer.validated_data['email'], 'test@example.com')

#     def test_empty_email_validation(self):
#         """Test empty email is rejected."""
#         data = {'email': ''}
#         serializer = OTPSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_whitespace_email_validation(self):
#         """Test whitespace-only email is rejected."""
#         data = {'email': '   '}
#         serializer = OTPSerializer(data=data)
#         self.assertFalse(serializer.is_valid())

#     def test_code_read_only(self):
#         """Test code is read-only."""
#         data = {'email': 'test@example.com', 'code': '999999'}
#         serializer = OTPSerializer(data=data)
#         self.assertTrue(serializer.is_valid())
#         # code should be ignored (auto-generated)

#     def test_expires_at_read_only(self):
#         """Test expires_at is read-only."""
#         data = {
#             'email': 'test@example.com',
#             'expires_at': '2025-01-01T00:00:00Z'
#         }
#         serializer = OTPSerializer(data=data)
#         self.assertTrue(serializer.is_valid())

#     def test_validate_expired_otp(self):
#         """Test validation of expired OTP."""
#         expired_otp = OTP.objects.create(
#             email='test@example.com',
#             code='123456',
#             reference='REF001',
#             expires_at=timezone.now() - timedelta(minutes=1)  # Expired
#         )
#         serializer = OTPSerializer(expired_otp, data={'email': 'test@example.com'})
#         # The validate method checks expiration
#         # This depends on implementation details


class ExportTokenSerializerTests(TestCase):
    """Comprehensive ExportTokenSerializer tests."""
    
    def test_valid_export_token_creation(self):
        """Test creating export token."""
        data = {
            'data_type': 'attendance',
            'filters': {'date': '2024-01-01'}
        }
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_data_type(self):
        """Test invalid data_type is rejected."""
        data = {'data_type': 'invalid_type'}
        serializer = ExportTokenSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('data_type', serializer.errors)

    def test_valid_data_types(self):
        """Test all valid data types."""
        valid_types = ['attendance', 'payment', 'deduction']
        for dt in valid_types:
            data = {'data_type': dt}
            serializer = ExportTokenSerializer(data=data)
            self.assertTrue(serializer.is_valid(), f"Data type {dt} should be valid")

    def test_token_read_only(self):
        """Test token is read-only."""
        data = {
            'token': 'hacked_token_123',
            'data_type': 'attendance'
        }
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # token should be ignored (auto-generated)

    def test_expires_at_read_only(self):
        """Test expires_at is read-only."""
        data = {
            'data_type': 'attendance',
            'expires_at': '2025-01-01T00:00:00Z'
        }
        serializer = ExportTokenSerializer(data=data)
        self.assertTrue(serializer.is_valid())
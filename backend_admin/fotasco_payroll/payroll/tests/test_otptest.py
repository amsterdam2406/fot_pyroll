from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status
from payroll.models import Employee, Attendance, Deduction, Payment, OTP, ExportToken, Notification
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import base64
from unittest.mock import patch
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from payroll.models import Employee
from unittest.mock import patch


User = get_user_model()

class OTPTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='admin', password='admin123', role='admin')
        self.employee = Employee.objects.create(
            user=self.user,
            name='Test Employee',
            type='staff',
            location='Test',
            salary=50000,
            bank_name='GTBank',
            account_number='0123456789',
            account_holder='Test Employee',
            join_date=timezone.now().date()
        )
        self.client.force_authenticate(user=self.user)
    
    def test_otp_creation(self):
        otp = OTP.objects.create(
            email='test@example.com',
            code='123456',
            reference='test_ref',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        self.assertFalse(otp.has_expired())
        self.assertEqual(otp.code, '123456')
    
    def test_otp_expiration(self):
        otp = OTP.objects.create(
            email='test@example.com',
            code='123456',
            reference='test_ref',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(otp.has_expired())
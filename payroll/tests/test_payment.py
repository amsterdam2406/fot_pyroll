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

class PaymentTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='admin', password='admin123', role='admin', is_payment_admin=True)
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
    
    def test_payment_creation(self):
        payment = Payment.objects.create(
            employee=self.employee,
            base_salary=50000,
            total_deductions=0,
            net_amount=50000,
            transaction_reference='test_ref_123',
            payment_date='2024-01-01'
        )
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.net_amount, 50000)
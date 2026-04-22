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

class ExportTokenTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='admin', password='admin123', role='admin')
        self.client.force_authenticate(user=self.user)
    
    def test_export_token_creation(self):
        token = ExportToken.objects.create(
            user=self.user,
            token='test_token_123',
            data_type='employees',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        self.assertFalse(token.is_expired())
        self.assertFalse(token.is_used)
        self.assertEqual(token.data_type, 'employees')
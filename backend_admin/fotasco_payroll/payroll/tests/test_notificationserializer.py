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
from payroll.serializers import NotificationSerializer

User = get_user_model()

class NotificationSerializerTests(TestCase):
    """Comprehensive NotificationSerializer tests."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_valid_notification_creation(self):
        """Test creating notification."""
        data = {
            'user': self.user.id,
            'message': 'Test notification message',
            'type': 'info',
            'is_read': False
        }
        serializer = NotificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_read_only_created_at(self):
        """Test created_at is read-only."""
        data = {
            'user': self.user.id,
            'message': 'Test',
            'created_at': '2020-01-01T00:00:00Z'
        }
        serializer = NotificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
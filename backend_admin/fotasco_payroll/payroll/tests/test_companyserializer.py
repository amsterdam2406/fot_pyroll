from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from payroll.serializers import CompanySerializer

User = get_user_model()

class CompanySerializerTests(TestCase):
    """Comprehensive CompanySerializer tests."""
    
    def test_valid_company_creation(self):
        """Test creating company with valid data."""
        data = {
            'name': 'Test Company Ltd',
            'address': '123 Test Street',
            'contact_email': 'contact@testcompany.com',
            'location': 'Lagos',
            'guards_count': 10,
            'payment_to_us': '100000',
            'payment_per_guard': '10000'
        }
        serializer = CompanySerializer(data=data)
        if not serializer.is_valid():
            print("COMPANY ERRORS:", serializer.errors)
        self.assertTrue(serializer.is_valid())

    def test_empty_name_validation(self):
        """Test empty company name is rejected."""
        data = {
            'name': '',
            'address': '123 Test Street',
            'location': 'Lagos',
            'guards_count': 1,
            'payment_to_us': '1000',
            'payment_per_guard': '100'
        }
        serializer = CompanySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_whitespace_name_validation(self):
        """Test whitespace-only name is rejected."""
        data = {
            'name': '   ',
            'address': '123 Test Street',
            'location': 'Lagos',
            'guards_count': 1,
            'payment_to_us': '1000',
            'payment_per_guard': '100'
        }
        serializer = CompanySerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_read_only_fields(self):
        """Test read-only fields are enforced."""
        data = {
            'name': 'Test Company',
            'location': 'Lagos',
            'guards_count': 1,
            'payment_to_us': '1000',
            'payment_per_guard': '100',
            'total_payment_to_guards': '999999.00',  # Read-only
            'profit': '999999.00',  # Read-only
            'created_at': '2020-01-01T00:00:00Z'  # Read-only
        }
        serializer = CompanySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # Read-only fields should be ignored
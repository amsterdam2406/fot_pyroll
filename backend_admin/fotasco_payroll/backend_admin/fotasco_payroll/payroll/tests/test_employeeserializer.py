from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from payroll.models import Employee
from payroll.serializers import EmployeeSerializer

User = get_user_model()


class EmployeeSerializerTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='Pass123!',
        )
        # Base valid data — employee_id is read_only so intentionally omitted
        self.valid_data = {
            'name': 'Test Employee',
            'type': 'staff',           # must be 'staff' or 'guard'
            'location': 'Lagos',
            'salary': '100000.00',
            'bank_name': 'GTBank',
            'account_number': '1234567890',
            'account_holder': 'Test Employee',
            'status': 'active',
            'join_date': str(timezone.now().date()),
        }

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_valid_with_user(self):
        data = {**self.valid_data, 'user': self.user.id}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        emp = serializer.save()
        self.assertEqual(emp.name, 'Test Employee')
        self.assertEqual(emp.user, self.user)

    def test_user_field_is_optional(self):
        """user is required=False — omitting it must still be valid."""
        serializer = EmployeeSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_user_can_be_null(self):
        data = {**self.valid_data, 'user': None}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_guard_type_valid(self):
        data = {**self.valid_data, 'type': 'guard'}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_zero_salary_is_allowed(self):
        data = {**self.valid_data, 'salary': '0.00'}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # ------------------------------------------------------------------
    # Validation failures
    # ------------------------------------------------------------------

    def test_empty_name_rejected(self):
        data = {**self.valid_data, 'name': ''}
        serializer = EmployeeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_whitespace_name_rejected(self):
        data = {**self.valid_data, 'name': '   '}
        serializer = EmployeeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_negative_salary_rejected(self):
        data = {**self.valid_data, 'salary': '-1000.00'}
        serializer = EmployeeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('salary', serializer.errors)

    # ------------------------------------------------------------------
    # Read-only fields
    # ------------------------------------------------------------------

    def test_employee_id_is_read_only(self):
        """Supplying employee_id in input must be silently ignored."""
        data = {**self.valid_data, 'employee_id': 'HACKED001'}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('employee_id', serializer.validated_data)

    def test_created_at_is_read_only(self):
        data = {**self.valid_data, 'created_at': '2020-01-01T00:00:00Z'}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('created_at', serializer.validated_data)

    def test_updated_at_is_read_only(self):
        data = {**self.valid_data, 'updated_at': '2020-01-01T00:00:00Z'}
        serializer = EmployeeSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('updated_at', serializer.validated_data)

    # ------------------------------------------------------------------
    # Serialization of existing instance
    # ------------------------------------------------------------------

    def test_serializes_existing_employee(self):
        emp = Employee.objects.create(
            user=self.user,
            name='Serialized Employee',
            type='guard',
            location='Abuja',
            salary=Decimal('60000'),
            bank_name='UBA',
            account_number='0987654321',
            account_holder='Serialized Employee',
            status='active',
            join_date=timezone.now().date(),
        )
        data = EmployeeSerializer(emp).data
        self.assertEqual(data['name'], 'Serialized Employee')
        self.assertIn('employee_id', data)
        self.assertIsNotNone(data['employee_id'])
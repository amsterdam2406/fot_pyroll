from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from payroll.models import Employee, Attendance
from payroll.serializers import AttendanceSerializer, CompanySerializer
import base64

User = get_user_model()


def make_user(username='staffuser', role='staff'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='testpass123',
        role=role,
    )


def make_employee(user, employee_id='EMP001'):
    """Create a minimal valid Employee instance."""
    return Employee.objects.create(
        user=user,
        employee_id=employee_id,
        name='Test Employee',
        type='staff',            # must match TYPE_CHOICES
        location='Lagos',
        salary=Decimal('100000'),
        bank_name='GTBank',
        account_number='1234567890',
        account_holder='Test Employee',
        status='active',
        join_date=timezone.now().date(),
    )


class AttendanceSerializerTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.employee = make_employee(self.user)
        self.valid_data = {
            'employee': self.employee.id,
            'date': str(timezone.now().date()),
            'status': 'present',
            'clock_in': '09:00:00',
        }

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_valid_attendance_creation(self):
        serializer = AttendanceSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_clock_times(self):
        data = {**self.valid_data, 'clock_in': '09:00:00', 'clock_out': '17:00:00'}
        serializer = AttendanceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_base64_photo_accepted(self):
        valid_b64 = base64.b64encode(b'fakeimagedata').decode()
        data = {**self.valid_data, 'clock_in_photo_base64': valid_b64}
        serializer = AttendanceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_read_only_fields_ignored_on_input(self):
        data = {**self.valid_data, 'id': 99999, 'created_at': '2020-01-01T00:00:00Z'}
        serializer = AttendanceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_employee_name_read_only_ignored(self):
        data = {**self.valid_data, 'employee_name': 'Hacked'}
        serializer = AttendanceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    # ------------------------------------------------------------------
    # Required-field validation
    # ------------------------------------------------------------------

    def test_employee_required(self):
        data = {**self.valid_data}
        del data['employee']
        serializer = AttendanceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('employee', serializer.errors)

    def test_date_required(self):
        data = {**self.valid_data}
        del data['date']
        serializer = AttendanceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('date', serializer.errors)

    # ------------------------------------------------------------------
    # Business-rule validation
    # ------------------------------------------------------------------

    def test_duplicate_attendance_rejected(self):
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            status='present',
        )
        serializer = AttendanceSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_invalid_base64_photo_rejected(self):
        data = {**self.valid_data, 'clock_in_photo_base64': 'not-valid-base64!!!'}
        serializer = AttendanceSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_clock_out_before_clock_in_rejected(self):
        data = {**self.valid_data, 'clock_in': '17:00:00', 'clock_out': '09:00:00'}
        serializer = AttendanceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    # ------------------------------------------------------------------
    # Update (partial) validation
    # ------------------------------------------------------------------

    def test_update_already_clocked_in_rejected(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            clock_in='09:00:00',
            clock_in_timestamp=timezone.now(),
            status='present',
        )
        serializer = AttendanceSerializer(attendance, data={'clock_in': '10:00:00'}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_update_already_clocked_out_rejected(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            clock_in='09:00:00',
            clock_out='17:00:00',
            clock_in_timestamp=timezone.now(),
            clock_out_timestamp=timezone.now(),
            status='present',
        )
        serializer = AttendanceSerializer(attendance, data={'clock_out': '18:00:00'}, partial=True)
        self.assertFalse(serializer.is_valid())

    # ------------------------------------------------------------------
    # Display / SerializerMethodField
    # ------------------------------------------------------------------

    def test_clock_in_display_format(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            clock_in_timestamp=timezone.now(),
            status='present',
        )
        data = AttendanceSerializer(attendance).data
        self.assertIsNotNone(data['clock_in_display'])
        # Should be 'YYYY-MM-DD HH:MM:SS'
        self.assertRegex(data['clock_in_display'], r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')

    def test_clock_out_display_none_when_not_clocked_out(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            clock_in_timestamp=timezone.now(),
            status='present',
        )
        data = AttendanceSerializer(attendance).data
        self.assertIsNone(data['clock_out_display'])

    def test_clock_out_display_populated_after_clock_out(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            clock_in_timestamp=timezone.now(),
            clock_out_timestamp=timezone.now(),
            status='present',
        )
        data = AttendanceSerializer(attendance).data
        self.assertIsNotNone(data['clock_out_display'])
        
    def test_valid_company_creation(self):
        data = {
            'name': 'Test Company Ltd',
            'address': '123 Test Street',
            'contact_email': 'contact@testcompany.com'     
        }
        serializer = CompanySerializer(data=data)
        if not serializer.is_valid():
            print("ERRORS:", serializer.errors)  # ADD THIS
        self.assertTrue(serializer.is_valid())
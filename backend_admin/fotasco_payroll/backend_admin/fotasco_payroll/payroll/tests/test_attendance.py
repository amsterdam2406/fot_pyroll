from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from payroll.models import Employee, Attendance, Deduction, Notification
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

User = get_user_model()

class AttendanceViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.admin = User.objects.create_user(
            username="admin1",
            password="pass123",
            role="admin",
            is_staff=True
        )
        self.staff = User.objects.create_user(
            username="staff1",
            password="pass123",
            role="staff"
        )

        # Employees
        self.admin_employee = Employee.objects.create(
            user=self.admin,
            name='Admin Employee',
            type='staff',
            location='Test',
            salary=50000,
            bank_name='TestBank',
            account_number='1234567890',
            account_holder='Admin Employee',
            join_date=timezone.now().date()
        )

        self.staff_employee = Employee.objects.create(
            user=self.staff,
            name='Staff Employee',
            type='staff',
            location='Test',
            salary=30000,
            bank_name='TestBank',
            account_number='0987654321',
            account_holder='Staff Employee',
            join_date=timezone.now().date()
        )

        # Attendance (fresh per test)
        self.admin_attendance = Attendance.objects.create(
            employee=self.admin_employee,
            date=timezone.now().date(),
            status='present'
        )

        # Test image
        self.valid_photo = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD..."

    @patch('payroll.views.AttendanceViewSet._decode_photo')
    def test_clock_in_with_valid_photo(self, mock_decode):
        """Test successful clock-in with valid photo."""
        mock_decode.return_value = ('jpg', b'fake_image_data')
        self.client.force_authenticate(user=self.staff)
        
        response = self.client.post('/api/attendance/clock_in_with_photo/', {
            'photo': self.valid_photo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Clocked in successfully')
        self.assertEqual(response.data['status'], 'present')
        
        # Verify attendance record
        attendance = Attendance.objects.get(employee=self.staff_employee, date=timezone.now().date())
        self.assertIsNotNone(attendance.clock_in_timestamp)
        self.assertTrue(attendance.clock_in_photo)
        self.assertEqual(attendance.status, 'present')
        mock_decode.assert_called_once()

    @patch('payroll.views.AttendanceViewSet._decode_photo')
    def test_clock_in_already_clocked(self, mock_decode):
        """Already clocked in today - should fail."""
        mock_decode.return_value = ('jpg', b'fake_image_data')
        self.client.force_authenticate(user=self.staff)
        
        # Pre-create attendance
        Attendance.objects.create(
            employee=self.staff_employee,
            date=timezone.now().date(),
        clock_in_timestamp=timezone.now()
    )
        
        response = self.client.post('/api/attendance/clock_in_with_photo/', {
            'photo': self.valid_photo
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Already clocked in today')

    def test_clock_in_no_photo_fails(self):
        """No photo provided."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/attendance/clock_in_with_photo/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Already clocked in today')

    @patch('payroll.views.AttendanceViewSet._decode_photo')
    def test_clock_in_invalid_photo_format(self, mock_decode):
        """Invalid base64 photo."""
        mock_decode.side_effect = ValueError("Invalid photo format")
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/attendance/clock_in_with_photo/', {
            'photo': 'invalid'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid photo format', response.data['error'])

    @patch('payroll.views.AttendanceViewSet._decode_photo')
    def test_clock_out_with_valid_photo(self, mock_decode):
        """Successful clock-out."""
        mock_decode.return_value = ('jpg', b'fake_image_data')
        self.client.force_authenticate(user=self.staff)
        
        # First clock in
        self.client.post('/api/attendance/clock_in_with_photo/', {'photo': self.valid_photo})
        
        response = self.client.post('/api/attendance/clock_out_with_photo/', {
            'photo': self.valid_photo
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Clocked out successfully')
        
        attendance = Attendance.objects.get(employee=self.staff_employee, date=timezone.now().date())
        self.assertIsNotNone(attendance.clock_out_timestamp)
        self.assertTrue(attendance.clock_out_photo)

    def test_clock_out_no_clockin_fails(self):
        """No prior clock-in."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/attendance/clock_out_with_photo/', {'photo': self.valid_photo})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['error'], 'No clock-in record found for today')

    def test_process_absence_deductions_not_admin(self):
        """Non-admin can't process deductions."""
        non_admin_user = User.objects.create_user(
            username="nonadmin",
            password="pass123",
            role="staff"
        )
        self.client.force_authenticate(user=non_admin_user)
        response = self.client.post('/api/attendance/process_absence_deductions/')
        self.assertEqual(response.status_code, 403)

    def test_get_queryset_admin_sees_all(self):
        """Admin sees all attendances."""
        self.client.force_authenticate(user=self.admin)
        
        # Create absences (3+ consecutive weekdays)
        today = timezone.now().date()
        absence_dates = [today - timedelta(days=i) for i in range(5) if (today - timedelta(days=i)).weekday() < 5]
        for date in absence_dates:
            Attendance.objects.get_or_create(employee=self.staff_employee, date=date, defaults={'status': 'absent'})
        
        response = self.client.post('/api/attendance/process_absence_deductions/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('deductions', response.data)
        self.assertEqual(len(response.data['deductions']), 1)  # One employee
        
        # Verify deduction created
        deduction = Deduction.objects.get(employee=self.staff_employee)
        self.assertEqual(deduction.status, 'pending')
        self.assertIn('consecutive days absent', deduction.reason)

    def test_process_absence_deductions_not_admin(self):
        """Non-admin can't process deductions."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.post('/api/attendance/process_absence_deductions/')
        self.assertEqual(response.status_code, 403)

    def test_get_queryset_admin_sees_all(self):
        """Admin sees all attendances."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/attendance/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  # admin_attendance

    def test_get_queryset_staff_sees_own(self):
        """Staff sees only own attendances."""
        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/api/attendance/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)  # No staff attendance yet

    def test_permissions_not_authenticated(self):
        """Unauthenticated access denied."""
        response = self.client.get('/api/attendance/')
        self.assertEqual(response.status_code, 401)

    @patch('payroll.views.logger.info')
    def test_logging_clock_in(self, mock_logger):
        """Verify logging works."""
        with patch('payroll.views.AttendanceViewSet._decode_photo') as mock_decode:
            mock_decode.return_value = ('jpg', b'data')
            self.client.force_authenticate(user=self.staff)
            self.client.post('/api/attendance/clock_in_with_photo/', {'photo': self.valid_photo})
            mock_logger.assert_called_once()

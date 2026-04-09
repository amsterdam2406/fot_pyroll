from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from payroll.models import Employee, Notification
from django.utils import timezone
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken
from payroll.models import Employee

User = get_user_model()


class EmployeeTestCase(APITestCase):

    def setUp(self):
        # Staff user — owns self.employee
        self.user = User.objects.create_user(
            username='staffuser',
            password='password123',
            role='staff'
        )

        # Admin user — used for admin-only endpoints.
        # NOT linked to any Employee so perform_create(user=request.user)
        # never hits a unique-user_id conflict inside these tests.
        self.admin = User.objects.create_user(
            username='admin',
            password='password123',
            role='admin',
            is_employee_admin=True,
            is_staff=True,
            is_superuser=True,
        )

        # Employee for self.user — has email so initiate_payment won't 400
        self.employee = Employee.objects.create(
            user=self.user,
            name='Test Employee',
            employee_id='FSS001STAFF',
            type='staff',
            location='Lagos',
            salary=40000,
            email='testemployee@example.com',   # FIX: required by initiate_payment
            bank_name='UBA',
            account_number='1234567890',
            account_holder='Test Employee',
            status='active',
            join_date=timezone.now().date()
        )

        self.client.force_authenticate(user=self.user)

    # ------------------------------------------------------------------
    # CREATE EMPLOYEE
    # ------------------------------------------------------------------
    def test_create_employee(self):
        """
        FIX: perform_create() forces user=request.user, so we must POST as a
        user that does NOT already own an Employee (unique user_id constraint).
        Create a fresh user specifically for this test.
        """
        new_user = User.objects.create_user(
            username='admin_for_create',
            password='password123',
            role='admin',
            is_employee_admin=True,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=new_user)
        data = {
            'name': 'New Employee',
            'type': 'staff',
            'location': 'Abuja',
            'salary': 50000,
            'bank_name': 'GTBank',
            'account_number': '0123456789',
            'account_holder': 'New Employee',
            'join_date': str(timezone.now().date()),
        }
        response = self.client.post('/api/employees/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # EMPLOYEE ID AUTO-GENERATION
    # ------------------------------------------------------------------
    def test_employee_id_generation(self):
        """
        FIX: always use a fresh user — Employee.user_id is unique,
        so reusing self.user would raise IntegrityError.
        """
        new_user = User.objects.create_user(
            username='staffuser2',
            password='password123',
            role='staff'
        )
        employee = Employee.objects.create(
            user=new_user,
            name='Test Staff',
            type='staff',
            location='Test',
            salary=50000,
            bank_name='GTBank',
            account_number='0123456789',
            account_holder='Test Staff',
            join_date=timezone.now().date()
        )
        self.assertTrue(employee.employee_id.startswith('FSS'))
        self.assertTrue(employee.employee_id.endswith('Staff'))

    # ------------------------------------------------------------------
    # TERMINATE
    # ------------------------------------------------------------------
    def test_terminate_employee(self):
        self.client.force_authenticate(user=self.admin)
        # Use a separate user so admin's user_id stays free
        target_user = User.objects.create_user(
            username='target_staff',
            password='password123',
            role='staff'
        )
        employee = Employee.objects.create(
            name="Terminate Me",
            employee_id="EMP002",
            salary=40000,
            type="staff",
            location="Lagos",
            bank_name="UBA",
            account_number="1234567890",
            account_holder="Terminate Me",
            status="active",
            user=target_user,
            join_date=timezone.now().date()
        )
        url = f"/api/employees/{employee.id}/terminate/"
        response = self.client.post(url, {"offense": "Misconduct"})
        employee.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(employee.status, "terminated")
        self.assertEqual(Notification.objects.count(), 1)

    # ------------------------------------------------------------------
    # CLOCK IN
    # ------------------------------------------------------------------
    def test_clock_in_without_photo(self):
        response = self.client.post("/api/attendance/clock_in_with_photo/", {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Photo is required", str(response.data))

    def test_clock_in_no_employee(self):
        Employee.objects.all().delete()
        response = self.client.post("/api/attendance/clock_in_with_photo/", {
            "photo": "data:image/png;base64,abc123"
        })
        self.assertEqual(response.status_code, 404)

    def test_clock_in_success(self):
        response = self.client.post("/api/attendance/clock_in_with_photo/", {
            "photo": "data:image/png;base64,aGVsbG8="
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Clocked in successfully", str(response.data))


    @patch("payroll.views.PaystackAPI.initialize_transaction")
    def test_initiate_payment(self, mock_paystack):
        """
        FIX 1: authenticate as admin (IsPayrollAdmin + IsAdmin required).
        FIX 2: employee must have an email — the view returns 400 without one.
        FIX 3: pass employee UUID primary key (the view does Employee.objects.get(id=...)).
        """
        self.client.force_authenticate(user=self.admin)
        mock_paystack.return_value = {
            "status": True,
            "data": {"authorization_url": "http://test"}
        }
        response = self.client.post("/api/payments/initiate_payment/", {
            "employee_id": str(self.employee.id)   # UUID primary key, not employee_id string
        })
        self.assertEqual(response.status_code, 200)
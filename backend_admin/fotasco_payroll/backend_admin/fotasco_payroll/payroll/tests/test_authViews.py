from rest_framework.test import APITestCase
from rest_framework import status
from payroll.models import Employee
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthViewsTests(APITestCase):

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='password123',
            role='staff'
        )

        # Superuser — the only role allowed to register another admin
        # (register_view explicitly blocks admin-creating-admin)
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            password='superpass123',
        )
        # A plain admin — can register staff/guard but NOT another admin
        self.admin_user = User.objects.create_user(
            username='adminuser',
            password='adminpass123',
            role='admin',
            is_staff=True,
            is_employee_admin=True,
        )

        self.staff_employee = Employee.objects.create(
            user=self.staff_user,
            name="Test Staff",
            employee_id="EMP001",
            type="staff",
            location="Lagos",
            salary=50000,
            bank_name="GTBank",
            account_number="1234567890",
            account_holder="Test Staff",
            join_date=timezone.now().date()
        )

    def test_login_success(self):
        url = reverse('api-login')
        data = {'username': 'staffuser', 'password': 'password123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['username'], 'staffuser')
        self.assertEqual(response.data['user']['employee_id'], self.staff_employee.employee_id)
        self.assertIn('refresh_token', response.cookies)

    def test_login_invalid_credentials(self):
        url = reverse('api-login')
        data = {'username': 'staffuser', 'password': 'WrongPass!'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_login_missing_fields(self):
        url = reverse('api-login')
        data = {'username': 'staffuser'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_register_admin_by_superuser(self):
        """
        FIX: register_view explicitly returns 403 when a non-superuser admin
        tries to create another admin.  Only a superuser can do this.
        """
        self.client.force_authenticate(user=self.superuser)
        url = reverse('api-register')
        data = {
            'username': 'newadmin',
            'password': 'AdminNewPass123!',
            'role': 'admin',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'newadmin')

    def test_register_staff_by_admin_missing_employee_fields(self):
        """
        An admin registering a staff user must supply employee fields
        (salary, location, bank_name, account_number, account_holder).
        Omitting them must return 400.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('api-register')
        # role='staff' but no salary/location/bank fields → should fail
        data = {
            'username': 'newstaff',
            'password': 'StaffPass123!',
            'role': 'staff',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_register_staff_by_admin_success(self):
        """Happy-path: admin registers a fully-specified staff user."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('api-register')
        data = {
            'username': 'newstaff2',
            'password': 'StaffPass123!',
            'role': 'staff',
            'salary': 45000,
            'location': 'Lagos',
            'bank_name': 'GTBank',
            'account_number': '9876543210',
            'account_holder': 'New Staff',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_verify_password_correct(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('verify_password')
        data = {'password': 'password123'}   # must match setUp password
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_verify_password_incorrect(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('verify_password')
        data = {'password': 'WrongPass123!'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['valid'])

    def test_logout(self):
        self.client.force_authenticate(user=self.staff_user)
        refresh = RefreshToken.for_user(self.staff_user)
        self.client.cookies['refresh_token'] = str(refresh)
        url = reverse('api-logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies['refresh_token'].value, '')
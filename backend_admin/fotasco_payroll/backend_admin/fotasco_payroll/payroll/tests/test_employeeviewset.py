import uuid
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from payroll.models import Employee, Notification, SackedEmployee


User = get_user_model()

def make_employee(user, suffix='', salary=50000, employee_id=None):
    return Employee.objects.create(
        user=user,
        name=f'Employee {suffix}',
        employee_id=employee_id or f'EMP-{uuid.uuid4().hex[:6]}',
        type='staff',
        location='Lagos',
        salary=salary,
        bank_name='GTBank',
        account_number='0123456789',
        account_holder=f'Employee {suffix}',
        email=f'emp{suffix}@test.com',
        status='active',
        join_date=timezone.now().date(),
    )



class EmployeeViewSetPermissionTests(APITestCase):
    """Cover all permission branches in EmployeeViewSet."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='Pass123!', role='admin',
            is_employee_admin=True, is_staff=True, is_superuser=True,
        )
        self.staff_user = User.objects.create_user(
            username='staff1', password='Pass123!', role='staff',
        )
        self.staff_employee = make_employee(self.staff_user, suffix='s1')

    # ------------------------------------------------------------------
    # LIST / RETRIEVE
    # ------------------------------------------------------------------

    def test_admin_sees_all_employees(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_sees_only_own_employee(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get('/api/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [e['id'] for e in response.data['results']]
        self.assertIn(str(self.staff_employee.id), ids)

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def test_admin_can_create_employee(self):
        """Admin POST with no `user` field — perform_create injects admin as user."""
        # Admin has no employee yet; create will succeed.
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'New Hire',
            'type': 'staff',
            'location': 'Abuja',
            'salary': 45000,
            'bank_name': 'UBA',
            'account_number': '1111111111',
            'account_holder': 'New Hire',
            'join_date': str(timezone.now().date()),
        }
        response = self.client.post('/api/employees/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_staff_cannot_create_employee(self):
        self.client.force_authenticate(user=self.staff_user)
        data = {
            'name': 'Sneaky',
            'type': 'staff',
            'location': 'Lagos',
            'salary': 30000,
            'bank_name': 'GTBank',
            'account_number': '9999999999',
            'account_holder': 'Sneaky',
            'join_date': str(timezone.now().date()),
        }
        response = self.client.post('/api/employees/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_employee(self):
        response = self.client.post('/api/employees/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def test_admin_can_delete_employee(self):
        target_user = User.objects.create_user(
            username='target', password='Pass123!', role='staff',
        )
        emp = make_employee(target_user, suffix='del')
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/employees/{emp.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_staff_cannot_delete_employee(self):
        target_user = User.objects.create_user(
            username='target2', password='Pass123!', role='staff',
        )
        emp = make_employee(target_user, suffix='del2')
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(f'/api/employees/{emp.id}/')
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,  # staff queryset can't see other employees
        ])

    # ------------------------------------------------------------------
    # TERMINATE
    # ------------------------------------------------------------------

    def test_terminate_sets_status_and_creates_notification(self):
        target_user = User.objects.create_user(
            username='term_target', password='Pass123!', role='staff',
        )
        emp = make_employee(target_user, suffix='term')
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f'/api/employees/{emp.id}/terminate/',
            {'offense': 'Policy violation'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emp.refresh_from_db()
        self.assertEqual(emp.status, 'terminated')
        self.assertTrue(SackedEmployee.objects.filter(employee=emp).exists())
        self.assertTrue(Notification.objects.filter(user=target_user).exists())

    def test_terminate_without_offense_returns_400(self):
        target_user = User.objects.create_user(
            username='term_no_offense', password='Pass123!', role='staff',
        )
        emp = make_employee(target_user, suffix='t2')
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/employees/{emp.id}/terminate/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_cannot_terminate(self):
        target_user = User.objects.create_user(
            username='term_staff_target', password='Pass123!', role='staff',
        )
        emp = make_employee(target_user, suffix='t3')
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(
            f'/api/employees/{emp.id}/terminate/',
            {'offense': 'Test'},
        )
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ])

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------

    def test_request_export_requires_correct_password(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/employees/request_export/',
            {'password': 'WrongPassword!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_export_success(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/employees/request_export/',
            {'password': 'Pass123!'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_export_csv_with_valid_token(self):
        """Full export flow: get token then download CSV."""
        self.client.force_authenticate(user=self.admin)
        token_response = self.client.post(
            '/api/employees/request_export/',
            {'password': 'Pass123!'},
            format='json',
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        token = token_response.data['token']

        self.client.force_authenticate(user=None)  # token is AllowAny
        csv_response = self.client.get(f'/api/employees/export_csv/?token={token}')
        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)
        self.assertEqual(csv_response['Content-Type'], 'text/csv')

    def test_export_csv_with_invalid_token(self):
        response = self.client.get('/api/employees/export_csv/?token=badtoken')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        def test_export_csv_without_token(self):
            response = self.client.get('/api/employees/export_csv/')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    
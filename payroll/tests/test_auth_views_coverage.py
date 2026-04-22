from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterViewTests(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='reg_super', password='SuperPass123!',
        )
        self.admin = User.objects.create_user(
            username='reg_admin', password='AdminPass123!', role='admin',
        )

    def _register(self, data, user=None):
        self.client.force_authenticate(user=user or self.superuser)
        return self.client.post(reverse('api-register'), data, format='json')

    def test_full_name_two_words_splits(self):
        resp = self._register({'username': 'jsmith', 'password': 'JohnSmith1!',
                                'role': 'admin', 'full_name': 'John Smith'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        u = User.objects.get(username='jsmith')
        self.assertEqual(u.first_name, 'John')
        self.assertEqual(u.last_name, 'Smith')

    def test_full_name_single_word(self):
        resp = self._register({'username': 'cher', 'password': 'Cher1234!',
                                'role': 'admin', 'full_name': 'Cher'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username='cher').last_name, '')

    def test_duplicate_username_400(self):
        resp = self._register({'username': 'reg_admin', 'password': 'Admin123!', 'role': 'admin'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_400(self):
        resp = self._register({'username': 'weakpwd', 'password': 'password', 'role': 'admin'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_role_400(self):
        resp = self._register({'username': 'x', 'password': 'Valid1!A', 'role': 'villain'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_missing_employee_fields_400(self):
        resp = self._register({'username': 'newstaff', 'password': 'StaffPass1!', 'role': 'staff'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required fields', str(resp.data))

    def test_guard_with_all_fields_creates_employee(self):
        resp = self._register({
            'username': 'guardsmith', 'password': 'GuardPass1!', 'role': 'guard',
            'salary': 35000, 'location': 'Abuja', 'bank_name': 'Zenith',
            'account_number': '9876543210', 'account_holder': 'Guard Smith',
            'full_name': 'Guard Smith',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(resp.data['employee'])

    def test_admin_cannot_create_another_admin(self):
        resp = self._register({'username': 'newadmin', 'password': 'Admin123!', 'role': 'admin'},user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_register(self):
        staff = User.objects.create_user(username='reg_staff', password='Pass123!', role='staff')
        resp = self._register({'username': 'newone', 'password': 'NewOne123!', 'role': 'staff'}, user=staff)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_username_400(self):
        resp = self._register({'password': 'Valid1!AA', 'role': 'admin'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='logout_user', password='Pass123!', role='staff')

    def test_logout_without_cookie_200(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(reverse('api-logout')).status_code, status.HTTP_200_OK)

    def test_logout_with_cookie_200(self):
        self.client.force_authenticate(user=self.user)
        self.client.cookies['refresh_token'] = str(RefreshToken.for_user(self.user))
        self.assertEqual(self.client.post(reverse('api-logout')).status_code, status.HTTP_200_OK)


class VerifyPasswordViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vpwd_user', password='Pass123!', role='staff')
        self.client.force_authenticate(user=self.user)

    def test_missing_password_400(self):
        resp = self.client.post(reverse('verify_password'), {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_correct_password_200(self):
        resp = self.client.post(reverse('verify_password'), {'password': 'Pass123!'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['valid'])

    def test_wrong_password_401(self):
        resp = self.client.post(reverse('verify_password'), {'password': 'Wrong!'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(resp.data['valid'])


class CookieTokenRefreshTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='refresh_user', password='Pass123!', role='staff')

    def test_no_cookie_returns_error(self):
        resp = self.client.post(reverse('token_refresh'))
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_400_BAD_REQUEST])

    def test_valid_cookie_returns_access_token(self):
        self.client.cookies['refresh_token'] = str(RefreshToken.for_user(self.user))
        resp = self.client.post(reverse('token_refresh'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
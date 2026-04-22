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

# def test_admin_permission(api_client, admin_user):
#     api_client.force_authenticate(user=admin_user)

#     response = api_client.get("/some-protected-endpoint/")
#     assert response.status_code != 403



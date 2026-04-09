# payroll/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .views import (
    UserViewSet, EmployeeViewSet, AttendanceViewSet, DeductionViewSet,
    PaymentViewSet, CompanyViewSet, SackedEmployeeViewSet, 
    NotificationViewSet, frontend
)
from .auth_views import login_view, register_view, logout_view, CookieTokenRefreshView, verify_password
from rest_framework_simplejwt.views import (
    TokenObtainPairView, 
)
from .auth_views import CurrentUserView
from django.conf import settings
from django.conf.urls.static import static

#

# Simple login view that bypasses CSRF
# @csrf_exempt
# def api_login(request):
#     return login_view(request)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'deductions', DeductionViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'sacked-employees', SackedEmployeeViewSet)
router.register(r'notifications', NotificationViewSet)

urlpatterns = [
    path('', frontend, name='home'),
    path('login/', frontend, name='login'),
    path('dashboard/', frontend, name='dashboard'),
    path('employees/', frontend, name='employees'),
    path('attendance/', frontend, name='attendance'),
    path('deductions/', frontend, name='deductions'),
    path('payments/', frontend, name='payments'),
    path('companies/', frontend, name='companies'),
    path('sacked-employees/', frontend, name='sacked-employees'),
    path('notifications/', frontend, name='notifications'),

    # API endpoints
    path('api/', include(router.urls)),
    # Auth endpoints - using wrapper function to ensure CSRF exemption
    path('api/login/', login_view, name='api-login'),
    path('api/register/', register_view, name='api-register'),
    path('api/logout/', logout_view, name='api-logout'),
    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/current-user/', CurrentUserView.as_view(), name='current-user'),
    path('api/verify-password/', verify_password, name='verify_password'),
]

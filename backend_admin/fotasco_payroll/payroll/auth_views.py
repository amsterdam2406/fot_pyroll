import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Employee
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.views import APIView
from .serializers import UserSerializer
from .throttles import LoginThrottle


logger = logging.getLogger(__name__)
User = get_user_model()

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class CookieTokenRefreshSerializer(TokenRefreshSerializer):
    refresh = None
    def validate(self, attrs):
        attrs['refresh'] = self.context['request'].COOKIES.get('refresh_token')
        if attrs['refresh']:
            return super().validate(attrs)
        else:
            raise InvalidToken('No valid token found in cookie')

class CookieTokenRefreshView(TokenRefreshView):
    serializer_class = CookieTokenRefreshSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # The access token is the only thing sent back to the client in the response body.
        return response

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow anyone to access this endpoint
@throttle_classes([LoginThrottle])
def login_view(request):
    # """Login endpoint"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    
    if not user:
        logger.warning(f"Failed login attempt for {username} from {request.META.get('REMOTE_ADDR')}")
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
        
    logger.info(f"Successful login for {username} from {request.META.get('REMOTE_ADDR')}")
    
    refresh = RefreshToken.for_user(user)

    employee_id = None # safly check if user has employee profile
    if hasattr(user, 'employee_profile'):
        employee_id = user.employee_profile.employee_id

    response = Response({
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'employee_id': employee_id
        }
    }, status=status.HTTP_200_OK)

    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        httponly=True,
        secure=False,  # Set to True in production
        path="/"
    )

    return response


@api_view(['POST'])
# @permission_classes([AllowAny])
@permission_classes([IsAuthenticated])  # no allow anyon to register
def register_view(request):
    data = request.data
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'staff')  # From JSON
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    full_name = (data.get('full_name') or '').strip()
    current_user = request.user

    # #role vali
    if role not in ['admin', 'staff', 'guard']:
        return Response(
            {'error': 'Invalid role'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if current_user.is_superuser:
        pass
    else:
        if current_user.role == 'admin' and role == 'admin':
            return Response(
                {'error': 'Admin users cannot create other admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        if current_user.role in ['staff', 'guard']:
            return Response(
                {'error': 'Only admin users can create new users'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # role hierarchy validati up up

    """Register new user and create employee profile."""
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        validate_password(password)
    except ValidationError as e:
        return Response(
            {'error': e.messages},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # empl vali field
    if role in ['staff', 'guard']:
        required_fields = ['salary', 'location', 'bank_name','account_number', 'account_holder']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return Response(
                {'error': f'Missing required fields: {missing}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    try:
        with transaction.atomic():
            if full_name and not first_name and not last_name:
                name_parts = full_name.split(None, 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

            user = User.objects.create_user(
                username=username,
                password=password,
                email=data.get('email'),
                role=role
            )
            user.first_name = first_name or ''
            user.last_name = last_name or ''
            user.save()

            employee = None
            if role in ['staff', 'guard']:
                employee_name = full_name or f"{first_name or ''} {last_name or ''}".strip() or username

                employee = Employee.objects.create(
                    user=user,
                    name=employee_name,
                    type=role,
                    location=data.get('location'),
                    salary=data.get('salary'),
                    phone=data.get('phone', ''),
                    email=data.get('email'),
                    bank_name=data.get('bank_name'),
                    account_number=data.get('account_number'),
                    account_holder=data.get('account_holder'),
                    join_date=timezone.now().date()
                )

        return Response(
            {
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'employee': (
                    {
                        'id': str(employee.id),
                        'employee_id': employee.employee_id,
                        'name': employee.name,
                        'type': employee.type,
                    } if employee else None
                )
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e: # pragma: no cover
        logger.error(f"Registration error: {e}")
        return Response(
            {'error': 'Registration failed'},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie('refresh_token')
        return response
    except Exception as e:  # pragma: no cover
        logger.error(f"Logout error: {e}")
        response = Response({"detail": "Logout failed, but cookie cleared."}, status=status.HTTP_400_BAD_REQUEST)
        response.delete_cookie('refresh_token')
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_password(request):
    """Confirm current password matches input. Used by frontend exports."""
    pwd = request.data.get('password')
    if not pwd:
        return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
    if request.user.check_password(pwd):
        return Response({'valid': True}, status=status.HTTP_200_OK)
    return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)

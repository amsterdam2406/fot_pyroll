# Coverage Improvement Plan for Production
Status: [IN PROGRESS] Total Coverage: 28% → Target: >85%

## Priority 1: 0% Files (13 files)
- [ ] attendance_views.py (137 miss) - ViewSet + photo actions
- [ ] auth_views.py (135 miss) - Complete branches/token refresh
- [ ] employeeviewset.py (105 miss) 
- [ ] notification_serializer.py 
- [ ] other_views.py
- [ ] otpserializer.py
- [ ] payment_serializer.py
- [ ] payment_views.py
- [ ] permissions.py
- [ ] sack_serializer.py
- [ ] throttles.py
- [ ] user_serializer.py
- [ ] user_views.py

## Priority 2: <50% Files
- [ ] attendance_serializer.py (24%)
- [ ] image_utils.py (23%)
- [ ] paystack.py (24%)
- [ ] password_validators.py (26%)

## Priority 3: 50-79%
- [ ] company_serializer.py (84%)
- [ ] models.py (84%)
- [ ] deduction_serializer.py (58%)
- [ ] employee_serializer.py (75%)

## Steps
1. ✅ Create this TODO.md
2. 🔄 Fix attendance_views.py tests → test_attendance.py
3. Fix auth_views.py → test_auth_views_coverage.py
4. ...

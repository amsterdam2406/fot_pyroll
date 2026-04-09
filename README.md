# Fotasco Payroll - Production Deployment Guide

## Heroku Deployment (Recommended)

### 1. Prerequisites
```
heroku login
heroku create your-app-name
```

### 2. Safety Checklist (Heroku Config Vars)
```
heroku config:set SECRET_KEY=`python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
heroku config:set PAYSTACK_SECRET_KEY=sk_live_...
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=.herokuapp.com
heroku config:set DATABASE_URL=(Heroku auto-adds)
heroku config:set CORS_ALLOWED_ORIGINS=https://your-app.herokuapp.com
```

### 3. Deploy
```
git add .
git commit -m \"Production ready\"
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py collectstatic --noinput
heroku open
```

### 4. Local Production Test
```
pip install gunicorn
gunicorn fotasco_payroll.wsgi
```

### 5. Test Coverage
```
pytest --cov=payroll --cov-report=html --cov-fail-under=90
```

## Key Prod Settings (auto-config)
- DEBUG=False
- PostgreSQL via DATABASE_URL
- Static files: whitenoise
- Security: HSTS, CSP, secure cookies
- Logging: Rotating files
- Throttling/Pagination enabled

**Security:** Never commit .env. Use live Paystack keys only after testing.

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PaystackAPI:
    """Paystack Payment Gateway Integration"""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = getattr(settings,'PAYSTACK_SECRET_KEY', '')
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(self, email, amount, reference):
        """Initialize a payment transaction"""
        url = f"{self.BASE_URL}/transaction/initialize"
        
        payload = {
            'email': email,
            'amount': int(amount * 100), 
            'reference': reference,
            'currency': 'NGN'
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack initialize error: {e}")
            return {'status': False, 'message': str(e), 'data': None}
        except Exception as e:
            logger.error(f"Paystack initialize unexpected error: {e}")
            return {'status': False, 'message': str(e), 'data': None}
    
    def verify_transaction(self, reference):
        """Verify a payment transaction - NEVER returns None"""
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            # Ensure result has expected structure
            if not isinstance(result, dict):
                return {'status': False, 'message': 'Invalid response format', 'data': {'status': 'failed'}}
            if 'data' not in result:
                result['data'] = {'status': 'failed'}
            if 'status' not in result:
                result['status'] = False
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verify error: {e}")
            # CRITICAL: Always return a dict, never None
            return {'status': False, 'message': str(e), 'data': {'status': 'failed'}}
        except Exception as e:
            logger.error(f"Paystack verify unexpected error: {e}")
            return {'status': False, 'message': str(e), 'data': {'status': 'failed'}}
    
    def create_recipient(self, name, account_number, bank_code):
        """Create a transfer recipient"""
        url = f"{self.BASE_URL}/transferrecipient"

        payload = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=20
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status"):
                return {
                    "status": True,
                    "recipient_code": data["data"]["recipient_code"]
                }

            return {"status": False, "message": data.get("message")}

        except requests.exceptions.RequestException as e:
            return {"status": False, "message": str(e)}
        except Exception as e:
            logger.error(f"Paystack create recipient unexpected error: {e}")
            return {"status": False, "message": str(e)}
import json
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError, HTTPError

from django.test import TestCase, override_settings
from django.conf import settings

from payroll.paystack import PaystackAPI


@override_settings(PAYSTACK_SECRET_KEY='sk_test_1234567890abcdef')
class PaystackAPITests(TestCase):
    """Comprehensive Paystack API tests with network failure handling."""
    
    def setUp(self):
        self.paystack = PaystackAPI()
        self.valid_email = 'employee@company.com'
        self.valid_amount = 500000  # 5000 NGN in kobo
        self.valid_reference = 'PAY-1234567890'
        self.valid_bank_code = '057'  # Zenith Bank
        self.valid_account = '1234567890'
        self.valid_name = 'Test Employee'

    # =========================================================================
    # INITIALIZE TRANSACTION TESTS
    # =========================================================================
    
    @patch('requests.post')
    def test_initialize_transaction_success(self, mock_post):
        """Test successful transaction initialization."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'message': 'Authorization URL created',
                'data': {
                    'authorization_url': 'https://checkout.paystack.com/test_auth_url',
                    'access_code': 'test_access_code',
                    'reference': self.valid_reference
                }
            }
        )
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        self.assertTrue(result['status'])
        self.assertEqual(result['data']['reference'], self.valid_reference)
        mock_post.assert_called_once()
        
        # Verify correct headers and payload
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['email'], self.valid_email)
        self.assertEqual(call_args[1]['json']['amount'], self.valid_amount)
        self.assertEqual(call_args[1]['json']['currency'], 'NGN')

    @patch('requests.post')
    def test_initialize_transaction_failure_response(self, mock_post):
        """Test Paystack returns failure status."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': False,
                'message': 'Invalid email address'
            }
        )
        
        result = self.paystack.initialize_transaction(
            email='invalid-email',
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        self.assertFalse(result['status'])
        self.assertEqual(result['message'], 'Invalid email address')

    @patch('requests.post')
    def test_initialize_transaction_network_timeout(self, mock_post):
        """Test handling of network timeout."""
        mock_post.side_effect = Timeout('Connection timed out after 30 seconds')
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        self.assertFalse(result['status'])
        self.assertIn('timed out', result['message'])

    @patch('requests.post')
    def test_initialize_transaction_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = ConnectionError('Failed to establish connection')
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        self.assertFalse(result['status'])
        self.assertIn('connection', result['message'].lower())

    @patch('requests.post')
    def test_initialize_transaction_http_error(self, mock_post):
        """Test handling of HTTP 5xx errors."""
        mock_post.return_value = Mock(
            status_code=500,
            raise_for_status=lambda: Mock(side_effect=HTTPError('500 Server Error')),
            json=lambda: {'status': False, 'message': 'Internal server error'}
        )
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        # Should catch exception and return error dict
        self.assertFalse(result['status'])

    @patch('requests.post')
    def test_initialize_transaction_invalid_json_response(self, mock_post):
        """Test handling of malformed JSON response."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: (_ for _ in ()).throw(ValueError('Invalid JSON'))
        )
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=self.valid_reference
        )
        
        self.assertFalse(result['status'])

    # =========================================================================
    # VERIFY TRANSACTION TESTS
    # =========================================================================
    
    @patch('requests.get')
    def test_verify_transaction_success(self, mock_get):
        """Test successful payment verification."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'message': 'Verification successful',
                'data': {
                    'status': 'success',
                    'reference': self.valid_reference,
                    'amount': self.valid_amount,
                    'gateway_response': 'Successful',
                    'paid_at': '2024-01-15T10:30:00.000Z'
                }
            }
        )
        
        result = self.paystack.verify_transaction(self.valid_reference)
        
        self.assertTrue(result['status'])
        self.assertEqual(result['data']['status'], 'success')
        self.assertEqual(result['data']['amount'], self.valid_amount)

    @patch('requests.get')
    def test_verify_transaction_pending(self, mock_get):
        """Test verification of pending payment."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {
                    'status': 'pending',
                    'reference': self.valid_reference,
                    'amount': self.valid_amount
                }
            }
        )
        
        result = self.paystack.verify_transaction(self.valid_reference)
        
        self.assertTrue(result['status'])
        self.assertEqual(result['data']['status'], 'pending')

    @patch('requests.get')
    def test_verify_transaction_failed(self, mock_get):
        """Test verification of failed payment."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {
                    'status': 'failed',
                    'reference': self.valid_reference,
                    'gateway_response': 'Insufficient funds'
                }
            }
        )
        
        result = self.paystack.verify_transaction(self.valid_reference)
        
        self.assertTrue(result['status'])
        self.assertEqual(result['data']['status'], 'failed')

    @patch('requests.get')
    def test_verify_transaction_not_found(self, mock_get):
        """Test verification of non-existent transaction."""
        mock_get.return_value = Mock(
            status_code=404,
            json=lambda: {
                'status': False,
                'message': 'Transaction not found'
            }
        )
        
        result = self.paystack.verify_transaction('invalid-ref')
        
        self.assertFalse(result['status'])

    @patch('requests.get')
    def test_verify_transaction_network_failure(self, mock_get):
        """Test verification during network failure."""
        mock_get.side_effect = ConnectionError('Network unreachable')
        
        result = self.paystack.verify_transaction(self.valid_reference)
        
        self.assertFalse(result['status'])
        self.assertIn('network', result['message'].lower())

    # =========================================================================
    # CREATE RECIPIENT TESTS (Transfer)
    # =========================================================================
    
    @patch('requests.post')
    def test_create_recipient_success(self, mock_post):
        """Test successful transfer recipient creation."""
        mock_post.return_value = Mock(
            status_code=201,
            raise_for_status=lambda: None,
            json=lambda: {
                'status': True,
                'message': 'Recipient created',
                'data': {
                    'recipient_code': 'RCP_1234567890',
                    'type': 'nuban',
                    'name': self.valid_name,
                    'account_number': self.valid_account
                }
            }
        )
        
        result = self.paystack.create_recipient(
            name=self.valid_name,
            account_number=self.valid_account,
            bank_code=self.valid_bank_code
        )
        
        self.assertTrue(result['status'])
        self.assertEqual(result['recipient_code'], 'RCP_1234567890')

    @patch('requests.post')
    def test_create_recipient_failure(self, mock_post):
        """Test recipient creation failure."""
        mock_post.return_value = Mock(
            status_code=400,
            raise_for_status=lambda: None,
            json=lambda: {
                'status': False,
                'message': 'Invalid account number'
            }
        )
        
        result = self.paystack.create_recipient(
            name=self.valid_name,
            account_number='invalid',
            bank_code=self.valid_bank_code
        )
        
        self.assertFalse(result['status'])
        self.assertEqual(result['message'], 'Invalid account number')

    @patch('requests.post')
    def test_create_recipient_http_error(self, mock_post):
        """Test recipient creation with HTTP error."""
        mock_post.return_value = Mock(
            raise_for_status=lambda: (_ for _ in ()).throw(
                HTTPError('400 Client Error: Bad Request')
            )
        )
        
        result = self.paystack.create_recipient(
            name=self.valid_name,
            account_number=self.valid_account,
            bank_code=self.valid_bank_code
        )
        
        self.assertFalse(result['status'])

    @patch('requests.post')
    def test_create_recipient_timeout(self, mock_post):
        """Test recipient creation timeout."""
        mock_post.side_effect = Timeout('Request timed out after 20 seconds')
        
        result = self.paystack.create_recipient(
            name=self.valid_name,
            account_number=self.valid_account,
            bank_code=self.valid_bank_code
        )
        
        self.assertFalse(result['status'])
        self.assertIn('timed out', result['message'])

    # =========================================================================
    # EDGE CASES & SECURITY
    # =========================================================================
    
    def test_headers_configuration(self):
        """Test that headers are correctly configured."""
        self.assertEqual(
            self.paystack.headers['Authorization'],
            'Bearer sk_test_1234567890abcdef'
        )
        self.assertEqual(
            self.paystack.headers['Content-Type'],
            'application/json'
        )

    @patch('requests.post')
    def test_amount_formatting_large_values(self, mock_post):
        """Test handling of large payment amounts."""
        large_amount = 999999999  # Very large amount
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'status': True, 'data': {'reference': 'large-pay'}}
        )
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=large_amount,
            reference='large-pay'
        )
        
        self.assertTrue(result['status'])

    @patch('requests.post')
    def test_special_characters_in_reference(self, mock_post):
        """Test handling of special characters in reference."""
        special_ref = 'PAY-TEST_123.456@789'
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'status': True, 'data': {'reference': special_ref}}
        )
        
        result = self.paystack.initialize_transaction(
            email=self.valid_email,
            amount=self.valid_amount,
            reference=special_ref
        )
        
        self.assertTrue(result['status'])

    @patch('requests.get')
    def test_verify_transaction_malformed_response(self, mock_get):
        """Test handling of completely malformed response."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: None  # Null response
        )
        
        result = self.paystack.verify_transaction(self.valid_reference)
        
        # Should not crash, but return error
        self.assertFalse(result['status'])


class PaystackIntegrationFlowTests(TestCase):
    """End-to-end payment flow integration tests."""
    
    @override_settings(PAYSTACK_SECRET_KEY='sk_test_integration')
    def setUp(self):
        self.paystack = PaystackAPI()
    
    @patch('requests.post')
    @patch('requests.get')
    def test_full_payment_lifecycle_success(self, mock_get, mock_post):
        """Test complete payment flow: initialize → verify."""
        # Initialize
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {
                    'authorization_url': 'https://paystack.com/pay/test',
                    'reference': 'lifecycle-test'
                }
            }
        )
        
        init_result = self.paystack.initialize_transaction(
            email='test@test.com',
            amount=100000,
            reference='lifecycle-test'
        )
        
        self.assertTrue(init_result['status'])
        
        # Verify
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {
                    'status': 'success',
                    'reference': 'lifecycle-test',
                    'amount': 100000
                }
            }
        )
        
        verify_result = self.paystack.verify_transaction('lifecycle-test')
        self.assertTrue(verify_result['status'])
        self.assertEqual(verify_result['data']['status'], 'success')

    @patch('requests.post')
    @patch('requests.get')
    def test_full_payment_lifecycle_failure(self, mock_get, mock_post):
        """Test complete payment flow with failure."""
        # Initialize succeeds
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {'reference': 'failed-test'}
            }
        )
        
        init_result = self.paystack.initialize_transaction(
            email='test@test.com',
            amount=100000,
            reference='failed-test'
        )
        self.assertTrue(init_result['status'])
        
        # But verification shows failure
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': True,
                'data': {
                    'status': 'failed',
                    'reference': 'failed-test',
                    'gateway_response': 'Declined by bank'
                }
            }
        )
        
        verify_result = self.paystack.verify_transaction('failed-test')
        self.assertEqual(verify_result['data']['status'], 'failed')
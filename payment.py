import os
import json
import random
import string
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

# Konfigurasi logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kunci rahsia ToyyibPay anda
TOYYIBPAY_SECRET_KEY = 'YOUR_TOYYIBPAY_SECRET_KEY'  # Gantikan dengan kunci rahsia anda

def generate_random_string(length=8) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def create_category() -> Optional[str]:
    """Create a category in ToyyibPay and return the category code."""
    category_name = f"Telegram Payment for {generate_random_string()}"
    category_description = "Payment for bot services"
    
    payload = {
        'catname': category_name,
        'catdescription': category_description,
        'userSecretKey': TOYYIBPAY_SECRET_KEY
    }
    
    try:
        response = requests.post('https://toyyibpay.com/index.php/api/createCategory', data=payload)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            return data[0].get('CategoryCode')
        else:
            logger.error("Unexpected response format for category creation.")
            return None
    except requests.RequestException as e:
        logger.error(f"Category creation failed: {e}")
        return None

def create_bill(category_code: str, user_id: int, price_code: int, item_name: str) -> Optional[str]:
    """Create a bill in ToyyibPay and return the payment URL."""
    bill_amount = price_code
    bill_name = generate_random_string(10)
    bill_description = f"Bill for {user_id}"
    order_id = f"{user_id}_{bill_name}_{item_name}"
    
    payload = {
        'userSecretKey': TOYYIBPAY_SECRET_KEY,
        'categoryCode': category_code,
        'billName': bill_name,
        'billDescription': bill_description,
        'billPriceSetting': 1,
        'billPayorInfo': 1,
        'billAmount': bill_amount,
        'billReturnUrl': 'https://yourdomain.com/payment_return',
        'billCallbackUrl': 'https://yourdomain.com/payment_callback',
        'billExternalReferenceNo': order_id,
        'billTo': '',
        'billEmail': '',  # Add user email if needed
        'billPhone': '',  # Add user phone number if needed
        'billSplitPayment': 0,
        'billPaymentChannel': '0',
        'billContentEmail': 'Thank you for purchasing!',
        'billChargeToCustomer': 1,
        'billExpiryDays': 1
    }
    
    try:
        response = requests.post('https://toyyibpay.com/index.php/api/createBill', data=payload)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            bill_code = data[0].get('BillCode')
            if bill_code:
                return f"https://toyyibpay.com/{bill_code}"
            else:
                logger.error("Bill code not found in response.")
                return None
        else:
            logger.error("Unexpected response format for bill creation.")
            return None
    except requests.RequestException as e:
        logger.error(f"Bill creation failed: {e}")
        return None

def load_user_data() -> Dict[int, Dict[str, str]]:
    """Load user data from file."""
    if os.path.exists('userpaid_data.json'):
        with open('userpaid_data.json', 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from file: {e}")
                return {}
    return {}

def save_user_data(user_data: Dict[int, Dict[str, str]]) -> None:
    """Save user data to file."""
    try:
        with open('userpaid_data.json', 'w') as file:
            json.dump(user_data, file, indent=4)
    except IOError as e:
        print(f"Error writing to file: {e}")

def process_payment(client: 'Client', message: 'types.Message') -> None:
    """Create a payment invoice and send the payment link to the user."""
    user_id = message.from_user.id
    
    category_code = create_category()
    if not category_code:
        client.send_message(message.chat.id, "Failed to create payment category. Please try again later.")
        return
    
    price_code = 1000  # Example: RM10 (in cents)
    item_name = "premium_access"
    
    payment_url = create_bill(category_code, user_id, price_code, item_name)
    if payment_url:
        client.send_message(message.chat.id, f"Please complete your payment by visiting: {payment_url}")
    else:
        client.send_message(message.chat.id, "Failed to create payment link. Please try again later.")

def payment_callback(request: 'requests.Request') -> None:
    """Handle payment callback and update user status."""
    try:
        data = request.json()
        bill_code = data.get('billcode')
        status = data.get('status')
        order_id = data.get('order_id')
        
        if not order_id:
            logger.error("Order ID missing in callback.")
            return
        
        user_id = int(order_id.split('_')[0])
        
        if status == '1':  # Success
            user_data = load_user_data()
            subscription_end = datetime.now() + timedelta(days=30)
            user_data[user_id] = {"subscription_end": subscription_end.isoformat()}
            save_user_data(user_data)
            # Notify user
            client.send_message(user_id, "Payment successful! You now have access to premium features.")
        else:
            client.send_message(user_id, "Payment failed. Please try again.")
    except Exception as e:
        logger.error(f"Payment callback handling failed: {e}")


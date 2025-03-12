import re
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings

def format_phone_number(phone):
    """ Convert Kenyan phone numbers to E.164 format """
    if phone.startswith("0"):
        return "+254" + phone[1:]  # Convert 071767XXXX → +25471767XXXX
    elif not phone.startswith("+"):
        return "+254" + phone  # Add +254 if missing
    return phone

def send_sms(to, message):
    try:
        formatted_to = format_phone_number(to)  # ✅ Format number correctly
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=formatted_to
        )
    except TwilioRestException as e:
        print(f"Twilio Error: {e}")  # Log error for debugging

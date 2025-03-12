from celery import shared_task
from datetime import datetime, timedelta
from django.conf import settings
from twilio.rest import Client
from .models import Appointment

# Twilio SMS Sending Function
def send_sms(to, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to
    )

@shared_task
def schedule_reminder_task(appointment_id):
    """
    Celery task to send appointment reminders.
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        reminder_time = appointment.date - timedelta(hours=1)  # 1 hour before
        now = datetime.now().date()

        if reminder_time == now:
            message = f"Reminder: Your appointment with {appointment.doctor} at {appointment.time} is in 1 hour."
            send_sms(appointment.phone, message)  # Send to patient
            send_sms("+254717677588", message)  # Send to doctor (replace with doctor's phone)
            
        return f"Reminder sent for appointment ID {appointment.id}"
    except Appointment.DoesNotExist:
        return "Appointment not found"

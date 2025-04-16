from django.core.mail import send_mail

def send_email_notification(recipient, subject, body):
    send_mail(
        subject,
        body,
        'elikiprop42@gmail.com',  # Update with your email
        [recipient],
        fail_silently=False,
    )

def get_doctor_email(doctor):
    return doctor.user.email
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from datetime import datetime
from .models import Appointment
from .utils import send_email_notification  # Import email function

# Home Page View
def home(request):
    return render(request, 'index.html')

# Static Pages
def about(request):
    return render(request, 'about.html')

def appointment(request):
    return render(request, 'appointment.html')

def blog(request):
    return render(request, 'blog.html')

def contact(request):
    return render(request, 'contact.html')

def detail(request):
    return render(request, 'detail.html')

def price(request):
    return render(request, 'price.html')

def search(request):
    return render(request, 'search.html')

def service(request):
    return render(request, 'service.html')

def team(request):
    return render(request, 'team.html')

def testimonial(request):
    return render(request, 'testimonial.html')

# ✅ Function to Get Google Meet Link for Each Doctor
def get_google_meet_link(doctor):
    doctor_meet_links = {
        "Doctor Kiprop": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Wambwere": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Jackie": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Lisper": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Mirriel": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Reckie": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Cherop": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Ndiema": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Eli": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Mutai": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Koech": "https://meet.google.com/bdu-vfen-nwx",
    }
    return doctor_meet_links.get(doctor, "https://meet.google.com/bdu-vfen-nwx")  # Default link

# ✅ Function to Send All Doctor Emails to "elindiema7@gmail.com"
def get_doctor_email(doctor):
    return "elindiema7@gmail.com"  # ✅ All emails go to this address

# ✅ Book an Appointment and Send Email to Doctor
def book_appointment(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        department = request.POST.get("department")
        doctor = request.POST.get("doctor")
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")

        try:
            # Convert date & time to a datetime object
            appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # Get Google Meet link
            google_meet_link = get_google_meet_link(doctor)

            # Save the appointment
            appointment = Appointment.objects.create(
                name=name, email=email, phone=phone,
                department=department, doctor=doctor,
                date=appointment_datetime.date(),
                time=appointment_datetime.time(),
                google_meet_link=google_meet_link  # ✅ Store Google Meet link
            )

            # ✅ Notify Doctor via Email
            doctor_email = get_doctor_email(doctor)
            subject = f"New Appointment with {name}"
            message = f"""
            Dear Doctor,

            You have a new appointment scheduled:

            Patient: {name}
            Email: {email}
            Phone: {phone}
            Department: {department}
            Date: {date_str}
            Time: {time_str}

            Google Meet Link: {google_meet_link}

            Please be available at the scheduled time.

            Best regards,
            MediConnect Team
            """

            send_email_notification(doctor_email, subject, message)  # ✅ Send Email

            return redirect("view_appointments")

        except ValueError:
            return render(request, "appointment.html", {"error": "Invalid date or time format!"})

    return render(request, "appointment.html")

# ✅ View all booked appointments
def view_appointments(request):
    appointments = Appointment.objects.all().order_by('-date', '-time')  # Fetch all appointments sorted by latest first
    return render(request, "view_appointments.html", {"appointments": appointments})

# ✅ Notify Doctor When Patient Joins Video Call
def notify_doctor_video_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor_email = get_doctor_email(appointment.doctor)

    subject = f"Patient {appointment.name} Joined the Video Call"
    message = f"""
    Dear Doctor,

    Your patient {appointment.name} has joined the video call.

    Meet Link: {appointment.google_meet_link}

    Please join the call at your scheduled time.
    """

    send_email_notification(doctor_email, subject, message)  # ✅ Send Email

    return redirect(appointment.google_meet_link)  # ✅ Open Google Meet

# ✅ Notify Doctor When Patient Makes a Voice Call
def notify_doctor_voice_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor_email = get_doctor_email(appointment.doctor)

    subject = f"Patient {appointment.name} is Calling You"
    message = f"""
    Dear Doctor,

    Your patient {appointment.name} is calling you on their registered phone number: {appointment.phone}

    Please be available for the call.
    """

    send_email_notification(doctor_email, subject, message)  # ✅ Send Email

    return redirect(f"tel:{appointment.phone}")  # ✅ Open Phone Dialer

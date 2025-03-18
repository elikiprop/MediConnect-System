from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from datetime import datetime
import pdfkit
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import MedicalRecordForm, PatientReferralForm, RegisterForm, LoginForm
from .utils import send_email_notification  # Import email function
from .forms import ContactForm
from django.core.mail import send_mail
from django.contrib import messages
from .models import Appointment, MedicalRecord, UserProfile


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Send an email (configure settings.py for email sending)
            send_mail(
                f"New Contact Form Submission: {subject}",
                f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                email,  # From email
                ['your-email@example.com'],  # Change this to your email
                fail_silently=False,
            )

            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')  # Redirect to the contact page after submission

    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})

# ✅ Home Page (Requires Login)
@login_required(login_url='login')
def home(request):
    return render(request, "index.html")

# ✅ Static Pages
def about(request):
    return render(request, "about.html")

def appointment(request):
    return render(request, "appointment.html")

def blog(request):
    return render(request, "blog.html")

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Send an email
            send_mail(
                f"New Contact Form Submission: {subject}",
                f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                email,  
                ['elikiprop42@gmail.com'],  
                fail_silently=False,
            )

            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')

    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})

def detail(request):
    return render(request, "detail.html")

def price(request):
    return render(request, "price.html")

def search(request):
    return render(request, "search.html")

def service(request):
    return render(request, "service.html")

def team(request):
    return render(request, "team.html")

def testimonial(request):
    return render(request, "testimonial.html")




# ✅ Dashboard Views
@login_required(login_url='login')
def patient_dashboard(request):
    return render(request, "patient_dashboard.html")

@login_required(login_url='login')
def doctor_dashboard(request):
    records = MedicalRecord.objects.all()
    return render(request, "doctor_dashboard.html", {"records": records})

@login_required(login_url='login')
def admin_dashboard(request):
    appointments = Appointment.objects.all().order_by("-date", "-time")
    return render(request, "admin_dashboard.html", {"appointments": appointments})


# ✅ Add/Edit Medical Record
@login_required(login_url='login')
def add_edit_medical_record(request, record_id=None):
    record = get_object_or_404(MedicalRecord, id=record_id) if record_id else None

    if request.method == "POST":
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect("doctor_dashboard")
    else:
        form = MedicalRecordForm(instance=record)

    return render(request, "add_edit_medication.html", {"form": form})


# ✅ Refer a Patient to Another Doctor
@login_required(login_url='login')
def refer_patient(request):
    if request.method == "POST":
        form = PatientReferralForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("doctor_dashboard")
    else:
        form = PatientReferralForm()

    return render(request, "refer_patient.html", {"form": form})


# ✅ Generate Medical Record PDF
@login_required(login_url='login')
def generate_pdf(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)
    html = render_to_string("medical_record_pdf.html", {"record": record})
    pdf = pdfkit.from_string(html, False)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{record.patient_name}_record.pdf"'
    return response


# ✅ Delete Appointment
@login_required(login_url='login')
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.delete()
    return redirect("view_appointments")


# ✅ Reschedule Appointment (With Center-Aligned Form)
@login_required(login_url='login')
def reschedule_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == "POST":
        new_date = request.POST.get("date")
        new_time = request.POST.get("time")

        try:
            new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            if new_datetime < datetime.now():
                return render(request, "reschedule_appointment.html", {"appointment": appointment, "error": "You cannot select a past date or time!"})

            appointment.date = new_datetime.date()
            appointment.time = new_datetime.time()
            appointment.save()

            return redirect("view_appointments")  
        except ValueError:
            return render(request, "reschedule_appointment.html", {"appointment": appointment, "error": "Invalid date or time format!"})

    return render(request, "reschedule_appointment.html", {"appointment": appointment})


# ✅ Function to Get Google Meet Link for Each Doctor
def get_google_meet_link(doctor):
    doctor_meet_links = {
        "Doctor Kiprop": "https://meet.google.com/bdu-vfen-nwx",
        "Doctor Wambwere": "https://meet.google.com/bdu-vfen-nwx",
    }
    return doctor_meet_links.get(doctor, "https://meet.google.com/bdu-vfen-nwx")  # Default link


# ✅ Function to Send Doctor Emails
def get_doctor_email(doctor):
    return "elindiema7@gmail.com"  # Default email for all doctors


# ✅ Book Appointment & Notify Doctor & Patient
@login_required(login_url='login')
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
            appointment_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            if appointment_datetime < datetime.now():
                return render(request, "appointment.html", {"error": "You cannot book an appointment in the past!"})

            appointment = Appointment.objects.create(
                name=name, email=email, phone=phone,
                department=department, doctor=doctor,
                date=appointment_datetime.date(),
                time=appointment_datetime.time(),
            )

            send_email_notification(email, "Appointment Confirmation", f"Your appointment with {doctor} is confirmed.")
            send_email_notification(get_doctor_email(doctor), "New Appointment", f"New appointment scheduled with {name}.")

            return redirect("view_appointments")

        except ValueError:
            return render(request, "appointment.html", {"error": "Invalid date or time format!"})

    return render(request, "appointment.html")


# ✅ View All Appointments
@login_required(login_url='login')
def view_appointments(request):
    appointments = Appointment.objects.all().order_by("-date", "-time")
    return render(request, "view_appointments.html", {"appointments": appointments})


# ✅ Notify Doctor When Patient Joins Video Call
@login_required(login_url='login')
def notify_doctor_video_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    send_email_notification(get_doctor_email(appointment.doctor), f"Patient {appointment.name} Joined Video Call", f"Meet Link: {appointment.google_meet_link}")
    return redirect(appointment.google_meet_link)


# ✅ Notify Doctor When Patient Makes a Voice Call
@login_required(login_url='login')
def notify_doctor_voice_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    send_email_notification(get_doctor_email(appointment.doctor), f"Patient {appointment.name} is Calling", f"Phone: {appointment.phone}")
    return redirect(f"tel:{appointment.phone}")


# ✅ Register
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            UserProfile.objects.create(user=user, role=form.cleaned_data["role"])
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})


# ✅ Login
def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data["username"], password=form.cleaned_data["password"])
            if user:
                login(request, user)
                return redirect("home")
            else:
                return render(request, "login.html", {"form": form, "error": "Invalid credentials!"})
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


# ✅ Logout
def user_logout(request):
    logout(request)
    return redirect("login")

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import UserProfile
from .forms import LoginForm

def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)

                # ✅ Fetch the user's role
                user_profile = UserProfile.objects.filter(user=user).first()

                if user_profile:
                    # ✅ Redirect based on role
                    if user_profile.role == "patient":
                        return redirect("patient_dashboard")
                    elif user_profile.role == "doctor":
                        return redirect("doctor_dashboard")
                    elif user_profile.role == "admin":
                        return redirect("admin_dashboard")
                else:
                    return render(request, "login.html", {"form": form, "error": "User profile not found!"})
            else:
                return render(request, "login.html", {"form": form, "error": "Invalid username or password!"})
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


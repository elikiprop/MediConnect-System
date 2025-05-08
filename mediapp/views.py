from datetime import date, datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
import json
import pdfkit
import sys

from .forms import (
    AppointmentForm,
    ContactForm,
    LoginForm,
    MedicalRecordForm,
    PatientReferralForm,
    RegisterForm,
)
from .models import (
    Appointment,
    CustomUser,
    Doctor,
    LabResult,
    MedicalRecord,
    PatientHistory,
    PatientNote,
    PatientReferral,
    Prescription,
   
)
from .utils import get_doctor_email, send_email_notification



# Simplified admin check
def is_admin(user):
    return user.role == 'admin'


# Static Pages
def about(request):
    return render(request, "about.html")


def appointment(request):
    form = AppointmentForm()
    return render(request, "appointment.html", {"form": form})


def blog(request):
    return render(request, "blog.html")


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


# Home Page
@login_required(login_url="login")
def home(request):
    return render(request, "index.html")


# Contact Form
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]
            send_mail(
                f"New Contact Form Submission: {subject}",
                f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                email,
                ["elikiprop42@gmail.com"],
                fail_silently=False,
            )
            messages.success(request, "Your message has been sent successfully!")
            return redirect("contact")
    else:
        form = ContactForm()
    return render(request, "contact.html", {"form": form})


# Authentication Views
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful! Please log in.")
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})



# Login view
def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            role = user.role
            if role == "admin":
                return redirect("admin_dashboard")
            elif role == "doctor":
                return redirect("doctor_dashboard")
            elif role == "patient":
                return redirect("patient_dashboard")
            else:
                messages.error(request, f"Unknown user role: {role}")
                return redirect("login")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})


def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")


# Dashboard Views
@login_required(login_url="login")
def patient_dashboard(request):
    if request.user.role != "patient":
        messages.error(request, "Only patients can access this page.")
        return redirect("home")
    records = MedicalRecord.objects.filter(patient=request.user)
    appointments = Appointment.objects.filter(patient=request.user)
    return render(request, "patient_dashboard.html", {
        "records": records,
        "appointments": appointments,
    })


@login_required(login_url="login")
def doctor_dashboard(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can access this dashboard.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found. Please contact an administrator.")
        return redirect("home")

    # Handle patient search
    search_results = []
    if request.method == "GET" and ("patient_name" in request.GET or "patient_id" in request.GET):
        patient_name = request.GET.get("patient_name", "")
        patient_id = request.GET.get("patient_id", "")
        if patient_name or patient_id:
            search_results = CustomUser.objects.filter(
                Q(role="patient") & (Q(username__icontains=patient_name) | Q(id__icontains=patient_id))
            )

    # Get data
    records = MedicalRecord.objects.filter(doctor=doctor).order_by("-created_at")
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor, date__gte=date.today()
    ).order_by("date", "time")
    past_appointments = Appointment.objects.filter(
        doctor=doctor, date__lt=date.today()
    ).order_by("-date", "-time")[:10]
    pending_referrals = PatientReferral.objects.filter(
        referred_doctor=doctor, status="pending"
    ).order_by("-created_at")
    incoming_referrals = PatientReferral.objects.filter(
        referred_doctor=doctor
    ).exclude(status="pending").order_by("-created_at")
    outgoing_referrals = PatientReferral.objects.filter(
        referring_doctor=doctor
    ).order_by("-created_at")
    patients = CustomUser.objects.filter(role="patient").order_by("username")
    prescriptions = Prescription.objects.filter(doctor=doctor).order_by("-created_at")
    lab_results = LabResult.objects.filter(doctor=doctor).order_by("-test_date")
    patient_notes = PatientNote.objects.filter(doctor=doctor).order_by("-created_at")
    patient_history = PatientHistory.objects.filter(doctor=doctor).order_by("-created_at")
    today_appointments = Appointment.objects.filter(
        doctor=doctor, date=date.today()
    ).count()
    appointments = Appointment.objects.filter(doctor=doctor)

    # Calculate total patients and appointments
    total_patients = CustomUser.objects.filter(
        role="patient",
        doctor=doctor
    ).count()
    total_appointments = Appointment.objects.filter(
        doctor=doctor
    ).count()

    # Handle AJAX medical record submission
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if all(k in request.POST for k in ["patient_id", "diagnosis", "medication"]):
            try:
                patient = CustomUser.objects.get(id=request.POST.get("patient_id"), role="patient")
                record = MedicalRecord(
                    patient=patient,
                    doctor=doctor,
                    diagnosis=request.POST.get("diagnosis"),
                    medication=request.POST.get("medication"),
                )
                record.save()
                return JsonResponse({
                    "status": "success",
                    "message": "Medical record added successfully!",
                    "record_id": record.id,
                    "patient_name": patient.username,
                    "date": record.created_at.strftime("%b %d, %Y"),
                })
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)})

    context = {
        "doctor": doctor,
        "records": records,
        "upcoming_appointments": upcoming_appointments,
        "past_appointments": past_appointments,
        "pending_referrals": pending_referrals,
        "incoming_referrals": incoming_referrals,
        "outgoing_referrals": outgoing_referrals,
        "patients": patients,
        "prescriptions": prescriptions,
        "lab_results": lab_results,
        "patient_notes": patient_notes,
        "patient_history": patient_history,
        "today_appointments": today_appointments,
        "appointments": appointments,
        "search_results": search_results,
        "today": date.today(),
        "total_patients": total_patients,  # Added
        "total_appointments": total_appointments,  # Added
    }
    return render(request, "doctor_dashboard.html", context)

# Medical Record Views
@login_required(login_url="login")
def add_medical_record(request, patient_id=None, record_id=None):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can add or edit medical records.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You do not have a doctor profile.")
        return redirect("home")

    # Determine patient_id from URL, GET, or POST
    patient_id = patient_id or request.GET.get("patient_id") or request.POST.get("patient_id")

    if record_id:  # Editing existing record
        record = get_object_or_404(MedicalRecord, id=record_id, doctor=doctor)
        patient = record.patient
        is_edit = True
    else:  # Adding new record
        if patient_id:
            try:
                patient = CustomUser.objects.get(id=patient_id, role="patient")
            except CustomUser.DoesNotExist:
                messages.error(request, "Patient not found or not a valid patient.")
                return redirect("doctor_dashboard")
        else:
            # Render patient selection page if no patient_id is provided
            patients = CustomUser.objects.filter(role="patient")
            return render(request, "select_patient.html", {"patients": patients})

        record = None
        is_edit = False

    if request.method == "POST":
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            try:
                medical_record = form.save(commit=False)
                medical_record.patient = patient
                medical_record.doctor = doctor
                medical_record.save()

                # Handle referral if specified
                referred_to = form.cleaned_data.get('referred_to')
                department_sent_to = form.cleaned_data.get('department_sent_to')
                if referred_to and department_sent_to:
                    PatientReferral.objects.create(
                        patient=patient,
                        referring_doctor=doctor,
                        referred_doctor=referred_to,
                        reason=f"Referral based on medical record: {medical_record.diagnosis}",
                        department=department_sent_to,
                        status='pending'
                    )

                messages.success(request, f"Medical record {'updated' if is_edit else 'added'} successfully!")
                return redirect("doctor_dashboard")
            except Exception as e:
                messages.error(request, f"Error saving record: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        initial_data = {'patient': patient, 'doctor': doctor} if patient else {}
        form = MedicalRecordForm(instance=record, initial=initial_data)

    context = {
        "form": form,
        "patient": patient,
        "is_edit": is_edit,
    }
    return render(request, "add_medical_record.html", context)


@login_required(login_url="login")
def update_medical_record(request, record_id):
    if request.user.role != "doctor":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": "Only doctors can edit medical records."})
        messages.error(request, "Only doctors can edit medical records.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": "You do not have a doctor profile."})
        messages.error(request, "You do not have a doctor profile.")
        return redirect("home")

    record = get_object_or_404(MedicalRecord, id=record_id)
    if record.doctor != doctor:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": "You can only edit your own medical records."})
        messages.error(request, "You can only edit your own medical records.")
        return redirect("doctor_dashboard")

    if request.method == "POST":
        if "diagnosis" in request.POST:
            record.diagnosis = request.POST.get("diagnosis")
        if "medication" in request.POST:
            record.medication = request.POST.get("medication")
        record.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "success", "message": "The Medical record updated successfully!"})

        messages.success(request, "The Medical record has been updated successfully!")
        return redirect("doctor_dashboard")

    return redirect("doctor_dashboard")


@login_required(login_url="login")
def delete_record(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(MedicalRecord, id=record_id)
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if (
            request.user == record.patient
            or request.user == record.doctor.user
            or request.user.role == "admin"
        ):
            patient_name = record.patient.get_full_name() or record.patient.username
            date = record.created_at.date()
            record.delete()

            if is_ajax:
                return JsonResponse({
                    "status": "success",
                    "message": f"Medical record for {patient_name} dated {date} has been deleted successfully.",
                })

            messages.success(
                request,
                f"Medical record for {patient_name} dated {date} has been deleted successfully.",
            )
        else:
            if is_ajax:
                return JsonResponse({
                    "status": "error",
                    "message": "You don't have permission to delete this medical record.",
                }, status=403)

            messages.error(request, "You don't have permission to delete this medical record.")

    if request.method != "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "status": "error",
            "message": "Invalid request method. Please use POST to delete records.",
        }, status=400)

    if request.user.role == "doctor":
        return redirect("doctor_dashboard")
    elif request.user.role == "patient":
        return redirect("patient_dashboard")
    return redirect("home")


@login_required(login_url="login")
def generate_pdf(request, record_id):
    record = get_object_or_404(MedicalRecord, id=record_id)

    if not (
        request.user == record.patient
        or request.user == record.doctor.user
        or request.user.role == "admin"
    ):
        messages.error(request, "You don't have permission to access this record.")
        return redirect("home")

    html = render_to_string("medical_record_pdf.html", {"record": record})
    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdf = pdfkit.from_string(html, False, configuration=config)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{record.patient.username}_record.pdf"'
    return response


# Appointment Views
@login_required(login_url="login")
def book_appointment(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            try:
                appointment_date = form.cleaned_data["date"]
                appointment_time = form.cleaned_data["time"]
                selected_doctor = form.cleaned_data["doctor"]

                if request.user.is_authenticated and request.user.role == "patient":
                    if Appointment.objects.filter(
                        patient=request.user,
                        doctor=selected_doctor,
                        date=appointment_date,
                        time=appointment_time,
                    ).exists():
                        messages.error(request, "You already have an appointment with this doctor at this time.")
                        return render(request, "appointment.html", {"form": form})

                default_meet_link = "https://meet.google.com/bdu-vfen-nwx"
                appointment = Appointment(
                    name=form.cleaned_data["name"],
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                    department=form.cleaned_data["department"],
                    doctor=selected_doctor,
                    date=appointment_date,
                    time=appointment_time,
                    patient=request.user if request.user.is_authenticated and request.user.role == "patient" else None,
                    voice_call_link=default_meet_link,
                    video_call_link=default_meet_link,
                )
                appointment.clean()
                appointment.save()

                try:
                    send_mail(
                        "Appointment Confirmation",
                        f"Your appointment with Dr. {selected_doctor.user.get_full_name() or selected_doctor.user.username} is confirmed for {appointment_date} at {appointment_time}. Video link: {default_meet_link}",
                        settings.DEFAULT_FROM_EMAIL,
                        [form.cleaned_data["email"]],
                        fail_silently=True,
                    )
                    doctor_email = selected_doctor.user.email
                    if doctor_email:
                        send_mail(
                            "New Appointment",
                            f"You have New appointment scheduled with patient Name: {form.cleaned_data['name']} for {appointment_date} at {appointment_time}. Video link: {default_meet_link}",
                            settings.DEFAULT_FROM_EMAIL,
                            [doctor_email],
                            fail_silently=True,
                        )
                except Exception as e:
                    print(f"Email sending error: {str(e)}")

                messages.success(request, "You have booked Your Appointment successfully!")
                return redirect("view_appointments" if request.user.is_authenticated and request.user.role == "patient" else "home")
            except forms.ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "The Doctor is having another appointment scheduled for this Time, choose other time!.")
    else:
        form = AppointmentForm()
    return render(request, "appointment.html", {"form": form})


@login_required(login_url="login")
def view_appointments(request):
    if request.user.role != "patient":
        messages.error(request, "Only patients can view appointments.")
        return redirect("home")
    appointments = Appointment.objects.filter(patient=request.user).order_by("date", "time")
    return render(request, "view_appointments.html", {"appointments": appointments})


@login_required(login_url="login")
def reschedule_appointment(request, appointment_id):
    if request.user.role != "patient":
        messages.error(request, "Only patients can reschedule appointments.")
        return redirect("home")
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            try:
                appointment = form.save(commit=False)
                appointment.clean()
                appointment.save()

                doctor_email = get_doctor_email(appointment.doctor)
                if doctor_email:
                    send_email_notification(
                        doctor_email,
                        "Appointment Rescheduled",
                        f"Patient {appointment.patient.get_full_name() or appointment.patient.username} has rescheduled their appointment to {appointment.date} at {appointment.time}.",
                    )

                messages.success(request, "Appointment rescheduled successfully!")
                return redirect("view_appointments")
            except forms.ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "The Doctor is having another appointment scheduled for this Time, please choose other time!")
    else:
        form = AppointmentForm(instance=appointment)
    return render(request, "reschedule_appointment.html", {"form": form, "appointment": appointment})


@login_required(login_url="login")
def delete_appointment(request, appointment_id):
    if request.user.role != "patient":
        messages.error(request, "Only patients can delete appointments.")
        return redirect("home")
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if request.method == "POST":
        doctor_email = get_doctor_email(appointment.doctor)
        doctor_name = appointment.doctor.user.get_full_name() or appointment.doctor.user.username
        appointment_date = appointment.date
        appointment_time = appointment.time

        appointment.delete()

        if doctor_email:
            send_email_notification(
                doctor_email,
                "Appointment Canceled",
                f"Patient {request.user.get_full_name() or request.user.username} has canceled their appointment scheduled for {appointment_date} at {appointment_time}.",
            )

        messages.success(
            request,
            f"Appointment with Dr. {doctor_name} on {appointment_date} at {appointment_time} has been canceled successfully.",
        )
        return redirect("view_appointments")
    return redirect("view_appointments")


@login_required(login_url="login")
def get_appointments(request):
    if request.user.role != "doctor":
        return JsonResponse({"error": "Unauthorized"}, status=403)
    try:
        doctor = Doctor.objects.get(user=request.user)
        appointments = Appointment.objects.filter(doctor=doctor)
        events = [
            {
                "title": f"Appointment with {app.patient.username if app.patient else app.name}",
                "start": f"{app.date}T{app.time}",
                "url": app.video_call_link or app.voice_call_link or "#",
            }
            for app in appointments
        ]
        return JsonResponse(events, safe=False)
    except Doctor.DoesNotExist:
        return JsonResponse({"error": "Doctor not found"}, status=404)


@login_required(login_url="login")
def schedule_appointment(request):
    if request.method == "POST":
        try:
            patient_id = request.POST.get("patient_id")
            date = request.POST.get("date")
            time = request.POST.get("time")
            department = request.POST.get("department")

            if not all([patient_id, date, time, department]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            patient = CustomUser.objects.get(id=patient_id, role="patient")
            doctor = Doctor.objects.get(user=request.user)

            Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                date=date,
                time=time,
                department=department,
                name=patient.username,
                email=patient.email,
            )
            messages.success(request, "Appointment scheduled successfully.")
            return redirect("doctor_dashboard")
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect("doctor_dashboard")
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect("doctor_dashboard")
        except Exception as e:
            messages.error(request, f"Error scheduling appointment: {str(e)}")
            return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
@user_passes_test(is_admin)
def get_all_appointments(request):
    try:
        appointments = Appointment.objects.select_related("patient", "doctor").all()
        events = [
            {
                "id": appointment.id,
                "title": f"{appointment.patient.user.username} with {appointment.doctor.user.username}",
                "start": f"{appointment.date}T{appointment.time}",
                "end": f"{appointment.date}T{appointment.time}",
                "extendedProps": {"department": appointment.department},
            }
            for appointment in appointments
        ]
        return JsonResponse(events, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Call Notification Views
@login_required(login_url="login")
def notify_doctor(request, appointment_id, call_type):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if not (request.user == appointment.patient or request.user.role == "admin"):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect("home")

    subject = (
        f"Patient {appointment.name or appointment.patient.username} {'Joined Video Call' if call_type == 'video' else 'is Calling'}"
    )
    body = (
        f"Meet Link: {appointment.video_call_link}" if call_type == "video" else f"Phone: {appointment.phone}"
    )

    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(doctor_email, subject, body)

    redirect_url = appointment.video_call_link if call_type == "video" else f"tel:{appointment.phone}"
    return redirect(redirect_url)


@login_required(login_url="login")
def notify_doctor_video_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if not (
        request.user == appointment.patient
        or request.user == appointment.doctor.user
        or request.user.role == "admin"
    ):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect("home")

    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(
            doctor_email,
            f"Patient {appointment.name or appointment.patient.username} Joined Video Call",
            f"Meet Link: {appointment.video_call_link}",
        )

    return redirect(appointment.video_call_link)


@login_required(login_url="login")
def notify_doctor_voice_call(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if not (
        request.user == appointment.patient
        or request.user == appointment.doctor.user
        or request.user.role == "admin"
    ):
        messages.error(request, "You don't have permission to initiate this call.")
        return redirect("home")

    doctor_email = get_doctor_email(appointment.doctor)
    if doctor_email:
        send_email_notification(
            doctor_email,
            f"Patient {appointment.name or appointment.patient.username} is Calling",
            f"Phone: {appointment.phone}",
        )

    return redirect(f"tel:{appointment.phone}")


def start_video_call(request):
    return render(request, "start_video_call.html")


def start_voice_call(request):
    return render(request, "start_voice_call.html")


# Patient Referral Views
@login_required(login_url="login")
def refer_patient(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can refer patients.")
        return redirect("home")

    try:
        referring_doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You don't have a doctor profile.")
        return redirect("home")

    if request.method == "POST":
        post_data = request.POST.copy()
        post_data["referring_doctor"] = referring_doctor.id
        form = PatientReferralForm(post_data)
        if form.is_valid():
            try:
                referral = form.save(commit=False)
                referral.referring_doctor = referring_doctor
                referral.status = "pending"
                referral.save()

                referred_doctor = referral.referred_doctor
                if referred_doctor and hasattr(referred_doctor, "user") and referred_doctor.user.email:
                    send_email_notification(
                        referred_doctor.user.email,
                        "Check New Patient Referral",
                        f"You have Successfully received a patient referral from Dr. {referring_doctor.user.get_full_name() or referring_doctor.user.username}.",
                    )

                messages.success(request, "Patient referred successfully!")
                return redirect("doctor_dashboard")
            except Exception as e:
                messages.error(request, f"Error referring patient: {str(e)}")
        else:
            messages.error(request, "Please correct the details of the patient correctly.")
            print(f"Form errors: {form.errors}")
    else:
        form = PatientReferralForm(initial={"referring_doctor": referring_doctor.id})

    patients = CustomUser.objects.filter(role="patient")
    doctors = Doctor.objects.exclude(user=request.user)
    return render(request, "refer_patient.html", {
        "form": form,
        "patients": patients,
        "doctors": doctors,
    })


@login_required(login_url="login")
def update_referral_status(request, referral_id):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can update referral statuses.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "You don't have a doctor profile.")
        return redirect("home")

    if request.method == "POST":
        referral_obj = get_object_or_404(PatientReferral, id=referral_id)
        new_status = request.POST.get("status")

        if new_status not in ["pending", "accepted", "rejected"]:
            messages.error(request, "Invalid status value.")
            return redirect("doctor_dashboard")

        if referral_obj.referred_doctor != doctor:
            messages.error(request, "You can only update referrals that were sent to you.")
            return redirect("doctor_dashboard")

        old_status = referral_obj.status
        referral_obj.status = new_status
        referral_obj.save()

        referring_doctor = referral_obj.referring_doctor
        if referring_doctor and hasattr(referring_doctor, "user") and referring_doctor.user.email:
            try:
                send_mail(
                    f"Patient Referral Status Updated to {new_status.capitalize()}",
                    f"The referral you made has been {new_status} by Dr. {doctor.user.get_full_name() or doctor.user.username}.",
                    settings.DEFAULT_FROM_EMAIL,
                    [referring_doctor.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending error: {str(e)}")

        messages.success(request, f"Referral status updated from {old_status} to {new_status}.")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def view_outgoing_referrals(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can view outgoing referrals.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("home")

    outgoing_referrals = PatientReferral.objects.filter(referring_doctor=doctor).order_by("-created_at")
    return render(request, "view_outgoing_referrals.html", {"referrals": outgoing_referrals})


@login_required(login_url="login")
def view_incoming_referrals(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can view incoming referrals.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("home")

    incoming_referrals = PatientReferral.objects.filter(referred_doctor=doctor).order_by("-created_at")
    pending_referrals = incoming_referrals.filter(status="pending")
    accepted_referrals = incoming_referrals.filter(status="accepted", is_treated=False)
    treated_referrals = incoming_referrals.filter(status="accepted", is_treated=True)
    rejected_referrals = incoming_referrals.filter(status="rejected")

    # Attach medical records (optional enhancement)
    for referral in list(pending_referrals) + list(accepted_referrals) + list(treated_referrals):
        referral.medical_record = MedicalRecord.objects.filter(patient=referral.patient).last()

    return render(request, "view_incoming_referrals.html", {
        "pending_referrals": pending_referrals,
        "accepted_referrals": accepted_referrals,
        "treated_referrals": treated_referrals,
        "rejected_referrals": rejected_referrals,
    })



@login_required(login_url="login")
def check_treatment_status(request):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            referral_ids = json.loads(request.POST.get("referral_ids", "[]"))
            treated_referrals = PatientReferral.objects.filter(
                id__in=referral_ids, is_treated=True
            ).values_list("id", flat=True)
            return JsonResponse({
                "status": "success",
                "treated_referrals": list(treated_referrals),
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required(login_url="login")
def treat_referred_patient(request, referral_id):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can treat referred patients.")
        return redirect("home")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.error(request, "The Doctor profile not found.")
        return redirect("home")

    try:
        referral = PatientReferral.objects.get(id=referral_id)
    except PatientReferral.DoesNotExist:
        messages.error(request, f"No referral found with ID {referral_id}")
        return redirect("doctor_dashboard")

    if not referral.patient:
        messages.error(request, "This referral has no patient associated with it!")
        return redirect("view_incoming_referrals")

    if referral.referred_doctor != doctor:
        messages.error(request, "You can only treat patients referred to you.")
        return redirect("doctor_dashboard")

    if referral.status != "accepted":
        messages.error(request, "You must accept the referral before treating the patient.")
        return redirect("view_incoming_referrals")

    if request.method == "POST":
        diagnosis = request.POST.get("diagnosis", "")
        medication = request.POST.get("medication", "")

        if not diagnosis or not medication:
            messages.error(request, "Both diagnosis and medication are required.")
        else:
            try:
                medical_record = MedicalRecord(
                    patient=referral.patient,
                    doctor=doctor,
                    diagnosis=diagnosis,
                    medication=medication,
                    referral=referral,
                )
                medical_record.save()

                referral.is_treated = True
                referral.save()

                try:
                    referring_doctor = referral.referring_doctor
                    if referring_doctor and hasattr(referring_doctor, "user") and referring_doctor.user.email:
                        send_mail(
                            f"Patient Treatment Update: {referral.patient.get_full_name() or referral.patient.username}",
                            f"Your referred patient has been treated by Dr. {doctor.user.get_full_name() or doctor.user.username}.\n\nDiagnosis: {diagnosis}\n\nMedication: {medication}",
                            settings.DEFAULT_FROM_EMAIL,
                            [referring_doctor.user.email],
                            fail_silently=True,
                        )
                except Exception as e:
                    print(f"Email sending error: {str(e)}")

                messages.success(request, "The Medical record have been created for referred patient!")
                return redirect("view_incoming_referrals")
            except Exception as e:
                import traceback
                print(f"Error creating record: {str(e)}")
                print(traceback.format_exc())
                messages.error(request, f"Error: {str(e)}")

    context = {"referral": referral, "patient": referral.patient, "doctor": doctor}
    return render(request, "treat_referred_patient.html", context)


# Prescription Views
@login_required(login_url="login")
def add_prescription(request):
    if request.method == "POST":
        try:
            patient_id = request.POST.get("patient")
            medication = request.POST.get("medication")
            dosage = request.POST.get("dosage")
            frequency = request.POST.get("frequency")
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")

            if not all([patient_id, medication, dosage, frequency, start_date, end_date]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            patient = CustomUser.objects.get(id=patient_id, role="patient")
            doctor = Doctor.objects.get(user=request.user)

            Prescription.objects.create(
                patient=patient,
                doctor=doctor,
                medication=medication,
                dosage=dosage,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            )
            messages.success(request, "Prescription added successfully.")
            return redirect("doctor_dashboard")
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect("doctor_dashboard")
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect("doctor_dashboard")
        except Exception as e:
            messages.error(request, f"Error adding prescription: {str(e)}")
            return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def delete_prescription(request, prescription_id):
    if request.method == "POST":
        try:
            prescription = Prescription.objects.get(id=prescription_id, doctor__user=request.user)
            prescription.delete()
            messages.success(request, "Prescription deleted successfully.")
        except Prescription.DoesNotExist:
            messages.error(request, "Prescription not found.")
        return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def edit_prescription(request):
    if request.method == "POST":
        try:
            prescription_id = request.POST.get("prescription_id")
            medication = request.POST.get("medication")
            dosage = request.POST.get("dosage")
            frequency = request.POST.get("frequency")
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")

            if not all([prescription_id, medication, dosage, frequency, start_date, end_date]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            prescription = Prescription.objects.get(id=prescription_id, doctor__user=request.user)
            prescription.medication = medication
            prescription.dosage = dosage
            prescription.frequency = frequency
            prescription.start_date = start_date
            prescription.end_date = end_date
            prescription.save()
            messages.success(request, "Prescription updated successfully.")
        except Prescription.DoesNotExist:
            messages.error(request, "Prescription not found.")
        except Exception as e:
            messages.error(request, f"Error updating prescription: {str(e)}")
        return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def get_prescription(request, prescription_id):
    try:
        prescription = Prescription.objects.get(id=prescription_id, doctor__user=request.user)
        data = {
            "medication": prescription.medication,
            "dosage": prescription.dosage,
            "frequency": prescription.frequency,
            "start_date": prescription.start_date.strftime("%Y-%m-%d"),
            "end_date": prescription.end_date.strftime("%Y-%m-%d"),
        }
        return JsonResponse(data)
    except Prescription.DoesNotExist:
        return JsonResponse({"error": "Prescription not found"}, status=404)


# Patient Note Views
@login_required(login_url="login")
def add_note(request):
    if request.method == "POST":
        try:
            patient_id = request.POST.get("patient")
            content = request.POST.get("content")

            if not all([patient_id, content]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            patient = CustomUser.objects.get(id=patient_id, role="patient")
            doctor = Doctor.objects.get(user=request.user)

            PatientNote.objects.create(patient=patient, doctor=doctor, content=content)
            messages.success(request, "Note added successfully.")
            return redirect("doctor_dashboard")
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect("doctor_dashboard")
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect("doctor_dashboard")
        except Exception as e:
            messages.error(request, f"Error adding note: {str(e)}")
            return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def edit_note(request):
    if request.method == "POST":
        try:
            note_id = request.POST.get("note_id")
            content = request.POST.get("content")

            if not all([note_id, content]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            note = PatientNote.objects.get(id=note_id, doctor__user=request.user)
            note.content = content
            note.save()
            messages.success(request, "Note updated successfully.")
        except PatientNote.DoesNotExist:
            messages.error(request, "Note not found.")
        except Exception as e:
            messages.error(request, f"Error updating note: {str(e)}")
        return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


@login_required(login_url="login")
def delete_note(request, note_id):
    if request.method == "POST":
        try:
            note = PatientNote.objects.get(id=note_id, doctor__user=request.user)
            note.delete()
            messages.success(request, "Note deleted successfully.")
        except PatientNote.DoesNotExist:
            messages.error(request, "Note not found.")
        return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


# Lab Result Views
@login_required(login_url="login")
def add_lab_result(request):
    if request.method == "POST":
        try:
            patient_id = request.POST.get("patient_id")
            test_name = request.POST.get("test_name")
            result_value = request.POST.get("result_value")
            test_date = request.POST.get("test_date")
            status = request.POST.get("status")

            if not all([patient_id, test_name, result_value, test_date, status]):
                messages.error(request, "All fields are required.")
                return redirect("doctor_dashboard")

            patient = CustomUser.objects.get(id=patient_id, role="patient")
            doctor = Doctor.objects.get(user=request.user)

            LabResult.objects.create(
                patient=patient,
                doctor=doctor,
                test_name=test_name,
                result_value=result_value,
                test_date=test_date,
                status=status,
            )
            messages.success(request, "Lab result added successfully.")
            return redirect("doctor_dashboard")
        except CustomUser.DoesNotExist:
            messages.error(request, "Selected patient does not exist.")
            return redirect("doctor_dashboard")
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor profile not found.")
            return redirect("doctor_dashboard")
        except Exception as e:
            messages.error(request, f"Error adding lab result: {str(e)}")
            return redirect("doctor_dashboard")
    return redirect("doctor_dashboard")


# Patient History Views
@login_required(login_url="login")
def get_patient_history(request):
    patient_id = request.GET.get("patient_id")
    try:
        patient = CustomUser.objects.get(id=patient_id, role="patient")
        history = PatientHistory.objects.filter(patient=patient)
        data = [
            {
                "event_type": h.event_type,
                "description": h.description,
                "created_at": h.created_at.strftime("%b %d, %Y"),
                "patient": h.patient.username,
            }
            for h in history
        ]
        return JsonResponse(data, safe=False)
    except CustomUser.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)


# Authentication Check
def is_admin(user):
    return user.is_superuser

@login_required(login_url="login")
@user_passes_test(is_admin)
def admin_dashboard(request):
    username_filter = request.GET.get("username", "")
    role_filter = request.GET.get("role", "")

    users = CustomUser.objects.all()  # Changed from User to CustomUser
    if username_filter:
        users = users.filter(username__icontains=username_filter)
    if role_filter:
        if role_filter == "patient":
            users = users.filter(role="patient")
        elif role_filter == "doctor":
            users = users.filter(doctor__isnull=False)

    appointments = Appointment.objects.all().select_related("patient", "doctor")
    referrals = PatientReferral.objects.all().select_related("patient", "referring_doctor", "referred_doctor")  # Changed to PatientReferral
    patients = CustomUser.objects.filter(role="patient")  # Changed from Patient
    doctors = Doctor.objects.all().select_related("user")

    context = {
        "users": users,
        "appointments": appointments,
        "referrals": referrals,
        "patients": patients,
        "doctors": doctors,
    }
    return render(request, "admin_dashboard.html", context)

@login_required(login_url="login")
@user_passes_test(is_admin)
@transaction.atomic
def add_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")

        if not all([username, email, password, role]):
            messages.error(request, "All fields are required.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        if CustomUser.objects.filter(username=username).exists():  # Changed from User
            messages.error(request, "Username already exists.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        if CustomUser.objects.filter(email=email).exists():  # Changed from User
            messages.error(request, "Email already exists.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        if role not in ["patient", "doctor"]:
            messages.error(request, "Invalid role selected.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        try:
            user = CustomUser.objects.create_user(  # Changed from User
                username=username,
                email=email,
                password=password,
                role=role,  # Set role directly
            )
            if role == "doctor":  # Create Doctor profile for doctors
                Doctor.objects.create(user=user)

            messages.success(request, f"User {username} created successfully.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

    return redirect("admin_dashboard")

@login_required(login_url="login")
@user_passes_test(is_admin)
@transaction.atomic
def edit_user(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        username = request.POST.get("username")
        email = request.POST.get("email")
        role = request.POST.get("role")

        if not all([user_id, username, email, role]):
            messages.error(request, "All fields are required.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        if role not in ["patient", "doctor"]:
            messages.error(request, "Invalid role selected.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

        try:
            user = CustomUser.objects.get(id=user_id)  # Changed from User
            if CustomUser.objects.filter(username=username).exclude(id=user_id).exists():
                messages.error(request, "Username already exists.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

            if CustomUser.objects.filter(email=email).exclude(id=user_id).exists():
                messages.error(request, "Email already exists.")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

            user.username = username
            user.email = email
            user.role = role  # Update role
            user.save()

            has_doctor_profile = hasattr(user, "doctor")

            if role == "patient" and has_doctor_profile:
                user.doctor.delete()  # Remove doctor profile if switching to patient
            elif role == "doctor" and not has_doctor_profile:
                Doctor.objects.create(user=user)  # Create doctor profile if switching to doctor

            messages.success(request, f"User {username} updated successfully.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

    return redirect("admin_dashboard")

@login_required(login_url="login")
@user_passes_test(is_admin)
@transaction.atomic
def delete_user(request, user_id):
    if request.method == "POST":
        try:
            user = CustomUser.objects.get(id=user_id)  # Changed from User
            username = user.username
            user.delete()
            messages.success(request, f"User {username} deleted successfully.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found.")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
        except Exception as e:
            messages.error(request, f"Error deleting user: {str(e)}")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

@login_required(login_url="login")
@user_passes_test(is_admin)
def get_user(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)  # Changed from User
        return JsonResponse({
            "username": user.username,
            "email": user.email,
            "role": user.role,
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required(login_url="login")
@user_passes_test(is_admin)
def generate_system_report(request):
    if pdfkit is None:
        messages.error(request, "PDF generation is unavailable. Please install pdfkit.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))

    try:
        total_users = CustomUser.objects.count()  # Changed from User
        total_patients = CustomUser.objects.filter(role="patient").count()  # Changed from Patient
        total_doctors = Doctor.objects.count()
        total_appointments = Appointment.objects.count()
        total_referrals = PatientReferral.objects.count()  # Changed to PatientReferral
        pending_referrals = PatientReferral.objects.filter(status="pending").count()

        context = {
            "total_users": total_users,
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "total_appointments": total_appointments,
            "total_referrals": total_referrals,
            "pending_referrals": pending_referrals,
            "report_date": datetime.now().strftime("%B %d, %Y"),
        }

        html_string = render_to_string("system_report.html", context)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="system_report.pdf"'

        config = (
            pdfkit.configuration(wkhtmltopdf="C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe")
            if "win" in sys.platform
            else None
        )
        pdfkit.from_string(html_string, response, configuration=config)
        return response
    except Exception as e:
        messages.error(request, f"Error generating report: {str(e)}")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin-dashboard/"))
    
def get_departments(request):
    departments = Doctor.SPECIALTY_CHOICES
    return JsonResponse({'departments': list(departments)})


from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import PatientReferral, MedicalRecord

def get_treatment_details(request):
    referral_id = request.GET.get("referral_id")
    try:
        referral = PatientReferral.objects.get(id=referral_id)
        records = MedicalRecord.objects.filter(patient=referral.patient).order_by("-created_at")
        html = render_to_string("partials/treatment_modal_content.html", {
            "records": records,
            "referral": referral,
        })
        title = f"Treatment Details for {referral.patient.get_full_name() if hasattr(referral.patient, 'get_full_name') else referral.patient.username}"
        return JsonResponse({"html": html, "title": title})
    except PatientReferral.DoesNotExist:
        return JsonResponse({"html": "<p>Referral not found.</p>", "title": "Error"})
    
    
    

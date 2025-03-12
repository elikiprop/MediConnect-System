from django.db import models

class Appointment(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    department = models.CharField(max_length=255)
    doctor = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    google_meet_link = models.URLField(default="https://meet.google.com/bdu-vfen-nwx")  #  Default Meet link

    def __str__(self):
        return f"{self.name} - {self.doctor} - {self.date}"

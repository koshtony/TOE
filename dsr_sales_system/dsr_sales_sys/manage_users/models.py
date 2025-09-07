from django.db import models
from django.contrib.auth.models import AbstractUser,Group, Permission
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUser(AbstractUser):
    # Role choices
    ROLE_CHOICES = (
        ("manager", "Manager"),
        ("admin", "Admin"),
        ("sales", "sales"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="sales")
    is_activated = models.BooleanField(default=False)
    date_of_registration = models.DateTimeField(default=timezone.now)  # ✅ auto timestamp
    
    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_set",
        blank=True,
        help_text="Specific permissions for this user.",
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
    

class Profile(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("---", "---"),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    # Employee details
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, unique=True) 
    date_of_joining = models.DateField(null=True, blank=True) 
    gender = models.CharField(max_length=20, blank=True, null=True, choices=GENDER_CHOICES)
    region = models.CharField(max_length=100, blank=True, null=True)
    

    # Uploads
    id_document = models.FileField(upload_to="profile/ids/", blank=True, null=True)
    photo = models.ImageField(upload_to="profile/photos/", blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
    

class CompanyProfile(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # ensures profile updates if already exists
        instance.profile.save()

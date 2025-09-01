from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Profile,CompanyProfile


# Customizing CustomUser admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # What is shown in the list view
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # Fieldsets for add/edit pages
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone_number")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "first_name", "last_name", "phone_number"),
        }),
    )


# Inline profile editor inside user admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


# Attach profile inline to CustomUser admin
CustomUserAdmin.inlines = [ProfileInline]


# Register Profile separately too (optional, but useful)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username", "user__email",)
    

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")
    search_fields = ("name", "phone", "email")


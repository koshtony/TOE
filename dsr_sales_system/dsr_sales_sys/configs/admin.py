from django.contrib import admin


admin.site.site_header = "Decoire Group"
admin.site.site_title = "Sales System"
admin.site.index_title = "PSI Management"

from django.contrib import admin
from django.contrib.admin.sites import AdminSite

class CustomAdminSite(AdminSite):
    site_header = "Your Company Admin"
    site_title = "Your Company"
    index_title = "Dashboard"

    def each_context(self, request):
        context = super().each_context(request)
        context['custom_admin_css'] = 'assets/css/admin_custom.css'
        return context

admin_site = CustomAdminSite(name="custom_admin")
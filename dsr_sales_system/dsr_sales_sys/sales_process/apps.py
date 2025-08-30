from django.apps import AppConfig


class SalesProcessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales_process'
    
    def ready(self):
        import sales_process.signals

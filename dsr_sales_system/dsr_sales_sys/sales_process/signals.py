from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Stock, StockHistory


@receiver(post_save, sender=Stock)
def create_stock_added_history(sender, instance, created, **kwargs):
    """Log when a new stock is added."""
    if created:
        StockHistory.objects.create(
            stock=instance,
            action='added',
            performed_by=instance.added_by,
            details=f"Stock {instance.serial_number} added to inventory."
        )


@receiver(pre_save, sender=Stock)
def track_stock_changes(sender, instance, **kwargs):
    """Track changes like assignment and status updates."""
    if not instance.pk:
        return  # Skip new objects (handled in post_save)

    old_instance = Stock.objects.get(pk=instance.pk)

    # Track assignment changes
    if old_instance.assigned_to != instance.assigned_to:
        if instance.assigned_to:  # newly assigned
            instance.last_assigned_date = timezone.now().date()
            StockHistory.objects.create(
                stock=instance,
                action='assigned',
                performed_by=instance.added_by,  # you could use request.user in views instead
                details=f"Assigned to {instance.assigned_to}."
            )
        else:  # unassigned
            StockHistory.objects.create(
                stock=instance,
                action='returned',
                performed_by=instance.added_by,
                details="Returned to stock (unassigned)."
            )

    # Track status changes
    if old_instance.status != instance.status:
        StockHistory.objects.create(
            stock=instance,
            action='status_change',
            performed_by=instance.added_by,
            details=f"Status changed from {old_instance.status} to {instance.status}."
        )

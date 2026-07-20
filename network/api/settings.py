import frappe


@frappe.whitelist()
def get_settings():
    settings = frappe.get_single("Network Monitor Settings")

    return {
        "enabled": settings.enabled,
        "monitor_interval": settings.monitoring_interval_seconds,
        "ping_timeout": settings.ping_timeout,
        "retry_count": settings.retry_count,
        "retry_delay": settings.retry_delay,
        "packets_per_check": settings.packets_per_check,
        "max_workers": settings.max_workers,
        "queue_batch_size": settings.queue_batch_size,
        "logging_mode": settings.check_logging_mode,
        "log_level": settings.log_level,
        "notifications_enabled": settings.enable_notifications,
        "notification_cooldown": settings.notification_cooldown,
        "keep_logs_days": settings.keep_logs_days,

    }
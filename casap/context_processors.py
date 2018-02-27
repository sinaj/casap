from casap.models import Alerts


def add_variable_to_context(request):
    alerts = Alerts.objects.filter(sent=False)
    alerts = list(alerts)
    return {
        'alert_len': len(alerts)
    }

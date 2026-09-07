from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .selectors import (
    get_dashboard_metrics,
    get_products_requiring_attention,
    get_recent_movements,
)


@login_required
def dashboard(request):
    context = {
        "metrics": get_dashboard_metrics(),
        "attention_products": get_products_requiring_attention(),
        "recent_movements": get_recent_movements(),
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def custom_404(request, exception):
    return render(request, "configs/404.html", status=404)

def custom_500(request):
    return render(request, "configs/500.html", status=500)

def custom_403(request, exception):
    return render(request, "configs/403.html", status=403)

def custom_400(request, exception):
    return render(request, "configs/400.html", status=400)
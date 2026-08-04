from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def project_view(request):
    
    return render(
        request,
        "notas/project.html"
    )

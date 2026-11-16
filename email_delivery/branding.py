from django.templatetags.static import static


def email_logo_url(request):
    path = static("img/myscoope-email-logo.png")
    return request.build_absolute_uri(path) if request else path

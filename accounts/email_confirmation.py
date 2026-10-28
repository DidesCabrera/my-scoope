from allauth.account.views import ConfirmEmailView
from django.shortcuts import render


class MyScoopeConfirmEmailView(ConfirmEmailView):
    def is_mobile_confirmation(self):
        return self.request.resolver_match.url_name == "mobile_confirm_email"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if not self.is_mobile_confirmation():
            return response

        self.object.email_address.refresh_from_db()
        if not self.object.email_address.verified:
            return response
        return render(request, "account/mobile_email_confirmed.html")

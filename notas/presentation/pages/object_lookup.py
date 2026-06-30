"""Small page-level bridge for object lookup failures.

Presentation page builders sometimes need to load an optional child object
before composing viewmodels (for example an item currently being edited).  The
HTTP boundary still lives in ``interface/views``; this helper centralizes the
legacy 404 bridge so page modules do not import ``django.shortcuts`` directly.
"""

from django.shortcuts import get_object_or_404


def get_page_object_or_404(queryset_or_model, *args, **kwargs):
    """Return one object or raise Django's 404 using a centralized bridge."""

    return get_object_or_404(queryset_or_model, *args, **kwargs)

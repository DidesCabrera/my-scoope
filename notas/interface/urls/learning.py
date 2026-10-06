from django.urls import path

from notas.interface.views.learning import learning_article, learning_catalog, learning_home

urlpatterns = [
    path("fundamentos/", learning_home, name="learning_home"),
    path("fundamentos/<str:kind>/", learning_catalog, name="learning_catalog"),
    path("fundamentos/<str:kind>/<slug:slug>/", learning_article, name="learning_article"),
]

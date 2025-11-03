from django.urls import path

from . import views

urlpatterns = [
    path("", views.display_board, name="display-board"),
    path("leader/", views.leader_panel, name="leader-panel"),
]

from django.urls import path

from . import views

urlpatterns = [
    path("", views.display_board, name="display-board"),
    path("board-data/", views.board_data, name="board-data"),
    path("leader/", views.leader_panel, name="leader-panel"),
]

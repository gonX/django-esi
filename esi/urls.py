from django.urls import re_path

from . import views


app_name = 'esi'

urlpatterns = [
    re_path(r'^callback/$', views.receive_callback, name='callback'),
]

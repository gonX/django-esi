from django.conf.urls import url

from . import views


app_name = 'esi'

urlpatterns = [
    url(r'^callback/$', views.receive_callback, name='callback'),
]

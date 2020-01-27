from django.urls import path

from . import views

app_name = 'esi_test_app'
urlpatterns = [
    path('', views.index, name='index'),    
    path('prepare_api_test', views.prepare_api_test, name='prepare_api_test'),
    path('run_api_test', views.run_api_test, name='run_api_test'),
]
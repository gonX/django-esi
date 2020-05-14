from django.urls import path

from . import views

app_name = 'esi_test_app'
urlpatterns = [
    path('', views.index, name='index'),    
    path(
        'test_token_required_1', 
        views.test_token_required_2, 
        name='test_token_required_1'
    ),
    path(
        'test_token_required_2', 
        views.test_token_required_2, 
        name='test_token_required_2'
    ),
    path(
        'test_single_use_token', 
        views.test_single_use_token, 
        name='test_single_use_token'
    ),
    path('run_api_test', views.run_api_test, name='run_api_test'),
]

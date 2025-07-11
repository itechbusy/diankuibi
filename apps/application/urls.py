# from django.conf import settings
from application.views import chunk_views
from application.views import model_views
from django.urls import path

app_name = 'application'

urlpatterns = [
    path('list_models/', model_views.list_models),
    path('create_model/', model_views.create_model),
    path('update_model/', model_views.update_model),
    path('delete_model/', model_views.delete_model),
    path('get_chunk_settings/', chunk_views.get_chunk_settings),
    path('update_chunk_settings/', chunk_views.update_chunk_settings),
]

# from django.conf import settings
from django.urls import path

from .views import file_task_views

app_name = 'task_flow'
urlpatterns = [
    path('get_file_list/', file_task_views.get_file_list),
    path('document_format_conversion/', file_task_views.document_format_conversion),
    path('document_combination/', file_task_views.document_combination),
    path('query_task_status/', file_task_views.query_task_status),
    path('query_result_list/', file_task_views.query_result_list),
    path('file_download/', file_task_views.file_download),
    path('read_file_content/', file_task_views.read_file_content),
]

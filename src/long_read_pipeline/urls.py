from django.conf.urls import include, url
from .views import long_read_home,long_read_status,long_read_retrieve,long_read_result,long_read_report

urlpatterns=[
    url(r'^$',long_read_home,name='long_read_home'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/retrieve$',long_read_retrieve,name='long_read_retrieve'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/status$',long_read_status,name='long_read_status'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/report$',long_read_report,name='long_read_report'),
    url(r'^long_read_result$',long_read_result,name="long_read_result"),
]
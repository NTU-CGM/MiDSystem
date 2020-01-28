from django.conf.urls import include, url
from .views import meta_home,meta_status,meta_retrieve,meta_result,meta_report,merge_sample

urlpatterns=[
    url(r'^$',meta_home,name='meta_home'),
    url(r'^merge_sample$',merge_sample,name='merge_sample'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/retrieve$',meta_retrieve,name='meta_retrieve'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/status$',meta_status,name='meta_status'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/report$',meta_report,name='meta_report'),
    url(r'^meta_result$',meta_result,name="meta_result"),
    


]
from django.conf.urls import include, url
from .views import home,reference_guided,non_ref,non_ref_result,ref_result,status,retrieve,report,test,data_upload,delete_upload,get_tree,confirm_urls,help

urlpatterns=[
    url(r'^$',home,name='home'),   
    url(r'^help$',help,name='help'),       
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/retrieve$',retrieve,name='retrieve'),
    url(r'^get_tree$',get_tree,name='get_tree'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/test$',test,name='test'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/status$',status,name='status'),
    url(r'^(?P<task_id>[0-9a-zA-Z\-]{36})/report$',report,name='report'),
	url(r'^ref_result$',ref_result,name="ref_result"),
	url(r'^non_ref_result$',non_ref_result,name="non_ref_result"),
    url(r'^reference_guided$',reference_guided,name="reference_guided"),
	url(r'^non_ref$',non_ref,name="non_ref"),
    url(r'^data_upload$',data_upload,name="data_upload"),
    url(r'^delete_upload$',delete_upload,name="delete_upload"),
    url(r'^confirm_urls$',confirm_urls,name="confirm_urls"),
]

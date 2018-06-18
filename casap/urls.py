"""casap URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework import routers

from casap import settings
from casap.utilities import vulnerable_info
from casap.utilities.map_data import getData, get_lost_data, get_found_data
from casap.views import views_report, views_dashboard, views, views_registration, views_api

dashboard_patterns = [
    url(r'^profile/edit/$', views_dashboard.profile_edit_view, name="profile_edit"),
    url(r'^volunteer/edit/$', views_dashboard.volunteer_edit_view, name="volunteer_edit"),
    url(r'^vulnerable/list/$', views_dashboard.vulnerable_list_view, name="vulnerable_list"),
    url(r'^vulnerable/add/$', views_dashboard.vulnerable_add_view, name="vulnerable_add"),
    url(r'^vulnerable/edit/(?P<hash>[\w\d]+)/$', views_dashboard.vulnerable_edit_view, name="vulnerable_edit"),
    url(r'^vulnerable/delete/(?P<hash>[\w\d]+)/$', views_dashboard.vulnerable_delete_view, name="vulnerable_delete"),
    url(r'^vulnerable/history/(?P<hash>[\w\d]+)/$', views_dashboard.vulnerable_history_view, name="vulnerable_history"),
    url(r'^manage-notifications/', views_dashboard.manage_notifications_view, name="manage_notifications"),
]

register_patterns = [
    url(r'^login/$', views_registration.login_view, name="login"),
    url(r'^logout/$', views_registration.logout_view, name="logout"),
    url(r'^register/$', views_registration.register_view, name="register"),
    url(r'^register/volunteer/$', views_registration.register_volunteer_view, name="register_volunteer"),
    url(r'^confirm-email/$', views_registration.confirm_email_view, name="email_confirm"),
    url(r'^password/forgot/$', views_registration.password_forgot, name="password_forgot"),
    url(r'^password/reset/$', views_registration.password_reset, name="password_reset"),
]

report_patterns = [
    url(r'^lost/$', views_report.report_lost_view, name="report_lost"),
    url(r'^sighting/(?P<hash>[\w\d]+)/$', views_report.report_sighting_view, name="report_sighting"),
    url(r'^found/(?P<hash>[\w\d]+)/$', views_report.report_found_view, name="report_found"),
    url(r'^alert-list', views_report.alert_list_view, name="alert_list"),
    url(r'^alert/(?P<hash>[\w\d]+)/$', views_report.alert_view, name="report_alert"),
]

# API routes
router = routers.DefaultRouter()
router.register(r'users', views_api.UserViewSet)
router.register(r'profiles', views_api.ProfileViewSet)
router.register(r'volunteers', views_api.VolunteerViewSet)
router.register(r'volunteer_availability', views_api.VolunteerAvailabilityViewSet)
router.register(r'vulnerable', views_api.VulnerableViewSet)
router.register(r'vulnerable_address', views_api.VulnerableAddressViewSet)
router.register(r'lost_person_record', views_api.LostPersonRecordViewSet)
router.register(r'find_record', views_api.FindRecordViewSet)

urlpatterns = [
    url(r'^$', views.index),
    url(r'^home/$', views.index, name="index"),
    url(r'^report/', include(report_patterns)),
    url(r'^track/(?P<hash>[\w\d]+)/$', views.track_missing_view, name="track_missing"),
    url(r'^show/(?P<hash>[\w\d]+)/$', views.show_missing_view, name="show_missing"),
    url(r'^accounts/', include(register_patterns)),
    url(r'^dashboard/', include(dashboard_patterns)),
    url(r'^admin/', admin.site.urls),
    url(r'^location/', views.location_view, name="location"),
    url(r'^adminView/', views.admin_view, name="adminView"),
    url(r'^getPath/', getData.getPath),
    url(r'^get-lost-path/', get_lost_data.getPath),
    url(r'^get-found-path/', get_found_data.getPath),
    url(r'^get-vulnerable-info/', vulnerable_info.get_vulnerable),
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^coordinator-settings/', views.admin_settings_view, name='coordinator-settings'),
    url(r'^tips/', views.tips_view, name='tips'),
    url(r'^redirect/', views.show_missing_view, name='redirect')
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from . import views
from django.urls import path

urlpatterns = [
    path('', views.user_login, name="login"),
    path('dashboard/msp', views.msp_dashboard, name="msp_dashboard"),
    path('dashboard/ec', views.ec_dashboard, name="ec_dashboard"),
    path('dashboard/ep', views.ep_dashboard, name="ep_dashboard"),
    path('dashboard/rp', views.rp_dashboard, name="rp_dashboard"),
    path(
        'dashboard/support',
        views.support_dashboard,
        name="support_dashboard"),
    path('dashboard/dispatch', views.dispatch, name="dispatch"),
    path(
        'dashboard/dispatch-details/<int:pk>/',
        views.dispatch_detail, name='dispatch_detail'),
    path('presentation/', views.plots_visualization, name='presentation'),
    path('logout/', views.logout_user, name='logout'),
    path(
        'dashboard/redirect',
        views.redirect_to_dashboard,
        name='redirect_to_dashboard'),
    path('pdf/', views.redirect_to_dashboard, name='pdf_gen'),
    path('average/sla/', views.average_sla, name='average_sla'),
    path("export/dispatches/excel/", views.export_dispatches_excel, name="export_dispatches_excel"),
]

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    #----------- AUTHENTIFICATION ------------
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
    path('parrainage/', views.parrainage, name='parrainage'),
    #----------- DASHBOARD CLIENT-------------
    path('dashboard/', views.dashboard, name='dashboard'),
    #----------- PRODUITS --------------
    path('produits/', views.liste_produits, name='liste_produits'),
    path('produit/<int:produit_id>/', views.detail_produit, name='detail_produit'),
    #----------- DEPOT & RETRAIT -----------
    path('depot/', views.depot, name='depot'),
    path('retrait/', views.retrait, name='retrait'),
    #------------ ADMIN ------------------
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('depot/valider/<int:depot_id>/', views.valider_depot, name='valider_depot'),
    path('depot/refuser/<int:depot_id>/', views.refuser_depot, name='refuser_depot'),
    path('retrait/valider/<int:retrait_id>/', views.valider_retrait, name='valider_retrait'),
    path('refuser-retrait/<int:retrait_id>/', views.refuser_retrait, name='refuser_retrait'),
    path('create-admin/', views.create_admin),
    path('test_cloudinary/', views.test_cloudinary, name='test_cloudinary'),
]

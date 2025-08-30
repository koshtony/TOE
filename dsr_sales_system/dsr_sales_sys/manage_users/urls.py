from django.urls import path
from . import views
from .views import register_user,list_users,user_detail,update_user,login_user,update_password,logout_user

urlpatterns = [
    path('register_users/', register_user, name='register-users'),
    path('list_users/', list_users, name='list-users'),
    path('user-detail/<int:user_id>/', user_detail, name='user-detail'),
    path('update-user/<int:user_id>/', update_user, name='update-user'),
    path('update-password/', update_password, name='update-password'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
]
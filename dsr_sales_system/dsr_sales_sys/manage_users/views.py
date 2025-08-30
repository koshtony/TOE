from django.shortcuts import render, redirect,get_object_or_404
from .forms import CustomUserForm, ProfileForm,CustomUserUpdateForm,ProfileUpdateForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .models import CustomUser,Profile
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse


def register_user(request):
    """
    View to register a new user.

    If the request is a POST, it attempts to validate the user and profile
    forms. If both are valid, it saves the user and profile and returns an
    HttpResponse with a success message.

    If the attempt to save the user and profile fails, it returns an
    HttpResponse with an error message.

    If the request is a GET, it simply renders the user and profile forms
    using the register_users.html template.

    :param request: The request object
    :return: An HttpResponse
    """

    if request.method == "POST":
        user_form = CustomUserForm(request.POST)
        profile_form = ProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            
            try:
                user = user_form.save()
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()
                
                
                
                return HttpResponse(
                    "<div class='alert alert-success'>✅👍👍 User registered successfully!</div>"
                )

            except Exception as e:
                return HttpResponse(
                    f"<div class='alert alert-danger'>❌👎👎 Registration failed: {str(e)}</div>"
                )
        return render(request, "manage_users/register_users.html", {
            "user_form": user_form,
            "profile_form": profile_form
        })  
    else:
        user_form = CustomUserForm()
        profile_form = ProfileForm()
    
    return render(request, "manage_users/register_users.html", {
        "user_form": user_form,
        "profile_form": profile_form
    })
    
def list_users(request):
    
    """
    List all registered users ordered by date of registration in descending order.
    
    :param request:
    :return:
    """
    users = CustomUser.objects.select_related("profile").all().order_by("-date_of_registration")
    
    context = {
        "users": users
    }
    
    return render(request, "manage_users/list_users.html",context)

def user_detail(request, user_id):
    """
    Display the details of the given user.

    This view is meant to be accessed via AJAX. The URL is of the form
    `user-detail/<user_id>`. The view renders the template
    `manage_users/user_detail.html` with the user and its profile object as
    context.
    """
    user = get_object_or_404(CustomUser, id=user_id)
    profile = getattr(user, "profile", None)  # safe fetch
    return render(request, "manage_users/user_detail.html", {
        "user": user,
        "profile": profile,
    })
    
def update_user(request, user_id):
    
    user = get_object_or_404(CustomUser, id=user_id)
    profile = getattr(user, "profile", None)

    if request.method == "POST":
        user_form = CustomUserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return HttpResponse("<div class='alert alert-success'>✅ User updated successfully</div>")
        else:
            return render(request, "manage_users/update_user.html", {
                "user_form": user_form,
                "profile_form": profile_form,
                "user": user,
            })

    else:
        user_form = CustomUserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, "manage_users/update_user.html", {
        "user_form": user_form,
        "profile_form": profile_form,
        "user": user,
    })
    
def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                response = HttpResponse()
                response['HX-Redirect'] = "/"   # 👈 redirects to home page
                return response
            else:
                return HttpResponse("<div class='alert alert-danger'>❌❌😔 User is Inactive</div>")
        else:
            return HttpResponse("<div class='alert alert-danger'>❌❌😔 Invalid Username or Password</div>")

    return render(request, "manage_users/login.html")

@login_required
def update_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            return HttpResponse("<div class='alert alert-success'>✅ Password updated successfully</div>")
        else:
            # Return form errors as HTML
            errors_html = "".join(
                f"<div class='alert alert-danger'>{err}</div>" for field in form.errors.values() for err in field
            )
            return HttpResponse(errors_html)
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "manage_users/update_password.html", {"form": form})


def logout_user(request):
    logout(request)
    return render(request, "manage_users/logout.html")


    

    


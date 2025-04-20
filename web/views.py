from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from web.forms import RegistrationForm, AuthForm
from web.models import User

def main_view(request):
    return render(request,"web/main.html")

def registration_view(request):
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            user = User(
                username=form.cleaned_data["username"], email=form.cleaned_data["email"]
            )

            user.set_password(form.cleaned_data["password"])
            user.save()
            return redirect("main")

    return render(
        request, "web/registration.html", {"form": form}
    )


def auth_view(request):
    form = AuthForm()
    if request.method == "POST":
        form = AuthForm(data=request.POST)
        if form.is_valid():
            user = authenticate(**form.cleaned_data)
            if user is None:
                form.add_error(None, "Введены неверные данные")
            else:
                login(request, user)
                return redirect("main")

    print("fdfdfdfd")
    return render(request, "web/auth.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("main")
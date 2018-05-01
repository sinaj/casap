from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.messages import add_message
from django.core import exceptions
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.forms import inlineformset_factory, forms

from casap import settings
from casap.forms.forms import UserLoginForm, UserCreateForm, VolunteerForm, Volunteer, VolunteerAvailabilityForm
from casap.models import EmailConfirmationCode, Profile, PasswordResetCode, VolunteerAvailability
from casap.utilities.utils import url_with_params, unquote_redirect_url, SimpleMailHelper, get_address_map_google


@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(request.GET.get(next, reverse("index")))


def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():  # already authenticated in form
            user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password'])
            login(request, user)
            redirect_url = request.POST.get('next', reverse("index"))
            return HttpResponseRedirect(unquote_redirect_url(redirect_url))
        else:
            request.context['next'] = unquote_redirect_url(request.GET.get('next', reverse("index")))
    else:
        request.context['next'] = request.GET.get('next', '')
        form = UserLoginForm()
    request.context['form'] = form
    return render(request, 'registration/login.html', request.context)


def register_view(request):
    if request.method == 'POST':
        next = request.POST.get("next", reverse("index"))
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            user.refresh_from_db()  # load the profile instance created by the signal
            user.email = user.username
            user.save()
            user = authenticate(username=user.username, password=form.cleaned_data.get('password1'))
            login(request, user)
            send_confirmation_email(user)
            return HttpResponseRedirect(url_with_params(next, dict(email=user.email)))
        request.context['next'] = next
    else:
        form = UserCreateForm()
        request.context['next'] = request.GET.get('next', reverse("index"))
    request.context['form'] = form
    return render(request, 'registration/register.html', request.context)


@login_required
def register_volunteer_view(request):
    profile = request.user.profile
    if request.method == "POST":
        availability_formset = inlineformset_factory(Volunteer, VolunteerAvailability,
                                                     form=VolunteerAvailabilityForm, fk_name="volunteer", extra=1)
        item_forms = availability_formset(prefix='volunteers')
        next = request.POST.get("next", reverse("index"))
        if Volunteer.objects.filter(profile=profile).exists():
            form = VolunteerForm(request.POST, instance=profile.volunteer)
        else:
            form = VolunteerForm(request.POST, request.FILES)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.profile = profile

            formset = availability_formset(request.POST, request.FILES, prefix='volunteers')
            if formset.is_valid():
                for f in formset:
                    if f.cleaned_data.get('address'):  # Check if there is a provided address
                        add = f.cleaned_data.get('address')
                        address = get_address_map_google(add)
                        for i in range(10):
                            if address is None:
                                address = get_address_map_google(add)
                            else:
                                break
                        if address is None:
                            messages.error(request, 'Address entered cannot be found.')
                        else:
                            volunteer.save()
                            # Create new windows of availabilities for a volunteer
                            availability = VolunteerAvailability(volunteer=volunteer, address=add,
                                                                 address_lat=address['lat'], address_lng=address['lng'],
                                                                 km_radius=f.cleaned_data['km_radius'])
                            availability.save()
                            add_message(request, messages.SUCCESS, "Volunteer Registration was successful.")
                return HttpResponseRedirect(request.POST.get("next", reverse("index")))

            else:
                # Repeat the code here because is_valid will always fail.
                for f in formset:
                    if f.cleaned_data.get('address'):  # Check if there is a provided address
                        add = f.cleaned_data.get('address')
                        address = get_address_map_google(add)
                        for i in range(10):
                            if address is None:
                                address = get_address_map_google(add)
                            else:
                                break
                        if address is None:
                            messages.error(request, 'Address entered cannot be found.')
                        else:
                            volunteer.save()
                            # Create new windows of availabilities for a volunteer
                            availability = VolunteerAvailability(volunteer=volunteer, address=add,
                                                                 address_lat=address['lat'], address_lng=address['lng'],
                                                                 km_radius=f.cleaned_data['km_radius'])
                            availability.save()
                            add_message(request, messages.SUCCESS, "Volunteer Registration was successful.")
                return HttpResponseRedirect(request.POST.get("next", reverse("index")))
        else:
            messages.error(request, 'Volunteer profile error.')
            return HttpResponseRedirect(request.path_info)
    else:
        availability_formset = inlineformset_factory(Volunteer, VolunteerAvailability,
                                                     form=VolunteerAvailabilityForm, fk_name="volunteer", extra=1)
        item_forms = availability_formset
        request.context['next'] = request.GET.get('next', reverse("index"))
        if Volunteer.objects.filter(profile=profile).exists():
            form = VolunteerForm(instance=profile.volunteer)
        else:
            form = VolunteerForm()
    request.context['formset'] = item_forms
    request.context['form'] = form
    return render(request, 'registration/register_volunteer.html', request.context)


def confirm_email_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if not email:
            add_message(request, messages.ERROR, "Email not found")
        else:
            send_confirmation_email(user)
            add_message(request, messages.SUCCESS, "Confirmation email has been sent.")
    else:
        email = request.GET.get("email")
        code = request.GET.get("code")
        confirmation_code = EmailConfirmationCode.objects.filter(user__email=email, code=code).first()
        if confirmation_code:
            profile = Profile.objects.get(user__email=email)
            profile.email_confirmed = True
            profile.save()
            confirmation_code.delete()
            add_message(request, messages.SUCCESS, "Email confirmed successfully.")
            return HttpResponseRedirect(reverse("index"))
        else:
            add_message(request, messages.WARNING, "Invalid code. Please try again.")
    return render(request, "registration/confirmation_resend.html", request.context)


def send_confirmation_email(user):
    email_code = EmailConfirmationCode.objects.create(user=user, creation_time=timezone.now())
    context = dict(
        domain=settings.DOMAIN,
        url=url_with_params(settings.DOMAIN + reverse("email_confirm"), dict(email=user.email, code=email_code.code)),
    )
    msg_html = str(render_to_string('emails/email_confirmation/email_confirmation.html', context))
    SimpleMailHelper('C-ASAP - Confirm your Email', strip_tags(msg_html), msg_html, user.email).send_email()


def password_forgot(request):
    if request.method == 'POST':
        user = User.objects.filter(email=request.POST.get('email', '')).first()
        if not user:
            add_message(request, messages.ERROR, "Email not found")
            return render(request, 'registration/forgot_password.html', request.context)
        reset_code = PasswordResetCode.objects.create(user=user, creation_time=timezone.now())
        context = dict(
            domain=settings.DOMAIN,
            url=url_with_params(settings.DOMAIN + reverse("password_reset"),
                                dict(email=user.email, code=reset_code.code)),
        )
        msg_html = str(render_to_string('emails/password_reset/password_reset_email.html', context))
        SimpleMailHelper('C-ASAP - Reset your Password', strip_tags(msg_html), msg_html, user.email).send_email()
        add_message(request, messages.SUCCESS, "Password reset code has been sent.")
    return render(request, 'registration/forgot_password.html', request.context)


def password_reset(request):
    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        email = request.POST.get("email")
        user = User.objects.filter(email=email).first()
        if not password1:
            add_message(request, messages.ERROR, "Invalid request. Please try again.")
        elif password1 != password2:
            add_message(request, messages.ERROR, "Passwords do not match. Please try again.")
        elif not user:
            add_message(request, messages.ERROR, "Passwords do not match. Please try again.")
            return HttpResponseRedirect(reverse("password_forgot"))
        else:
            try:
                validate_password(password=password1, user=User)
                user.set_password(password1)
                user.save()
                login(request, user)
                add_message(request, messages.SUCCESS, "Password changed successfully.")
                return HttpResponseRedirect(reverse("index"))
            except exceptions.ValidationError  as e:
                for error in list(e.messages):
                    add_message(request, messages.ERROR, str(error))
        request.context['email'] = email
    else:
        email = request.GET.get("email")
        code = request.GET.get("code")
        reset_code = PasswordResetCode.objects.filter(user__email=email, code=code).first()
        if not reset_code:
            add_message(request, messages.ERROR, "Invalid request. Please try again.")
            return HttpResponseRedirect(reverse("password_forgot"))
        request.context['email'] = email
    return render(request, "registration/password_reset.html", request.context)

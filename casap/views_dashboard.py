from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.forms import modelformset_factory, inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.utils import timezone

from casap.forms import *


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(request)
            user.refresh_from_db()  # load the profile instance created by the signal
            user.email = user.username
            user.save()
            add_message(request, messages.SUCCESS, "Changes saved successfully.")
    else:
        form = UserEditForm(instance=request.user)
        request.context['next'] = request.GET.get('next', reverse("index"))
    request.context['form'] = form
    return render(request, 'dashboard/profile/profile_edit.html', request.context)


@login_required
def volunteer_edit_view(request):
    profile = request.context['user_profile']
    if request.method == "POST":
        next = request.POST.get("next", reverse("index"))
        form = VolunteerForm(request.POST, instance=profile.volunteer)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.profile = profile
            if form.cleaned_data['personal_address']:
                volunteer.personal_lat = form.personal_lat
                volunteer.personal_lng = form.personal_lng
            if form.cleaned_data['business_address']:
                volunteer.business_lat = form.business_lat
                volunteer.business_lng = form.business_lng
            volunteer.save()
            add_message(request, messages.SUCCESS, "Changes saved successfully.")
        request.context['next'] = next
    else:
        request.context['next'] = request.GET.get('next', reverse("index"))
        form = VolunteerForm(instance=profile.volunteer)
    request.context['form'] = form
    return render(request, 'dashboard/profile/volunteer_edit.html', request.context)


@login_required
def vulnerable_list_view(request):
    profile = request.context['user_profile']
    request.context['vulnerable_list'] = profile.vulnerable_people.all()
    return render(request, 'dashboard/vulnerable/vulnerable_list.html', request.context)


@login_required
def vulnerable_add_view(request):
    profile = request.context['user_profile']
    if request.method == "POST":
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress,
                                                fk_name="vulnerable",
                                                fields=('address',),
                                                can_delete=True,
                                                formset=VulnerableAddressFormSet)
        next = request.POST.get("next", reverse("vulnerable_list"))
        vulnerable_form = VulnerableForm(request.POST, request.FILES)
        if vulnerable_form.is_valid():
            vulnerable = vulnerable_form.save(commit=False)
            vulnerable.creator = profile
            if not vulnerable.creation_time:
                vulnerable.creation_time = timezone.now()
            vulnerable.save()
        formset = address_formset(request.POST,
                                  queryset=VulnerableAddress.objects.filter(vulnerable=vulnerable))
        if formset.is_valid():
            for address in formset.save(commit=False):
                address.vulnerable = vulnerable
                address.save()
            a = 10 / 0
            add_message(request, messages.SUCCESS, "Vulnerable added successfully.")
            return HttpResponseRedirect(next)
        else:
            vulnerable.delete()
    else:
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress,
                                                fk_name="vulnerable",
                                                fields=('address',),
                                                extra=1,
                                                can_delete=True,
                                                formset=VulnerableAddressFormSet)
        vulnerable_form = VulnerableForm()
        formset = address_formset(queryset=VulnerableAddress.objects.none())
        next = request.GET.get("next", reverse("vulnerable_list"))
    request.context['next'] = next
    request.context['form'] = vulnerable_form
    request.context['formset'] = formset
    addresses = json.loads("[]")
    for form in formset.forms:
        form_json = json.loads("{}")
        form_json['errors'] = list(form.errors.values())
        form_json['instance_id'] = form.instance.id or None
        form_json['value'] = form['address'].value() or None
        addresses.append(form_json)
    request.context['addresses'] = json.dumps(addresses)
    return render(request, 'dashboard/vulnerable/vulnerable_add.html', request.context)


@login_required
def vulnerable_edit_view(request, hash):
    profile = request.context['user_profile']
    vulnerable = Vulnerable.objects.filter(hash=hash).first()
    if not vulnerable:
        add_message(request, messages.WARNING, "Vulnerable person not found.")
        return HttpResponseRedirect(reverse("vulnerable_list"))

    address_formset = inlineformset_factory(Vulnerable,
                                            VulnerableAddress,
                                            fk_name="vulnerable",
                                            fields=('address',),
                                            extra=5,
                                            can_delete=True,
                                            formset=VulnerableAddressFormSet)
    if request.method == "POST":
        request.context['is_post'] = True
        next = request.POST.get("next", reverse("vulnerable_list"))
        form = VulnerableForm(request.POST, request.FILES, instance=vulnerable)
        if form.is_valid():
            vulnerable = form.save(commit=False)
            vulnerable.creator = profile
            if not vulnerable.creation_time:
                vulnerable.creation_time = timezone.now()
            vulnerable.save()

        formset = address_formset(request.POST, instance=vulnerable)
        for form in formset:
            form.fields['address'].required = False
        if formset.is_valid():
            for address in formset.save(commit=False):
                if address.pk and address.address.strip() == '':
                    address.delete()
                else:
                    address.vulnerable = vulnerable
                    address.save()
            add_message(request, messages.SUCCESS, "Changes saved successfully.")
            return HttpResponseRedirect(next)

    else:
        form = VulnerableForm(instance=vulnerable)
        formset = address_formset(instance=vulnerable)
        next = request.GET.get("next", reverse("vulnerable_list"))
    request.context['next'] = next
    request.context['form'] = form
    request.context['formset'] = formset
    return render(request, 'dashboard/vulnerable/vulnerable_edit.html', request.context)


@login_required
def vulnerable_delete_view(request, hash):
    profile = request.context['user_profile']
    vulnerable = Vulnerable.objects.filter(hash=hash).first()
    if not vulnerable:
        add_message(request, messages.WARNING, "Vulnerable person not found.")
        return HttpResponseRedirect(reverse("vulnerable_list"))
    if vulnerable.creator != profile:
        add_message(request, messages.WARNING, "You cannot delete this person.")
        return HttpResponseRedirect(reverse("vulnerable_list"))
    vulnerable.delete()
    add_message(request, messages.SUCCESS, "Vulnerable person has been deleted successfully.")
    return HttpResponseRedirect(reverse("vulnerable_list"))

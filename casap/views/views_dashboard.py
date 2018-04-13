import datetime
import json
from django.forms import inlineformset_factory, model_to_dict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.forms import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry, WKTWriter

from casap.forms.forms import *


def create_address(request, vulnerable, form):
    if form.cleaned_data.get('street') and form.cleaned_data.get('city') and form.cleaned_data.get('province'):
        address = "{} {} {}".format(form.cleaned_data['street'], form.cleaned_data['city'],
                                    form.cleaned_data['province'])
        loc = get_address_map_google(address)
        for i in range(10):
            if loc is None:
                loc = get_address_map_google(address)
            else:
                break
        if loc is None:
            add_message(request, messages.ERROR, "Problem with the inputted address.")
            vulnerable.delete()
            return render(request, 'dashboard/vulnerable/vulnerable_add.html', request.context)
        else:
            additional_address = VulnerableAddress()
            additional_address.vulnerable = vulnerable
            additional_address.address = address
            additional_address.street = form.cleaned_data['street']
            additional_address.city = form.cleaned_data['city']
            additional_address.province = form.cleaned_data['province']
            additional_address.address_lng = loc['lng']
            additional_address.address_lat = loc['lat']
            additional_address.save()
    else:
        add_message(request, messages.ERROR, "Problem with the inputted address.")
        vulnerable.delete()
        return render(request, 'dashboard/vulnerable/vulnerable_add.html', request.context)


def in_admin_group(user):
    return 'administration' in user.groups


# helper function builds the object for a point location record
def point_map_record(name, feat, point, activity, act_type):
    if act_type == "exit place":
        time = activity.time - datetime.timedelta(0, 1)
    else:
        time = activity.time

    if activity.location:
        person = str(activity.person)
    else:
        person = str(activity.person)
    point_record = {
        'name': str(name),
        'feature': str(feat),
        'time': str(time),
        'locLat': str(point.y),
        'locLon': str(point.x),
        'category': str(activity.category),
        'act_type': str(act_type),
        'person': person,
        'loc': str(activity.activity_type)
    }
    return point_record


# helper function builds the object for a geofence record
def geofence_record(activity, fence, an_activity, time='', person=''):
    if an_activity:
        time = activity.time
        person = str(activity.person)
        category = str([str(cat) for cat in activity.location.category])[1:-1]
        location = activity.location

    else:
        location = activity
        category = str([str(cat) for cat in location.category])[1:-1]
        person = str(activity.person)

    record = {
        'name': str(location.name),
        'id': str(location.id),
        'feature': str(fence),
        'time': str(time),
        'description': str(location.description),
        'act_type': 'geo_fence',
        'category': category.replace("'", ""),
        'person': person,
    }
    return record


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
def manage_notifications_view(request):
    if request.method == "POST":
        notif = Notifications.objects.last()
        form = ManageNotificationsForm(request.POST, initial=model_to_dict(notif))
        if form.is_valid():
            if form.cleaned_data.get('phone_notify'):
                notif.phone_notify = True
            else:
                notif.phone_notify = False
            if form.cleaned_data.get('email_notify'):
                notif.email_notify = True
            else:
                notif.email_notify = False
            if form.cleaned_data.get('twitter_dm_notify'):
                notif.twitter_dm_notify = True
            else:
                notif.twitter_dm_notify = False
            if form.cleaned_data.get('twitter_public_notify'):
                notif.twitter_public_notify = True
            else:
                notif.twitter_public_notify = False
            notif.save()
            add_message(request, messages.SUCCESS, "Notifications successfully updated.")
            return HttpResponseRedirect(reverse("index"))
        else:
            if form.cleaned_data:
                if form.cleaned_data.get('phone_notify'):
                    notif.phone_notify = True
                else:
                    notif.phone_notify = False
                if form.cleaned_data.get('email_notify'):
                    notif.email_notify = True
                else:
                    notif.email_notify = False
                if form.cleaned_data.get('twitter_dm_notify'):
                    notif.twitter_dm_notify = True
                else:
                    notif.twitter_dm_notify = False
                if form.cleaned_data.get('twitter_public_notify'):
                    notif.twitter_public_notify = True
                else:
                    notif.twitter_public_notify = False
                notif.save()
            add_message(request, messages.SUCCESS, "Notifications successfully updated.")
            return HttpResponseRedirect(reverse("index"))

    notif = Notifications.objects.last()
    form = ManageNotificationsForm(initial=model_to_dict(notif))
    request.context['notif'] = notif
    request.context['form'] = form
    return render(request, 'adminManage.html', request.context)


@login_required
def volunteer_edit_view(request):
    profile = request.context['user_profile']
    if request.method == "POST":
        availability_formset = inlineformset_factory(Volunteer, VolunteerAvailability,
                                                     form=VolunteerAvailabilityForm, fk_name="volunteer")
        list_of_avail = VolunteerAvailability.objects.filter(volunteer=profile.volunteer).values()
        item_forms = availability_formset(initial=list_of_avail, prefix='volunteers')
        next = request.POST.get("next", reverse("volunteer_edit"))
        form = VolunteerForm(request.POST, instance=profile.volunteer)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.profile = profile
        formset = availability_formset(request.POST, instance=volunteer)
        formset.is_valid()

        for f in formset:
            if f.cleaned_data.get('street') and f.cleaned_data.get('city') and f.cleaned_data.get(
                    'province') and f.cleaned_data.get('km_radius'):
                add = f.cleaned_data.get('street') + " " + f.cleaned_data.get(
                    'city') + " " + f.cleaned_data.get('province')
                address = get_address_map_google(add)
                for i in range(25):
                    if address is None:
                        address = get_address_map_google(add)
                    else:
                        break
                if address is None:
                    for i in range(25):
                        if address is None:
                            address = get_address_map_google(add)
                        else:
                            break
                if address is None:
                    messages.error(request, 'Address entered cannot be found. Try again')
                    return HttpResponseRedirect(request.path_info)
            elif not f.cleaned_data.get('street') and not f.cleaned_data.get('city') and not f.cleaned_data.get(
                    'province') and not f.cleaned_data.get('km_radius'):
                messages.error(request, 'Empty area of availability entered.')
                return HttpResponseRedirect(request.path_info)
            else:
                messages.error(request, 'Incomplete area of availability entered. Please fill out all fields.')
                return HttpResponseRedirect(request.path_info)

        VolunteerAvailability.objects.filter(volunteer=volunteer).delete()

        for f in formset:
            if f.cleaned_data.get('street') and f.cleaned_data.get('city') and f.cleaned_data.get(
                    'province') and f.cleaned_data.get('km_radius'):  # Check if there is a provided address
                add = f.cleaned_data.get('street') + " " + f.cleaned_data.get(
                    'city') + " " + f.cleaned_data.get('province')
                address = get_address_map_google(add)
                for i in range(25):
                    if address is None:
                        address = get_address_map_google(add)
                    else:
                        break
                if address is None:
                    messages.error(request, 'Address entered cannot be found.')
                else:
                    # Create new windows of availabilities for a volunteer
                    availability = VolunteerAvailability(volunteer=volunteer, address=add,
                                                         street=f.cleaned_data['street'],
                                                         city=f.cleaned_data['city'],
                                                         province=f.cleaned_data['province'],
                                                         address_lat=address['lat'], address_lng=address['lng'],
                                                         km_radius=f.cleaned_data['km_radius'])
                    volunteer.save()
                    availability.save()
            else:
                messages.error(request, 'Please fill out all of the fields.')
                return HttpResponseRedirect(request.path_info)

        request.context['next'] = next
        add_message(request, messages.SUCCESS, "Changes saved successfully.")
        return HttpResponseRedirect(request.POST.get("next", reverse("index")))
    else:
        how_many = len(VolunteerAvailability.objects.filter(volunteer=profile.volunteer).values())
        if how_many == 0:
            how_many = 1
        availability_formset = inlineformset_factory(Volunteer, VolunteerAvailability,
                                                     form=VolunteerAvailabilityForm, fk_name="volunteer",
                                                     extra=how_many)
        list_of_avail = VolunteerAvailability.objects.filter(volunteer=profile.volunteer).values()
        item_forms = availability_formset(initial=list_of_avail, prefix='volunteers')
        request.context['next'] = request.GET.get('next', reverse("index"))
        form = VolunteerForm(instance=profile.volunteer)

    request.context['form'] = form
    request.context['formset'] = item_forms
    return render(request, 'dashboard/profile/volunteer_edit.html', request.context)


@login_required
def vulnerable_list_view(request):
    profile = request.context['user_profile']
    request.context['user'] = profile.user
    if profile.coordinator_email:
        request.context['vulnerable_list'] = Vulnerable.objects.all().order_by('first_name')
    else:
        request.context['vulnerable_list'] = profile.vulnerable_people.all().order_by('first_name')
    return render(request, 'dashboard/vulnerable/vulnerable_list.html', request.context)


@login_required
def vulnerable_history_view(request, hash):
    vulnerable_hash = hash
    person = Vulnerable.objects.filter(hash=hash).first()
    LostPersonName = []
    name = person.first_name + ' ' + person.last_name
    print(name)
    LostPersonName.append(name)

    request.context['LostPersonName'] = LostPersonName
    request.context['Vulnerable'] = Vulnerable

    return render(request, 'dashboard/vulnerable/vulnerable_history.html', request.context)


@login_required
def vulnerable_add_view(request):
    profile = request.context['user_profile']
    if request.method == "POST":
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress, form=VulnerableAddressForm)
        next = request.POST.get("next", reverse("vulnerable_list"))
        vulnerable_form = VulnerableForm(request.POST, request.FILES)
        if vulnerable_form.is_valid():
            vulnerable = vulnerable_form.save(commit=False)
            vulnerable.creator = profile
            if not vulnerable.creation_time:
                vulnerable.creation_time = timezone.now()
            vulnerable.save()
        formset = address_formset(request.POST, queryset=VulnerableAddress.objects.all())
        if formset.is_valid():
            for form in formset:
                create_address(request, vulnerable, form)
            add_message(request, messages.SUCCESS, "Vulnerable added successfully.")
            return HttpResponseRedirect(next)
        else:
            vulnerable.delete()
    else:
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress, form=VulnerableAddressForm, fk_name="vulnerable",
                                                extra=1)
        vulnerable_form = VulnerableForm()
        formset = address_formset(queryset=VulnerableAddress.objects.none())
        next = request.GET.get("next", reverse("vulnerable_list"))
    request.context['next'] = next
    request.context['form'] = vulnerable_form
    request.context['formset'] = formset
    addresses = json.loads("[]")
    # for form in formset.forms:
    #     form_json = json.loads("{}")
    #     form_json['errors'] = list(form.errors.values())
    #     form_json['instance_id'] = form.instance.id or None
    #     form_json['value'] = form['address'].value() or None
    #     addresses.append(form_json)
    # request.context['addresses'] = json.dumps(addresses)
    return render(request, 'dashboard/vulnerable/vulnerable_add.html', request.context)


@login_required
def vulnerable_edit_view(request, hash):
    profile = request.context['user_profile']
    vulnerable = Vulnerable.objects.filter(hash=hash).first()
    if not vulnerable:
        add_message(request, messages.WARNING, "Vulnerable person not found.")
        return HttpResponseRedirect(reverse("vulnerable_list"))

    if request.method == "POST":
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress, form=VulnerableAddressForm, fk_name="vulnerable",
                                                )
        request.context['is_post'] = True
        next1 = request.POST.get("next", reverse("vulnerable_list"))
        form = VulnerableForm(request.POST, request.FILES, instance=vulnerable)
        if form.is_valid():
            vulnerable = form.save(commit=False)
            vulnerable.creator = profile
            if not vulnerable.creation_time:
                vulnerable.creation_time = timezone.now()
            vulnerable.save()

        formset = address_formset(request.POST, instance=vulnerable)
        VulnerableAddress.objects.filter(vulnerable=vulnerable).delete()
        if formset.is_valid():
            for form in formset:
                create_address(request, vulnerable, form)
            add_message(request, messages.SUCCESS, "Vulnerable added successfully.")
            return HttpResponseRedirect(next1)
    else:
        address_list = VulnerableAddress.objects.filter(vulnerable=vulnerable).values()
        how_many = len(address_list)
        if how_many == 0:
            how_many = 1
        address_formset = inlineformset_factory(Vulnerable,
                                                VulnerableAddress, form=VulnerableAddressForm, fk_name="vulnerable",
                                                extra=how_many)
        form = VulnerableForm(instance=vulnerable)
        formset = address_formset(initial=address_list, prefix='addresses')
        next = request.GET.get("next", reverse("vulnerable_list"))
    request.context['next'] = next
    request.context['form'] = form
    request.context['formset'] = formset
    addresses = json.loads("[]")
    # for form in formset.forms:
    #     form_json = json.loads("{}")
    #     form_json['errors'] = list(form.errors.values())
    #     form_json['instance_id'] = form.instance.id or None
    #     form_json['value'] = form['address'].value() or None
    #     addresses.append(form_json)
    # request.context['addresses'] = json.dumps(addresses)
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

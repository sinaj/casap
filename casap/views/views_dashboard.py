import datetime
import json
from django.forms import inlineformset_factory
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry, WKTWriter

from casap.forms.forms import *


def create_address(vulnerable, v):
    loc = get_address_map_google(v)
    if loc is None:
        raise forms.ValidationError("Address is invalid")
    else:
        additional_address = VulnerableAddress()
        additional_address.vulnerable = vulnerable
        additional_address.address = v
        additional_address.address_lng = loc['lng']
        additional_address.address_lat = loc['lat']
        additional_address.save()


def in_admin_group(user):
    return 'administration' in user.groups


# helper function builds the object for a point location record
def point_map_record(name, feat, point, activity, act_type):
    if act_type == "exit place":
        time = activity.time - datetime.timedelta(0, 1)
    else:
        time = activity.time

    if activity.location:
        person = str(activity.location.person)
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
        'person': person}
    return point_record


# helper function builds the object for a geofence record
def geofence_record(activity, fence, an_activity, time='', person=''):
    if an_activity:
        time = activity.time
        person = str(activity.location.person)
        category = str([str(cat) for cat in activity.location.category])[1:-1]
        location = activity.location

    else:
        location = activity
        category = str([str(cat) for cat in location.category])[1:-1]
        person = str(location.person)

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
def volunteer_edit_view(request):
    profile = request.context['user_profile']
    availability_formset = inlineformset_factory(Volunteer, VolunteerAvailability,
                                                 form=VolunteerAvailabilityForm, fk_name="volunteer")
    list_of_avail = VolunteerAvailability.objects.filter(volunteer=profile.volunteer).values()
    item_forms = availability_formset(initial=list_of_avail)
    if request.method == "POST":
        next = request.POST.get("next", reverse("index"))
        form = VolunteerForm(request.POST, instance=profile.volunteer)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.profile = profile
            volunteer.save()
        formset = availability_formset(request.POST, instance=volunteer)
        VolunteerAvailability.objects.filter(volunteer=volunteer).delete()
        formset.is_valid()
        for f in formset:
            if f.cleaned_data.get('address'):  # Check if there is a provided address
                address = get_address_map_google(f.cleaned_data['address'])
                if address is None:
                    raise forms.ValidationError("Address is invalid")
                if not f.cleaned_data.get('time_from') or not f.cleaned_data.get('time_to'):
                    raise forms.ValidationError("Time inputted is invalid")
                else:
                    # Create new windows of availabilities for a volunteer
                    availability = VolunteerAvailability(volunteer=volunteer, address=f.cleaned_data.get('address'),
                                                         address_lat=address['lat'], address_lng=address['lng'],
                                                         time_from=f.cleaned_data['time_from'],
                                                         time_to=f.cleaned_data['time_to'])
                    availability.save()

        add_message(request, messages.SUCCESS, "Changes saved successfully.")
        request.context['next'] = next
    else:
        request.context['next'] = request.GET.get('next', reverse("index"))
        form = VolunteerForm(instance=profile.volunteer)

    request.context['form'] = form
    request.context['formset'] = item_forms
    return render(request, 'dashboard/profile/volunteer_edit.html', request.context)


@login_required
def vulnerable_list_view(request):
    profile = request.context['user_profile']
    request.context['user'] = profile.user
    request.context['vulnerable_list'] = profile.vulnerable_people.all()
    return render(request, 'dashboard/vulnerable/vulnerable_list.html', request.context)


@login_required
# @user_passes_test(in_admin_group)
def vulnerable_history_view(request, hash):
    profile = request.context['user_profile']
    vulnerable_hash = hash
    person = Vulnerable.objects.filter(hash=hash).first()

    wkt_w = WKTWriter()  # wkt string object format is recognisable for mapping coordinates

    # get activity details from 'Location' activities for this person
    loc_activities = Activity.objects.prefetch_related('location', 'person').filter(person__hash=vulnerable_hash,
                                                                                    category="Location").order_by(
        'time')
    j = 0

    processed = []  # for the table summary. Group all similar location activities in order
    currlocation = None
    currentplace = None
    startDate = None

    journeys = [
        []]  # list of lists of separate journey dicts to then add to ordered dict of features for template to draw
    feature_fences = []  # list of lists of locations to add
    for l in loc_activities:
        if not startDate:
            startDate = l.time.date()

        # current point
        pnt = Point(float(l.locLon), float(l.locLat), srid=3857)
        # see if activity in geofence but needs to be updated in database (new geofence created recently)
        if not l.location:
            fence_loc = Location.objects.filter(fence__contains=pnt)
            if fence_loc:
                l.location = fence_loc[0]
                l.update()

        prior = {}
        prior['name'] = None
        prior['act_type'] = None
        if len(journeys[j]) > 0:
            prior = journeys[j][-1]

        # if hit a known location add nearest boundary points too
        if l.location:

            # for the processed table groupings (append each place travelled to in order)
            if l.location != currlocation:
                processed.append({"time": str(l.time), "location": l.location, "person": l.person,
                                  "activity_type": str(l.activity_type)})
                currentplace = l
                currlocation = l.location

            # add the ENTRY boundary point then the location
            if str(l.location.name):  # if has name then at known geofence

                # went from location to location
                if (prior['act_type'] == "geo_fence" or prior['act_type'] == "exit place") and prior[
                    'name'] != l.location.name:
                    # use centroids as point to point reference
                    a = prior['feature'].lstrip('b')
                    prior['feature'] = a[1:-1]
                    last_cnt = GEOSGeometry(prior['feature']).centroid

                    wkt_feat = wkt_w.write(last_cnt)
                    a = str(wkt_feat)
                    b = a.lstrip('b')
                    wkt_feat = b[1:-1]
                    print(wkt_feat)
                    to_add = point_map_record(str(l.location.name), wkt_feat, last_cnt, l, "exit place")
                    journeys[j].append(to_add)
                    # start next journey
                    journeys.append([])
                    j += 1

                    # add entry point
                    curr_cnt = l.location.fence.centroid
                    wkt_feat = curr_cnt.wkt
                    to_add = point_map_record(str(l.location.name), wkt_feat, curr_cnt, l, "enter location")
                    journeys[j].append(to_add)

                # entered new location after a travel point
                # get entry point based on last recorded location
                elif prior['name'] and prior['name'] != l.location.name:
                    last_pnt = Point(float(prior['locLon']), float(prior['locLat']), srid=3857)
                    boundary = l.location.fence.boundary
                    opt_dist = boundary.project(last_pnt)
                    # get point on boundary at that distance
                    entry = boundary.interpolate(opt_dist)
                    wkt_feat = wkt_w.write(entry)
                    a = str(wkt_feat)
                    b = a.lstrip('b')
                    wkt_feat = b[1:-1]
                    to_add = point_map_record(str(l.location.name), wkt_feat, entry, l, "enter location")
                    journeys[j].append(to_add)

                # add current location even if stayed in same location
                wkt_fence = wkt_w.write(l.location.fence)
                to_add = geofence_record(l, wkt_fence, True)
                journeys[j].append(to_add)

        # just travel point
        else:
            # for the table count travel as no location
            currlocation = None
            currentplace = None

            # may need exit point from last location to this current point
            if prior['act_type'] == "geo_fence":
                a = prior['feature']
                b = a.lstrip('b')
                prior['feature'] = b[1:-1]
                boundary = GEOSGeometry(prior['feature']).boundary
                opt_dist = boundary.project(pnt)
                exitpnt = boundary.interpolate(opt_dist)
                wkt_feat = wkt_w.write(exitpnt)
                a = str(wkt_feat)
                b = a.lstrip('b')
                wkt_feat = b[1:-1]
                to_add = point_map_record(str(prior['name']), wkt_feat, exitpnt, l, "exit place")
                journeys[j].append(to_add)

                # start next journey after exit
                journeys.append([])
                j += 1

            wkt_feat = wkt_w.write(pnt)
            a = str(wkt_feat)
            b = a.lstrip('b')
            wkt_feat = b[1:-1]
            reg_point = point_map_record("journey: " + str(j), wkt_feat, pnt, l, "moving")
            journeys[j].append(reg_point)

    # get additional known locations details for this person or their friends' homes
    fences = list(Location.objects.filter(person__hash=vulnerable_hash))
    for f in fences:
        wkt_fence = wkt_w.write(f.fence)
        to_add = geofence_record(f, wkt_fence, False)
        feature_fences.append([to_add])

        # send all the data back to the template
    request.context['known_locations'] = feature_fences
    request.context['title'] = "History for " + str(person.first_name) + " " + str(person.last_name)
    request.context['point_collection'] = journeys
    request.context['selectperson'] = person
    request.context['location'] = 'all'
    # request.context['time_from'] = {'date': str(startDate)}
    # request.context['time_to'] = {'date': str(endDate)}
    request.context['query_result'] = processed  # for the table summary. all similar location activities grouped

    request.context['vulnerable'] = person
    if not person:
        add_message(request, messages.WARNING, "Vulnerable person not found.")
        return HttpResponseRedirect(reverse("vulnerable_list"))

    return render(request, 'dashboard/vulnerable/vulnerable_history.html', request.context)


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
        formset = address_formset(request.POST, queryset=VulnerableAddress.objects.all())
        if formset.is_valid():
            for k, v in formset.data.items():
                if k.endswith("-address") and k != "addresses-0-address" and v != "":
                    create_address(vulnerable, v)
            for address in formset.save(commit=False):
                address.vulnerable = vulnerable
                address.save()
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
                                            can_delete=True,
                                            extra=1,
                                            formset=VulnerableAddressFormSet)
    if request.method == "POST":
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
        for k, v in formset.data.items():
            if k.endswith("-address") and v != "":
                create_address(vulnerable, v)
        add_message(request, messages.SUCCESS, "Changes saved successfully.")
        return HttpResponseRedirect(next1)
    else:
        form = VulnerableForm(instance=vulnerable)
        formset = address_formset(instance=vulnerable)
        next = request.GET.get("next", reverse("vulnerable_list"))
    request.context['next'] = next
    request.context['form'] = form
    request.context['formset'] = formset
    addresses = json.loads("[]")
    for form in formset.forms:
        form_json = json.loads("{}")
        form_json['errors'] = list(form.errors.values())
        form_json['instance_id'] = form.instance.id or None
        form_json['value'] = form['address'].value() or None
        addresses.append(form_json)
    request.context['addresses'] = json.dumps(addresses)
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

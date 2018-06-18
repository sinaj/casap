import datetime
import simplejson as json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.forms import model_to_dict
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse

from casap.forms.forms import EmergencyCallForm
from casap.models import LostPersonRecord, VolunteerAvailability, EmergencyCall
from casap.models import SightingRecord
from casap.models import Vulnerable
from casap.utilities.utils import get_user_time


@login_required
def index(request):
    profile = request.context['user_profile']
    current_date = datetime.date.today()
    time_now = datetime.datetime.now()
    two_days_ago = datetime.datetime.now() - datetime.timedelta(hours=48)
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    combined_queryset = LostPersonRecord.objects.filter(state="reported") | LostPersonRecord.objects.filter(
        state="sighted")
    missing_people = list(combined_queryset.order_by("-time").all())
    # missing_people = list(LostPersonRecord.objects.filter(state="reported").order_by("-time").all())

    # Remove all duplicates but keep the most recently updated seen record
    # seen_id = []
    # seen_list = []
    # for i in seen_people:
    #     if i.lost_record_id not in seen_id:
    #         seen_id.append(i.lost_record_id)
    #         seen_list.append(i)

    records = list()
    json_dec = json.decoder.JSONDecoder()
    try:
        if profile.volunteer.id:
            for i in missing_people:
                try:
                    vol_list = json_dec.decode(i.volunteer_list)
                    if int(profile.volunteer.id) in vol_list:
                        records.append(i)
                except:
                    pass
    except:
        pass

    request.context['current_date'] = current_date
    request.context['time_now'] = time_now
    request.context['two_days_ago'] = two_days_ago
    request.context['week_ago'] = week_ago
    if profile.user.is_staff:
        request.context['missing_people'] = missing_people
    else:
        request.context['missing_people'] = records
    # request.context['seen_people'] = seen_list
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    return render(request, "public/index.html", request.context)


@login_required
def track_missing_view(request, hash):
    profile = request.context['user_profile']
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    emerg = EmergencyCall.objects.get()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))
    request.context['emerg'] = emerg
    request.context['record'] = lost_record
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    if lost_record.state == "found" and not profile.user.is_staff:
        return render(request, "redirect.html", request.context)
    else:
        return render(request, "public/track_missing.html", request.context)


@login_required
def show_missing_view(request, hash):
    profile = request.context['user_profile']
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    emerg = EmergencyCall.objects.get()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))
    request.context['emerg'] = emerg
    request.context['record'] = lost_record
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    if lost_record.state == "found" and not profile.user.is_staff:
        return render(request, "redirect.html", request.context)
    else:
        return render(request, "public/show_missing.html", request.context)


def location_view(request):
    return render(request, "LocationView.html", request.context)


def admin_view(request):
    avail = list()
    for each in VolunteerAvailability.objects.all():
        vol_details = [each.address_lat, each.address_lng, each.km_radius, each.address, each.volunteer.full_name,
                       ]

        avail.append(vol_details)

    request.context['volunteeraddress'] = avail

    LostPersonName = []

    for each in LostPersonRecord.objects.all():
        name = each.vulnerable.first_name + ' ' + each.vulnerable.last_name
        LostPersonName.append(name)

    request.context['LostPersonName'] = list(set(LostPersonName))
    request.context['Vulnerable'] = Vulnerable

    return render(request, "adminView.html", request.context)


def admin_settings_view(request):
    if request.method == "POST":
        emerg = EmergencyCall.objects.last()
        form = EmergencyCallForm(request.POST, initial=model_to_dict(emerg))
        if form.is_valid():
            if form.cleaned_data.get('phone_number'):
                print(form.cleaned_data.get('phone_number'))
                emerg.phone_number = form.cleaned_data.get('phone_number')
                emerg.save()
                add_message(request, messages.SUCCESS, "Settings successfully updated.")
    emerg = EmergencyCall.objects.last()
    form = EmergencyCallForm(initial=model_to_dict(emerg))
    request.context['form'] = form
    return render(request, "admin_settings.html", request.context)


def tips_view(request):
    return render(request, "tips.html", request.context)

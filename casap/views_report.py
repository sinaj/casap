import datetime
import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from geopy.distance import vincenty

from casap.forms_report import LostPersonRecordForm, SightingRecordForm, FindRecordForm
from casap.models import Vulnerable, LostPersonRecord, Volunteer, VolunteerAvailability
from casap.utils import get_user_time, send_sms, get_standard_phone,SimpleMailHelper
from django.utils.html import strip_tags

# Taken from https://stackoverflow.com/questions/10747974/how-to-check-if-the-current-time-is-in-range-in-python
# Date: January 23, 2018
# Author: Dietrich Epp
def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

@login_required
def report_lost_view(request):
    if request.method == "POST":
        form = LostPersonRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
            vulnerable = Vulnerable.objects.filter(hash=request.POST.get("vulnerable")).first()
            if vulnerable:
                form.save(request.user, vulnerable)
                return HttpResponseRedirect(request.POST.get("next", reverse("index")))
            else:
                form.add_error("vulnerable", ValidationError("Vulnerable person not found"))
    else:
        form = LostPersonRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['all_timezones'] = pytz.all_timezones
    request.context['vulnerable_people'] = [dict(hash=vul.hash, name=vul.full_name) for vul in Vulnerable.objects.all()]
    return render(request, "report/report_lost.html", request.context)


@login_required
def report_sighting_view(request, hash):
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        form = SightingRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
            time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime("%H:%M")
            sighting_record = form.save(request.user, lost_record)
            lost_record.state = "sighted"
            lost_record.save()
            notify_sighting(sighting_record, time_seen)
            add_message(request, messages.SUCCESS, "Thank you! Our records are updated.")
            return HttpResponseRedirect(request.POST.get("next", reverse("index")))

    else:
        form = SightingRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['record'] = lost_record
    request.context['all_timezones'] = pytz.all_timezones
    return render(request, "report/report_sighting.html", request.context)


def notify_sighting(sighting_record, time_seen, max_distance=None):
    if max_distance is None:
        max_distance = 5
    lat, lng = sighting_record.address_lat, sighting_record.address_lng
    close_volunteers = set()
    for vol in Volunteer.objects.all():
        availability = VolunteerAvailability.objects.filter(volunteer=vol)
        for x in availability:
            seen = datetime.datetime.strptime(time_seen, "%H:%M").time()
            if (time_in_range(x.time_from, x.time_to, seen)) and \
                    (vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= max_distance):
                    close_volunteers.add(vol)

    for vol in close_volunteers:
        if sighting_record.description:
            sms_text = "Dear %s,\n%s has been lost near you with description:\n%s\n\n" % (vol.full_name,
                                                                                        sighting_record.lost_record.vulnerable.full_name,
                                                                                        sighting_record.description) + \
                       "Please report to use when sighted by following the link below:\n%s" % sighting_record.get_link()
        else:
            sms_text = "Dear %s,\n%s has been lost near you.\n" % (vol.full_name,
                                                                   sighting_record.lost_record.vulnerable.full_name) + \
                       "Please report to use when sighted by following the link below:\n%s" % sighting_record.get_link()
        send_sms(get_standard_phone(vol.phone), sms_text)
        SimpleMailHelper("Someone lost near you", sms_text, sighting_record.get_link(), vol.email).send_email()

@login_required
def report_found_view(request, hash):
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        form = FindRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
            form.save(request.user, lost_record)
            lost_record.state = "found"
            lost_record.save()
            add_message(request, messages.SUCCESS, "Thank you! Our records are updated.")
            return HttpResponseRedirect(request.POST.get("next", reverse("index")))
    else:
        form = FindRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['record'] = lost_record
    request.context['all_timezones'] = pytz.all_timezones
    return render(request, "report/report_found.html", request.context)

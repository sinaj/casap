import datetime

from django.contrib import messages
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse

from casap.models import LostPersonRecord, VolunteerAvailability
from casap.models import SightingRecord
from casap.models import Vulnerable
from casap.utilities.utils import get_user_time


def index(request):
    current_date = datetime.date.today()
    time_now = datetime.datetime.now()
    two_days_ago = datetime.datetime.now() - datetime.timedelta(hours=48)
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    missing_people = list(LostPersonRecord.objects.filter(state="reported").order_by("-time").all())
    seen_people = list(SightingRecord.objects.order_by("-time").all().filter(lost_record__state__exact='sighted'))

    # Remove all duplicates but keep the most recently updated seen record
    seen_id = []
    seen_list = []
    for i in seen_people:
        if i.lost_record_id not in seen_id:
            seen_id.append(i.lost_record_id)
            seen_list.append(i)

    request.context['current_date'] = current_date
    request.context['time_now'] = time_now
    request.context['two_days_ago'] = two_days_ago
    request.context['week_ago'] = week_ago
    request.context['missing_people'] = missing_people
    request.context['seen_people'] = seen_list
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    return render(request, "public/index.html", request.context)


def track_missing_view(request, hash):
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))
    request.context['record'] = lost_record
    request.context['vulnerable'] = lost_record.vulnerable
    return render(request, "public/track_missing.html", request.context)


def show_missing_view(request, hash):
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))
    request.context['record'] = lost_record
    request.context['vulnerable'] = lost_record.vulnerable
    return render(request, "public/show_missing.html", request.context)


def location_view(request):
    return render(request, "LocationView.html", request.context)


def admin_view(request):
    avail = list()
    for each in VolunteerAvailability.objects.all():

        vol_details = [each.address_lat, each.address_lng, each.km_radius, each.address, each.volunteer.full_name,
                       each.time_to.strftime('%H:%M'), each.time_from.strftime('%H:%M')]

        avail.append(vol_details)

    request.context['volunteeraddress'] = avail

    LostPersonName = []

    for each in LostPersonRecord.objects.all():
        name = each.vulnerable.first_name + ' ' + each.vulnerable.last_name
        LostPersonName.append(name)

    request.context['LostPersonName'] = list(set(LostPersonName))
    request.context['Vulnerable'] = Vulnerable

    return render(request, "adminView.html", request.context)

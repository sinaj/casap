import datetime

from django.contrib import messages
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse


from casap.models import LostPersonRecord, VolunteerAvailability
from casap.models import SightingRecord
from casap.models import Vulnerable


def index(request):
    current_date = datetime.date.today()
    time_now = datetime.datetime.now()
    two_days_ago = datetime.datetime.now() - datetime.timedelta(hours=48)
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    missing_people = list(LostPersonRecord.objects.filter(state="reported").order_by("-time").all())
    seen_people = list(SightingRecord.objects.order_by("-time").all())
    request.context['current_date'] = current_date
    request.context['time_now'] = time_now
    request.context['two_days_ago'] = two_days_ago
    request.context['week_ago'] = week_ago
    request.context['missing_people'] = missing_people
    request.context['seen_people'] = seen_people
    return render(request, "public/index.html", request.context)


def track_missing_view(request, hash):
    sighting_record = SightingRecord.objects.filter(hash=hash).first()
    lost_record = sighting_record.lost_record
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
    address = []
    for each in VolunteerAvailability.objects.all():
        personallocation = [each.address_lat, each.address_lng]

        address.append(personallocation)

    request.context['volunteeraddress'] = address

    LostPersonName = []

    for each in LostPersonRecord.objects.all():
        name = each.vulnerable.first_name + ' ' + each.vulnerable.last_name
        LostPersonName.append(name)

    request.context['LostPersonName'] = LostPersonName
    request.context['Vulnerable'] = Vulnerable

    return render(request, "adminView.html", request.context)


def slider_view(request):
    return render(request, "slider.html", request.context)

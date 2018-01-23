from django.contrib import messages
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.template import loader, context

from casap.models import LostPersonRecord
from casap.models import SightingRecord
from casap.models import Volunteer
from casap.models import Vulnerable


def index(request):
    missing_people = dict()
    for record in LostPersonRecord.objects.exclude(state="found").order_by("-time").all():
        date = record.time.date()
        if date not in missing_people:
            missing_people[date] = list()
        missing_people[date].append(record)
    request.context['missing_people'] = missing_people.items()
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

def location_view(request):
    return render(request, "LocationView.html", request.context)

def admin_view(request):
    address = []
    for each in Volunteer.objects.all():
        personallocation = [each.personal_lat,each.personal_lng]
        businesslocation = [each.business_lat,each.business_lng]
        address.append(businesslocation)
        address.append(personallocation)

    request.context['volunteeraddress'] = address

    LostPersonName = []

    for each in LostPersonRecord.objects.all():
        name = each.vulnerable.first_name +' '+each.vulnerable.last_name
        LostPersonName.append(name)

    request.context['LostPersonName'] = LostPersonName
    request.context['Vulnerable'] = Vulnerable

    return render(request, "adminView.html", request.context)



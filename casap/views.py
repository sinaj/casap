from django.contrib import messages
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.template import loader, context

from casap.models import LostPersonRecord
from casap.models import SightingRecord


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

def map_view(request):
    return render(request, "MapView.html", request.context)

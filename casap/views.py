from django.contrib import messages
from django.contrib.messages import add_message
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage


from casap.models import LostPersonRecord


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
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))
    request.context['record'] = lost_record
    request.context['vulnerable'] = lost_record.vulnerable
    return render(request, "public/track_missing.html", request.context)
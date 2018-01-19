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
from casap.models import Vulnerable, LostPersonRecord, Volunteer
from casap.utils import get_user_time, send_sms, get_standard_phone,SimpleMailHelper
from django.utils.html import strip_tags



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
            sighting_record = form.save(request.user, lost_record)
            lost_record.state = "sighted"
            lost_record.save()
            notify_sighting(sighting_record)
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


def notify_sighting(sighting_record, max_distance=None):
    if max_distance is None:
        max_distance = 5
    lat, lng = sighting_record.address_lat, sighting_record.address_lng
    close_volunteers = set()
    for vol in Volunteer.objects.all():
        if vincenty((vol.personal_lat, vol.personal_lng), (lat, lng)).kilometers <= max_distance:
            close_volunteers.add(vol)
        if vincenty((vol.business_lat, vol.business_lng), (lat, lng)).kilometers <= max_distance:
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

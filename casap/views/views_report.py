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
from django.contrib.gis.geos import Point

from casap.forms.forms_report import LostPersonRecordForm, SightingRecordForm, FindRecordForm

from casap.models import Vulnerable, LostPersonRecord, Volunteer, Activity, Location, VolunteerAvailability, \
    LostActivity, FoundActivity

from casap.utilities.utils import get_user_time, send_sms, get_standard_phone, SimpleMailHelper, send_tweet, shorten_url


def tweet_helper(name, link, flag, time):
    link = shorten_url(link)
    if flag == 1:
        txt = "{} has been reported LOST at {}. For more details, visit {}".format(name,
                                                                                   time.time().strftime(
                                                                                       '%H:%M'), link)
    else:
        txt = "{} has been reported SEEN at {}. For more details, visit {}".format(name,
                                                                                   time.time().strftime(
                                                                                       '%H:%M'),
                                                                                   link)
    return txt


def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def lost_notification(notify_record, vol):
    if notify_record.description:
        sms_text = "Dear %s,\nClient: %s has been lost near you with description:\n%s\n\n" % (vol.full_name,
                                                                                              notify_record.vulnerable.full_name,
                                                                                              notify_record.description) + \
                   "Please report when seen or found by following the link below:\n%s" % notify_record.get_link()
    else:
        sms_text = "Dear %s,\nClient: %s has been lost near you.\n" % (vol.full_name,
                                                                       notify_record.vulnerable.full_name) + \
                   "Please report when seen or found by following the link below:\n%s" % notify_record.get_link()

    mail_subject = "C-ASAP Client: %s has been lost near you " % notify_record.vulnerable.full_name
    send_sms(get_standard_phone(vol.phone), sms_text)
    SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()


def seen_notification(notify_record, vol):
    if notify_record.description:
        sms_text = "Dear %s,\nLost client: %s has been seen near you with description:\n%s\n\n" % (vol.full_name,
                                                                                                   notify_record.lost_record.vulnerable.full_name,
                                                                                                   notify_record.description) + \
                   "Please report to use when seen or found byfollowing the link below:\n%s" % notify_record.get_link()
    else:
        sms_text = "Dear %s,\nLost client: %s has been seen near you.\n" % (vol.full_name,
                                                                            notify_record.lost_record.vulnerable.full_name) + \
                   "Please report when seen or found by following the link below:\n%s" % notify_record.get_link()
    send_sms(get_standard_phone(vol.phone), sms_text)
    mail_subject = "C-ASAP Lost Client: %s has been seen near you" % notify_record.lost_record.vulnerable.full_name
    SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()


@login_required
def report_lost_view(request):
    if request.method == "POST":
        form = LostPersonRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
            vulnerable = Vulnerable.objects.filter(hash=request.POST.get("vulnerable")).first()
            if vulnerable:
                lost_record = form.save(request.user, vulnerable)
                time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime("%H:%M")

                lost_activity = LostActivity()
                lost_activity.locLat = lost_record.address_lat
                lost_activity.locLon = lost_record.address_lng
                lost_activity.person_id = lost_record.vulnerable_id
                lost_activity.time = lost_record.time
                lost_activity.adminPoint = Point(float(lost_activity.locLon), float(lost_activity.locLat), srid=3857)
                fence_loc = Location.objects.filter(fence__contains=lost_activity.adminPoint)
                if fence_loc:
                    lost_activity.location = fence_loc[0]
                lost_activity.save()
                flag = 1
                notify_volunteers(lost_record, time_seen, flag)
                send_tweet(
                    tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(), flag, lost_record.time))
                success_msg = "Success! %s has been reported lost." % vulnerable.full_name
                add_message(request, messages.SUCCESS, success_msg)
                return HttpResponseRedirect(request.POST.get("next", reverse("index")))
            else:
                form.add_error("vulnerable", ValidationError("Vulnerable person not found"))
    else:
        form = LostPersonRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))

    profile = request.context['user_profile']
    request.context['form'] = form
    request.context['all_timezones'] = pytz.all_timezones
    request.context['vulnerable_people'] = [dict(hash=vul.hash, name=vul.full_name) for vul in
                                            profile.vulnerable_people.all()]
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
            flag = 2
            sighting_record = form.save(request.user, lost_record)
            activity = Activity()
            activity.locLat = sighting_record.address_lat
            activity.locLon = sighting_record.address_lng
            activity.person_id = sighting_record.lost_record.vulnerable_id
            activity.time = sighting_record.time
            activity.adminPoint = Point(float(activity.locLon), float(activity.locLat), srid=3857)
            fence_loc = Location.objects.filter(fence__contains=activity.adminPoint)
            if fence_loc:
                activity.location = fence_loc[0]

            activity.save()

            lost_record.state = "sighted"
            lost_record.save()
            notify_volunteers(sighting_record, time_seen, flag)
            send_tweet(
                tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(), flag, sighting_record.time))
            success_msg = "Success! %s has been reported seen." % lost_record.vulnerable.full_name
            add_message(request, messages.SUCCESS, success_msg)
            return HttpResponseRedirect(request.POST.get("next", reverse("index")))

    else:
        form = SightingRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['record'] = lost_record
    request.context['all_timezones'] = pytz.all_timezones
    return render(request, "report/report_sighting.html", request.context)


def notify_volunteers(notify_record, time_seen, flag):
    lat, lng = notify_record.address_lat, notify_record.address_lng
    close_volunteers = set()
    for vol in Volunteer.objects.all():
        availability = VolunteerAvailability.objects.filter(volunteer=vol)
        for x in availability:
            seen = datetime.datetime.strptime(time_seen, "%H:%M").time()
            if (time_in_range(x.time_from, x.time_to, seen)) and \
                    (vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= x.km_radius):
                close_volunteers.add(vol)

    for vol in close_volunteers:
        if flag == 1:
            lost_notification(notify_record, vol)
        else:
            seen_notification(notify_record, vol)


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
            v = form.save(request.user, lost_record)
            lost_record.state = "found"
            lost_record.save()
            found_activity = FoundActivity()
            found_activity.locLat = v.address_lat
            found_activity.locLon = v.address_lng
            found_activity.person_id = lost_record.vulnerable_id
            found_activity.time = lost_record.time
            found_activity.adminPoint = Point(float(found_activity.locLon), float(found_activity.locLat), srid=3857)
            fence_loc = Location.objects.filter(fence__contains=found_activity.adminPoint)
            if fence_loc:
                found_activity.location = fence_loc[0]
            found_activity.save()
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

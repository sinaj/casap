import datetime
import pytz
import simplejson as json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages import add_message
from django.core.exceptions import ValidationError
from django.forms import model_to_dict
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core.urlresolvers import reverse
from geopy.distance import vincenty
from django.contrib.gis.geos import Point
from pyproj import Proj, transform

from casap.forms.forms import ManageNotificationsForm
from casap.forms.forms_report import LostPersonRecordForm, SightingRecordForm, FindRecordForm

from casap.models import Vulnerable, LostPersonRecord, Volunteer, Activity, Location, VolunteerAvailability, \
    LostActivity, FoundActivity, Alerts, Notifications, Profile

from casap.utilities.utils import get_user_time, send_sms, get_standard_phone, SimpleMailHelper, send_tweet, \
    shorten_url, send_twitter_dm


def tweet_helper(name, link, flag, time):
    link = "http://{}".format(link)
    link = shorten_url(link)
    if flag == 1:
        txt = "{} has been reported LOST at {}. For more details, visit {} #Missing".format(name,
                                                                                            time.time().strftime(
                                                                                                '%H:%M'), link)
    else:
        txt = "{} has been FOUND at {}. For more details, visit {} #Found".format(name,
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
                   "For more details visit the link below:\n%s" % notify_record.get_link()
    else:
        sms_text = "Dear %s,\nClient: %s has been lost near you.\n" % (vol.full_name,
                                                                       notify_record.vulnerable.full_name) + \
                   "Please report when seen or found by following the link below:\n%s" % notify_record.get_link()

    mail_subject = "C-ASAP Client: %s has been lost near you " % notify_record.vulnerable.full_name
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), sms_text)
    if vol.email:
        SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()
    if vol.twitter_handle:
        send_twitter_dm(sms_text, vol.twitter_handle)


def seen_notification(notify_record, vol, notif):
    if notify_record.description:
        sms_text = "Dear %s,\nLost client: %s has been seen near you with description:\n%s\n\n" % (vol.full_name,
                                                                                                   notify_record.lost_record.vulnerable.full_name,
                                                                                                   notify_record.description) + \
                   "Please report to use when seen or found byfollowing the link below:\n%s" % notify_record.get_link()
    else:
        sms_text = "Dear %s,\nLost client: %s has been seen near you.\n" % (vol.full_name,
                                                                            notify_record.lost_record.vulnerable.full_name) + \
                   "Please report when seen or found by following the link below:\n%s" % notify_record.get_link()

    if notif.phone_notify:
        send_sms(get_standard_phone(vol.phone), sms_text)
    if notif.email_notify:
        mail_subject = "C-ASAP Lost Client: %s has been seen near you" % notify_record.lost_record.vulnerable.full_name
        SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()
    if notif.twitter_dm_notify:
        if vol.twitter_handle:
            send_twitter_dm(sms_text, vol.twitter_handle)


def send_alert_email(profile, lost_alert):
    text = "%s: a new notification needs your attention. Please click the link below to view it. \n %s" % (
        profile.full_name, lost_alert.get_link())
    mail_subject = "C-ASAP Admin: New Notification Alert"
    SimpleMailHelper(mail_subject, text, text, profile.user.email).send_email()


@login_required
def report_lost_view(request):
    coordinators = Profile.objects.filter(coordinator_email=True)
    profile = request.context['user_profile']
    if request.method == "POST":
        form = LostPersonRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
            vulnerable = Vulnerable.objects.filter(hash=request.POST.get("vulnerable")).first()
            if vulnerable:
                lost_record = form.save(request.user, vulnerable)
                x = list(generate_volunteers(lost_record))
                lost_record.volunteer_list = json.dumps(x)
                lost_record.save()
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
                time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime(
                    "%H:%M")
                flag = 1
                notify_volunteers(lost_record, flag)
                send_tweet(
                    tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(),
                                 flag, lost_record.time))
            add_message(request, messages.SUCCESS, "Success")
            return HttpResponseRedirect(reverse('index'))
        else:
            form.add_error("vulnerable", ValidationError("Vulnerable person not found"))
    else:
        form = LostPersonRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))

    profile = request.context['user_profile']
    request.context['form'] = form
    request.context['all_timezones'] = pytz.all_timezones
    request.context['vulnerable_people'] = [dict(hash=vul.hash, name=vul.full_name) for vul in Vulnerable.objects.all()]
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    return render(request, "report/report_lost.html", request.context)


@login_required
def report_sighting_view(request, hash):
    coordinators = Profile.objects.filter(coordinator_email=True)
    lost_record = LostPersonRecord.objects.filter(hash=hash).first()
    if not lost_record:
        add_message(request, messages.WARNING, "Record not found")
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        form = SightingRecordForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid():
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
            notif = Notifications()
            notif.save()
            lost_alert = Alerts(
                state='Sighted', lost_record=lost_record, seen_record=sighting_record, notifications=notif
            )
            lost_alert.save()
            for coord in coordinators:
                send_alert_email(coord, lost_alert)
            success_msg = "Success! %s has been reported seen." % lost_record.vulnerable.full_name
            add_message(request, messages.SUCCESS, success_msg)
            return HttpResponseRedirect(reverse('index'))
        else:
            pass

    else:
        form = SightingRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['record'] = lost_record
    request.context['all_timezones'] = pytz.all_timezones
    return render(request, "report/report_sighting.html", request.context)


@login_required
def alert_list_view(request):
    alerts = Alerts.objects.all()
    request.context['alerts'] = alerts
    request.context['user_tz_name'] = 'Canada/Mountain'
    return render(request, 'alertList.html', request.context)


@login_required
def alert_view(request, hash):
    alert = Alerts.objects.filter(hash=hash).first()
    notif = Notifications.objects.get(id=alert.notifications_id)
    form = ManageNotificationsForm(request.POST, initial=model_to_dict(notif))
    if request.method == 'POST':
        if 'sendAlert' in request.POST:
            alert = Alerts.objects.filter(hash=hash).first()
            notif = Notifications.objects.get(id=alert.notifications_id)
            if form.is_valid():
                if form.cleaned_data.get('phone_notify'):
                    notif.phone_notify = True
                else:
                    notif.phone_notify = False
                if form.cleaned_data.get('email_notify'):
                    notif.email_notify = True
                else:
                    notif.email_notify = False
                if form.cleaned_data.get('twitter_dm_notify'):
                    notif.twitter_dm_notify = True
                else:
                    notif.twitter_dm_notify = False
                if form.cleaned_data.get('twitter_public_notify'):
                    notif.twitter_public_notify = True
                else:
                    notif.twitter_public_notify = False
                notif.save()

                time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime("%H:%M")
                if alert.state == 'Lost':
                    flag = 1
                    notify_volunteers(alert.lost_record, time_seen, flag, notif)
                    if notif.twitter_public_notify:
                        send_tweet(
                            tweet_helper(alert.lost_record.vulnerable.full_name, alert.lost_record.get_link(), flag,
                                         alert.lost_record.time))
                else:
                    flag = 2
                    notify_volunteers(alert.sighting_record, time_seen, flag, notif)
                    if notif.twitter_public_notify:
                        send_tweet(
                            tweet_helper(alert.lost_record.vulnerable.full_name, alert.lost_record.get_link(), flag,
                                         alert.sighting_record.time))

                alert.sent = True
                alert.save()
                add_message(request, messages.SUCCESS, "Notifications successfully sent.")
                return HttpResponseRedirect(reverse("index"))
            else:
                if form.cleaned_data:
                    if form.cleaned_data.get('phone_notify'):
                        notif.phone_notify = True
                    else:
                        notif.phone_notify = False
                    if form.cleaned_data.get('email_notify'):
                        notif.email_notify = True
                    else:
                        notif.email_notify = False
                    if form.cleaned_data.get('twitter_dm_notify'):
                        notif.twitter_dm_notify = True
                    else:
                        notif.twitter_dm_notify = False
                    if form.cleaned_data.get('twitter_public_notify'):
                        notif.twitter_public_notify = True
                    else:
                        notif.twitter_public_notify = False

                    notif.save()

                    time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime(
                        "%H:%M")
                    if alert.state == 'Lost':
                        flag = 1
                        notify_volunteers(alert.lost_record, time_seen, flag, notif)
                        if notif.twitter_public_notify:
                            send_tweet(
                                tweet_helper(alert.lost_record.vulnerable.full_name, alert.lost_record.get_link(), flag,
                                             alert.lost_record.time))
                    else:
                        flag = 2
                        notify_volunteers(alert.seen_record, time_seen, flag, notif)
                        if notif.twitter_public_notify:
                            send_tweet(
                                tweet_helper(alert.lost_record.vulnerable.full_name, alert.lost_record.get_link(), flag,
                                             alert.seen_record.time))
                    alert.sent = True
                    alert.save()
                    add_message(request, messages.SUCCESS, "Notifications successfully sent.")
                    return HttpResponseRedirect(reverse("index"))
        else:
            alert = Alerts.objects.filter(hash=hash).first()
            profile = request.context['user_profile']
            if not alert:
                add_message(request, messages.WARNING, "Notification alert not found.")
                return HttpResponseRedirect(reverse("index"))
            if not profile.coordinator_email:
                add_message(request, messages.WARNING, "You are not authorized to perform this action.")
                return HttpResponseRedirect(reverse("index"))
            alert.sent = True
            alert.save()
            add_message(request, messages.SUCCESS, "Notification alert has been ignored.")
            return HttpResponseRedirect(reverse("index"))

    form = ManageNotificationsForm(initial=model_to_dict(notif))
    request.context['form'] = form
    request.context['alert'] = alert
    request.context['notif'] = notif
    return render(request, "alert_view.html", request.context)


def notify_volunteers(notify_record, flag):
    lat, lng = notify_record.address_lat, notify_record.address_lng
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    lng, lat = transform(inProj, outProj, float(lng), float(lat))
    close_volunteers = set()
    for vol in Volunteer.objects.all():
        availability = VolunteerAvailability.objects.filter(volunteer=vol)
        for x in availability:
            if (vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= x.km_radius):
                close_volunteers.add(vol)

    for vol in close_volunteers:
        # if flag == 1:
        lost_notification(notify_record, vol)
        # else:
        #     seen_notification(notify_record, vol, notif)


def generate_volunteers(notify_record):
    '''

    :param notify_record: the lost record
    :return: List of volunteer ids
    '''
    lat, lng = notify_record.address_lat, notify_record.address_lng
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    lng, lat = transform(inProj, outProj, float(lng), float(lat))
    close_volunteers = set()
    for vol in Volunteer.objects.all():
        availability = VolunteerAvailability.objects.filter(volunteer=vol)
        for x in availability:
            if (vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= x.km_radius):
                close_volunteers.add(vol.id)

    return close_volunteers


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
            json_dec = json.decoder.JSONDecoder()
            try:
                volunteer_list = json_dec.decode(lost_record.volunteer_list)
            except:
                volunteer_list = list()
            if volunteer_list:
                for i in volunteer_list:
                    send_found_alert(i, lost_record, v)
            lost_record.save()
            found_activity = FoundActivity()
            found_activity.locLat = v.address_lat
            found_activity.locLon = v.address_lng
            found_activity.person_id = lost_record.vulnerable_id
            found_activity.time = v.time
            found_activity.adminPoint = Point(float(found_activity.locLon), float(found_activity.locLat), srid=3857)
            fence_loc = Location.objects.filter(fence__contains=found_activity.adminPoint)
            if fence_loc:
                found_activity.location = fence_loc[0]
            found_activity.save()
            add_message(request, messages.SUCCESS, "Thank you! Our records are updated.")
            return HttpResponseRedirect(reverse("index"))
    else:
        form = FindRecordForm(initial=dict(time=get_user_time(request)))
        request.context['next'] = request.GET.get("next", reverse("index"))
    request.context['form'] = form
    request.context['vulnerable'] = lost_record.vulnerable
    request.context['record'] = lost_record
    request.context['all_timezones'] = pytz.all_timezones
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    return render(request, "report/report_found.html", request.context)


def send_found_alert(vol_id, record, v):
    vol = Volunteer.objects.get(id=vol_id)
    link = "http://{}".format(record.get_link())
    link = shorten_url(link)
    message = "Dear {}: {} has been found at {}. For more details visit the link below: {}".format(vol.full_name,
                                                                                                   record.vulnerable.full_name,
                                                                                                   v.time.time().strftime(
                                                                                                       '%H:%M'), link)
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), message)
    if vol.email:
        mail_subject = "C-ASAP Client: {} has been found".format(record.vulnerable.full_name)
        SimpleMailHelper(mail_subject, message, message, vol.email).send_email()
    if vol.twitter_handle:
        send_twitter_dm(message, vol.twitter_handle)

    send_tweet(tweet_helper(record.vulnerable.full_name, record.get_link(), 2, v.time))

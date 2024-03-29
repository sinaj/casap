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

from casap.forms.forms import ManageNotificationsForm, VulnerableReportForm
from casap.forms.forms_report import LostPersonRecordForm, SightingRecordForm, FindRecordForm

from casap.models import Vulnerable, LostPersonRecord, Volunteer, Activity, Location, VolunteerAvailability, \
    LostActivity, FoundActivity, Alerts, Notifications, Profile, TempSightingRecord, SightingRecord

from casap.utilities.utils import *


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
    # link = "http://{}".format(notify_record.get_link())
    link = shorten_url(notify_record.get_link())
    if not notify_record.vulnerable.instructions:
        sms_text = "Dear %s,\nClient: %s has been lost near you.\n" % (vol.full_name,
                                                                       notify_record.vulnerable.full_name) + \
                   "For more details visit the link below:\n%s" % link
    else:
        sms_text = "Dear %s,\nClient: %s has been lost near you.\n" % (vol.full_name,
                                                                       notify_record.vulnerable.full_name) + \
                   "For more details visit the link below:\n%s" % link + \
                   "\nQuick Tip: %s" % notify_record.vulnerable.instructions

    mail_subject = "C-ASAP Client: %s has been lost near you " % notify_record.vulnerable.full_name
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), sms_text)
    if vol.email:
        SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()
    # if vol.twitter_handle:
    #     send_twitter_dm(sms_text, vol.twitter_handle)


def new_update_notification(notify_record, vol):
    vol = Volunteer.objects.get(id=vol)
    # link = "http://{}".format(notify_record.get_link())
    link = shorten_url(notify_record.get_link())

    if not notify_record.vulnerable.instructions:
        sms_text = "C-ASAP Missing Client: %s has been recently updated at a location near you.\n" % notify_record.vulnerable.full_name + \
                   "You will now receive alerts. Original missing report:\n%s" % link
    else:
        sms_text = "C-ASAP Missing Client: %s has been recently updated at a location near you.\n" % notify_record.vulnerable.full_name + \
                   "You will now receive alerts. Original missing report:\n%s" % link + \
                   "\nQuick tip: %s" % notify_record.vulnerable.instructions

    mail_subject = "C-ASAP Client: %s has been recently updated at a location near you." % notify_record.vulnerable.full_name
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), sms_text)
    if vol.email:
        SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()


def update_notification(notify_record, vol):
    vol = Volunteer.objects.get(id=vol)
    # link = "http://{}".format(notify_record.get_link())
    link = shorten_url(notify_record.get_link())

    if not notify_record.vulnerable.instructions:
        sms_text = "C-ASAP Missing Client: %s has been updated near you.\n" % notify_record.vulnerable.full_name + \
                   "For more details visit the link below:\n%s" % link
    else:
        sms_text = "C-ASAP Missing Client: %s has been updated near you.\n" % notify_record.vulnerable.full_name + \
                   "For more details visit the link below:\n%s" % link + \
                   "\nQuick tip: %s" % notify_record.vulnerable.instructions

    mail_subject = "C-ASAP Client: %s has been updated near you " % notify_record.vulnerable.full_name
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), sms_text)
    if vol.email:
        SimpleMailHelper(mail_subject, sms_text, sms_text, vol.email).send_email()


def send_alert_email(profile, lost_alert):
    text = "%s: a new notification needs your attention. Please click the link below to view it. \n %s" % (
        profile.full_name, lost_alert.get_link())
    mail_subject = "C-ASAP Admin: New Notification Alert"
    SimpleMailHelper(mail_subject, text, text, profile.user.email).send_email()


def update_clean_vulnerable(vulnerable, vul_form):
    vulnerable.nickname = vul_form.cleaned_data.get('nickname')
    vulnerable.sex = vul_form.cleaned_data.get('sex')
    vulnerable.race = vul_form.cleaned_data.get('race')
    vulnerable.hair_colour = vul_form.cleaned_data.get('hair_colour')
    vulnerable.height = vul_form.cleaned_data.get('height')
    vulnerable.weight = vul_form.cleaned_data.get('weight')
    vulnerable.eye_colour = vul_form.cleaned_data.get('eye_colour')
    vulnerable.favourite_locations = vul_form.cleaned_data.get('favourite_locations')
    vulnerable.work_action = vul_form.cleaned_data.get('work_action')
    if vul_form.cleaned_data.get('transportation'):
        vulnerable.transportation = vul_form.cleaned_data.get('transportation')
    if vul_form.cleaned_data.get('instructions'):
        vulnerable.instructions = vul_form.cleaned_data.get('instructions')
    vulnerable.save()


def update_vulnerable(vulnerable, vul_form):
    vulnerable.nickname = vul_form.data.get('nickname')
    vulnerable.sex = vul_form.data.get('sex')
    vulnerable.race = vul_form.data.get('race')
    vulnerable.hair_colour = vul_form.data.get('hair_colour')
    vulnerable.height = vul_form.data.get('height')
    vulnerable.weight = vul_form.data.get('weight')
    vulnerable.eye_colour = vul_form.data.get('eye_colour')
    vulnerable.favourite_locations = vul_form.data.get('favourite_locations')
    vulnerable.work_action = vul_form.cleaned_data.get('work_action')
    if vul_form.data.get('transportation'):
        vulnerable.transportation = vul_form.data.get('transportation')
    if vul_form.cleaned_data.get('instructions'):
        vulnerable.instructions = vul_form.cleaned_data.get('instructions')
    vulnerable.save()


def create_lost_activity(lost_record):
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


@login_required
def report_lost_view(request):
    if request.method == "POST":
        form = LostPersonRecordForm(request.POST)
        vul_form = VulnerableReportForm(request.POST)
        request.context['next'] = request.POST.get("next", reverse("index"))
        if form.is_valid() and vul_form.is_valid():
            vulnerable = Vulnerable.objects.filter(hash=request.POST.get("vulnerable")).first()
            if vulnerable:
                update_clean_vulnerable(vulnerable, vul_form)
                lost_record = form.save(request.user, vulnerable)
                # Save the list of volunteer ids to the lost record
                x = list(generate_volunteers(lost_record))
                lost_record.volunteer_list = json.dumps(x)
                lost_record.save()
                create_lost_activity(lost_record)
                flag = 1
                notify_volunteers(lost_record, flag)
                # send_tweet(
                #     tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(),
                #                  flag, lost_record.time))
            add_message(request, messages.SUCCESS, "Success")
            return HttpResponseRedirect(reverse('index'))
        else:
            vulnerable = Vulnerable.objects.filter(hash=request.POST.get("vulnerable")).first()
            if vulnerable:
                update_vulnerable(vulnerable, vul_form)
                lost_record = new_lost_record(request.user, vulnerable, form.data.get('address'), form.data.get('time'),
                                              request.context.get('user_tz_name'))
                x = list(generate_volunteers(lost_record))
                lost_record.volunteer_list = json.dumps(x)
                lost_record.save()
                create_lost_activity(lost_record)
                time_seen = datetime.datetime.now(pytz.timezone(request.context.get('user_tz_name'))).strftime(
                    "%H:%M")
                flag = 1
                notify_volunteers(lost_record, flag)
                # send_tweet(
                #     tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(),
                #                  flag, lost_record.time))
            add_message(request, messages.SUCCESS, "Success")
            return HttpResponseRedirect(reverse('index'))
    else:
        form = LostPersonRecordForm(initial=dict(time=get_user_time(request)))
        vul_form = VulnerableReportForm()
        request.context['next'] = request.GET.get("next", reverse("index"))

    profile = request.context['user_profile']
    request.context['form'] = form
    request.context['vul_form'] = vul_form
    request.context['all_timezones'] = pytz.all_timezones
    request.context['vulnerable_people'] = [dict(hash=vul.hash, name=vul.full_name) for vul in Vulnerable.objects.all()]
    request.context['user_tz_name'] = 'Canada/Mountain'  # This needs to be changed when multiple timezones will be used
    return render(request, "report/report_lost.html", request.context)


def new_lost_record(reporter, vulnerable, address, time, zone):
    """
    This function is used to create a new lost record, due to an error occuring on the server.

    :param zone:
    :param reporter:
    :param vulnerable:
    :param address:
    :param time:
    :return:
    """
    lost_rec = LostPersonRecord()

    map_response = get_address_map_google(address)
    for i in range(10):
        if map_response is None:
            map_response = get_address_map_google(address)
        else:
            break
    lost_rec.address_lat = map_response['lat']
    lost_rec.address_lng = map_response['lng']
    lost_rec.address = address
    lost_rec.reporter = reporter
    lost_rec.vulnerable = vulnerable
    lost_rec.state = "reported"
    lost_rec.time = pytz.timezone(zone).localize(time.replace(tzinfo=None))
    return lost_rec


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
            lost_alert = Alerts(
                state='Sighted', lost_record=lost_record, seen_record=sighting_record
            )
            lost_alert.save()
            for coord in coordinators:
                send_alert_email(coord, lost_alert)
            success_msg = "Community coordinator has been notified of an update."
            add_message(request, messages.SUCCESS, success_msg)
            return HttpResponseRedirect(reverse('index'))
        else:
            add_message(request, messages.ERROR, "Something went wrong.")
            return HttpResponseRedirect(reverse('index'))

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
    update_rec = TempSightingRecord.objects.filter(hash=alert.seen_record.hash).first()
    form = SightingRecordForm(request.POST)
    if request.method == 'POST':
        if 'sendAlert' in request.POST:
            alert = Alerts.objects.filter(hash=hash).first()
            update_rec = TempSightingRecord.objects.filter(hash=alert.seen_record.hash).first()
            lost_rec = alert.lost_record
            add_seen = SightingRecord(time=update_rec.time, address=update_rec.address,
                                      address_lat=update_rec.address_lat, address_lng=update_rec.address_lng,
                                      description=update_rec.description, lost_record=update_rec.lost_record,
                                      reporter=update_rec.reporter)
            add_seen.save()
            alert.sent = True
            alert.save()
            activity = Activity()
            activity.locLat = add_seen.address_lat
            activity.locLon = add_seen.address_lng
            activity.person_id = add_seen.lost_record.vulnerable_id
            activity.time = add_seen.time
            activity.adminPoint = Point(float(activity.locLon), float(activity.locLat), srid=3857)
            fence_loc = Location.objects.filter(fence__contains=activity.adminPoint)
            if fence_loc:
                activity.location = fence_loc[0]
            activity.save()
            add_seen.lost_record.state = "sighted"
            add_seen.lost_record.save()
            # Include new volunteers
            json_dec = json.decoder.JSONDecoder()
            try:
                volunteer_list = json_dec.decode(lost_rec.volunteer_list)
            except:
                volunteer_list = list()
            new_volunteers, user_ids = generate_updated_volunteers(add_seen, volunteer_list)
            for i in new_volunteers:
                new_update_notification(lost_rec, i)
            for j in volunteer_list:
                update_notification(lost_rec, j)
                # Send sighting to original list
            send_onesignal_sighting(lost_rec, add_seen, volunteer_list)
            if new_volunteers:
                volunteer_list.extend(new_volunteers)
                # Send sighting to new list
                send_new_sighting_onesignal_notification(lost_rec, add_seen, user_ids)
            lost_rec.volunteer_list = json.dumps(volunteer_list)
            lost_rec.save()
            add_message(request, messages.SUCCESS, "Update successfully sent.")
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
            update_rec = TempSightingRecord.objects.filter(hash=alert.seen_record.hash).first()
            if update_rec:
                update_rec.delete()
            add_message(request, messages.SUCCESS, "Update has been ignored.")
            return HttpResponseRedirect(reverse("index"))

    form = SightingRecordForm(initial=model_to_dict(update_rec))
    request.context['form'] = form
    request.context['alert'] = alert
    request.context['rec'] = update_rec
    request.context['all_timezones'] = pytz.all_timezones
    request.context['user_tz_name'] = 'Canada/Mountain'
    return render(request, "alert_view.html", request.context)


def send_onesignal_sighting(lost_rec, add_seen, vol_list):
    user_list = list()
    for i in vol_list:
        vol = Volunteer.objects.get(id=i)
        user_list.append(vol.profile.user.id)

    send_sighting_onesignal_notification(user_list, lost_rec, add_seen)


def send_onesignal_found(lost_rec, vol_list):
    user_list = list()
    for i in vol_list:
        vol = Volunteer.objects.get(id=i)
        user_list.append(vol.profile.user.id)

    send_found_onesignal_notification(user_list, lost_rec)


def notify_volunteers(notify_record, flag):
    lat, lng = notify_record.address_lat, notify_record.address_lng
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    lng, lat = transform(inProj, outProj, float(lng), float(lat))
    close_volunteers = set()
    user_ids = []
    for vol in Volunteer.objects.all():
        availability = VolunteerAvailability.objects.filter(volunteer=vol)
        for x in availability:
            if (vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= x.km_radius):
                close_volunteers.add(vol)
                user_ids.append(vol.profile.user.id)

    # Onesignal notifications
    send_missing_onesignal_notification(user_ids, notify_record)

    for vol in close_volunteers:
        # if flag == 1:
        lost_notification(notify_record, vol)
        # else:
        #     seen_notification(notify_record, vol, notif)


def generate_updated_volunteers(notify_record, volunteer_list):
    """
    This function will generate new volunteers based on the new location.

    :param notify_record:
    :param volunteer_list:
    :return: close_volunteers list
    """
    lat, lng = notify_record.address_lat, notify_record.address_lng
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    lng, lat = transform(inProj, outProj, float(lng), float(lat))
    close_volunteers = set()
    user_ids = list()

    for vol in Volunteer.objects.all():
        if vol.id not in volunteer_list:
            availability = VolunteerAvailability.objects.filter(volunteer=vol)
            for x in availability:
                if vincenty((x.address_lat, x.address_lng), (lat, lng)).kilometers <= x.km_radius:
                    close_volunteers.add(vol.id)
                    user_ids.append(vol.profile.user.id)

    return close_volunteers, user_ids


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
                send_onesignal_found(lost_record, volunteer_list)
            # send_tweet(tweet_helper(lost_record.vulnerable.full_name, lost_record.get_link(), 2, v.time))
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
    # link = "http://{}".format(record.get_link())
    link = shorten_url(record.get_link())
    message = "Dear {}: {} has been found at {}. For more details visit the link below: {}".format(vol.full_name,
                                                                                                   record.vulnerable.full_name,
                                                                                                   v.time.time().strftime(
                                                                                                       '%H:%M'), link)
    if vol.phone:
        send_sms(get_standard_phone(vol.phone), message)
    if vol.email:
        mail_subject = "C-ASAP Client: {} has been found".format(record.vulnerable.full_name)
        SimpleMailHelper(mail_subject, message, message, vol.email).send_email()
    # if vol.twitter_handle:
    #     send_twitter_dm(message, vol.twitter_handle)

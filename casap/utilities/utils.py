import hashlib
import json
import threading
import urllib

import time
from random import randint

import sys

import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import twitter
from requests import HTTPError
from twilio.rest import Client
import phonenumbers as phonenumbers
import pytz
import requests
from django.core.mail import send_mail
import onesignal as onesignal_sdk

from casap import settings
from django.utils import timezone


def url_with_params(path, parameters_dict=None):
    if parameters_dict is None:
        parameters_dict = dict()
    if path[-3:] == "%3F":
        path = path[:-3]
    return path + '?' + urllib.parse.urlencode(parameters_dict)


def unquote_redirect_url(url):
    url = urllib.parse.unquote(url)
    if url.endswith("/") and not url == '/':
        return url[:-1]
    return url


def normalize_email(email):
    """
    Normalize the email address by lowercasing the domain part of it.
    """
    email = email or ''
    try:
        email_name, domain_part = email.strip().rsplit('@', 1)
    except ValueError:
        pass
    else:
        email = '@'.join([email_name, domain_part.lower()])
    return email.lower()


def gen_hash(model_id, length=None):
    hash = hashlib.sha1()
    hash.update((str(model_id) + '!#@$%&^*CASAP' + str(time.time())).encode("utf-8"))
    if length is None:
        return hash.hexdigest()[-10:]
    else:
        return hash.hexdigest()[-length:]


def gen_unique_hash(model_class, length, all_caps=None, field_name=None):
    if all_caps is None:
        all_caps = False
    if field_name is None:
        field_name = "hash"
    field_name += "__iexact"
    id = model_class.objects.count()
    unique_hash = gen_hash(id, length)
    while model_class.objects.filter(**{field_name: unique_hash}).exists():
        id += randint(1, sys.maxint)
        unique_hash = gen_hash(id, length)
    return unique_hash.upper() if all_caps else unique_hash


def get_standard_phone(raw_phone, ignore_error=None):
    if raw_phone in ("911", "999"):
        return raw_phone
    try:
        non_decimal = re.compile(r'[^\d]+')
        if raw_phone.find("+1") != -1:
            raw_phone = raw_phone[2:]
        raw_phone = non_decimal.sub('', raw_phone)
        phone = "+1" + raw_phone
        phone_obj = phonenumbers.parse(phone, "CA")
        return "+1" + str(phone_obj.national_number)
    except:
        if ignore_error:
            return raw_phone
        return None


def get_address_map_google(address):
    try:
        address.replace(",", " ")
        address.replace("'", "")
        endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
        api = 'AIzaSyCaiM53DTZi0ASuIIGY6yudqE9nPoThVsE'
        resp = requests.get(endpoint, params=dict(address=address, key=api))

        ans = dict()
        results = json.loads(resp.text)['results']
        if len(results) == 0:
            return None
        latlng = results[0]['geometry']['location']
        ans['lat'] = str(latlng['lat'])
        ans['lng'] = str(latlng['lng'])

        try:
            postal_code = \
                [item for item in json.loads(resp.text)['results'][0]['address_components'] if
                 "postal_code" in item['types']][
                    0]['short_name']
            ans['postal_code'] = postal_code
        except:
            pass
        city = [item for item in json.loads(resp.text)['results'][0]['address_components'] if
                "administrative_area_level_3" in item['types'] or "locality" in item['types']][0]['short_name']
        province = [item for item in json.loads(resp.text)['results'][0]['address_components'] if
                    "administrative_area_level_1" in item['types']][0]['short_name']
        ans['city'] = city
        ans['province'] = province
        return ans
    except Exception as e:
        return None


def get_address_map_open_street(address):
    try:
        address.replace(",", "")
        address.replace("'", "")
        geocode_url = "http://nominatim.openstreetmap.org/search/%s/" % address
        req = requests.get(geocode_url, params=dict(format="json", addressdetails=1, limit=1, ))
        response_json = req.json()
        ans = dict()
        ans['lat'] = response_json[0]['lat']
        ans['lng'] = response_json[0]['lng']
        print(json.dumps(response_json))
        return ans
    except Exception as e:
        return None


def get_user_time(request, now=None):
    if now is None:
        now = timezone.now()
    user_tz_name = request.context.get('user_tz_name')
    if user_tz_name:
        return now.astimezone(pytz.timezone(user_tz_name))
    return now


client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(number, text):
    try:
        client.messages.create(
            to=number,
            from_=settings.TWILIO_NUMBER,
            body=text
        )
    except Exception as e:
        return False
    return True


class BaseMailHelper(object):
    def __init__(self):
        self.context = dict()
        self.context['domain'] = settings.DOMAIN


class SimpleMailHelper(BaseMailHelper):
    def __init__(self, subject, mail_text, mail_html, recipient):
        super(SimpleMailHelper, self).__init__()
        self.subject = subject
        self.mail_text = mail_text
        self.mail_html = mail_html
        self.recipient = recipient

    def send_email(self):
        t = threading.Thread(target=self.send_thread, args=[])
        t.setDaemon(False)
        t.start()

    def send_thread(self):
        send_mail(
            self.subject,
            self.mail_text,
            settings.DEFAULT_EMAIL_FROM,
            [self.recipient],
            html_message=self.mail_html,
        )


def send_tweet(tweet):
    api = twitter.Api(consumer_key=settings.TWITTER_CONSUMER_KEY, consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                      access_token_key=settings.TWITTER_ACCESS_KEY, access_token_secret=settings.TWITTER_ACCESS_SECRET)

    api.PostUpdate(tweet)


def shorten_url(url):
    try:
        params = urlencode(
            {'longUrl': url, 'login': settings.BITLY_API_USER, 'apiKey': settings.BITLY_API_KEY, 'format': 'json'})
        req = Request("http://api.bit.ly/v3/shorten?%s" % params)
        response = urlopen(req)
        j = json.loads(response.read().decode('utf-8'))
        if j['status_code'] == 200:
            return j['data']['url']
        raise Exception('%s' % j['status_txt'])
    except HTTPError as e:
        raise ('HTTP error%s' % e.read())


def validate_twitter_handle(handle):
    api = twitter.Api(consumer_key=settings.TWITTER_CONSUMER_KEY, consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                      access_token_key=settings.TWITTER_ACCESS_KEY, access_token_secret=settings.TWITTER_ACCESS_SECRET)

    api.GetUser(screen_name=handle)


def send_twitter_dm(message, user):
    api = twitter.Api(consumer_key=settings.TWITTER_CONSUMER_KEY, consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                      access_token_key=settings.TWITTER_ACCESS_KEY, access_token_secret=settings.TWITTER_ACCESS_SECRET)

    api.PostDirectMessage(message, screen_name=user)


# def create_payload_data(data):
#     filter_list = list()
#
#     for i, item in enumerate(data):
#         if i < len(data) - 1:
#             filter_list.append({"field": "tag", "key": "id", "relation": "=", "value": str(item)})
#             filter_list.append({"operator": "OR"})
#         else:
#             filter_list.append({"field": "tag", "key": "id", "relation": "=", "value": str(item)})
#
#     payload = {"app_id": settings.ONESIGNAL_APP_ID,
#                "filters": filter_list,
#                "template_id": settings.ONESIGNAL_MISSING_ID,
#                }
#
#     return payload


def send_missing_onesignal_notification(data, notify_record):
    filter_list = list()

    for i, item in enumerate(data):
        if i < len(data) - 1:
            filter_list.append({"field": "tag", "key": "id", "relation": "=", "value": str(item)})
            filter_list.append({"operator": "OR"})
        else:
            filter_list.append({"field": "tag", "key": "id", "relation": "=", "value": str(item)})

    onesignal_client = onesignal_sdk.Client(user_auth_key=settings.ONESIGNAL_AUTH_KEY,
                                            app={"app_auth_key": settings.ONESIGNAL_REST_KEY,
                                                 "app_id": settings.ONESIGNAL_APP_ID})

    # create a notification
    new_notification = onesignal_sdk.Notification()
    new_notification.set_parameter("contents", {
        "en": "Last seen near: {}. Has {} hair and is wearing {}.".format(notify_record.intersection,
                                                                          notify_record.vulnerable.hair_colour,
                                                                          notify_record.description)})
    new_notification.set_parameter("headings", {"en": "MISSING: {}".format(notify_record.vulnerable.full_name)})
    new_notification.set_parameter("template_id", settings.ONESIGNAL_MISSING_TEMPLATE_ID)
    print("{}/media/{}".format(settings.DOMAIN, notify_record.vulnerable.picture))
    new_notification.set_parameter("ios_attachments",
                                   {
                                       "id": "{}/media/{}".format(settings.DOMAIN, notify_record.vulnerable.picture)})

    # set filters
    new_notification.set_filters(filter_list)

    # send notification, it will return a response
    onesignal_response = onesignal_client.send_notification(new_notification)
    print(onesignal_response.status_code)
    print(onesignal_response.json())

import hashlib
import json
import threading
import urllib

import time
from random import randint

import sys

import re

from twilio.rest import Client
import phonenumbers as phonenumbers
import pytz
import requests
from django.core.mail import send_mail

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
        endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
        resp = requests.get(endpoint, params=dict(address=address))

        ans = dict()
        results = json.loads(resp.text)['results']
        if len(results) == 0:
            return None
        latlng = results[0]['geometry']['location']
        ans['lat'] = str(latlng['lat'])
        ans['lng'] = str(latlng['lng'])
        postal_code = [item for item in json.loads(resp.text)['results'][0]['address_components'] if "postal_code" in item['types']][0]['short_name']
        city = [item for item in json.loads(resp.text)['results'][0]['address_components'] if "administrative_area_level_3" in item['types'] or "locality" in item['types']][0]['short_name']
        province = [item for item in json.loads(resp.text)['results'][0]['address_components'] if "administrative_area_level_1" in item['types']][0]['short_name']
        ans['postal_code'] = postal_code
        ans['city'] = city
        ans['province'] = province
        return ans
    except Exception as e:
        return None


def get_address_map_open_street(address):
    try:
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
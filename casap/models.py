import os
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point

from multiselectfield import MultiSelectField
from pyproj import Proj, transform
from django.db import IntegrityError
from django.db import transaction

from casap import settings
from casap.utilities.utils import gen_unique_hash


def get_vulnerable_picture_path(instance, filename=None):
    _, file_ext = os.path.splitext(filename)
    return os.path.join('users', 'vulnerable', instance.hash, "profile_picture" + file_ext)


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)
    phone_validated = models.BooleanField(default=False)
    coordinator_email = models.BooleanField(default=False)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    @property
    def full_name(self):
        return self.user.get_full_name()

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.user)


class EmailConfirmationCode(models.Model):
    user = models.ForeignKey(User)
    code = models.CharField(max_length=120)
    creation_time = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = gen_unique_hash(self.__class__, 120, field_name="code")
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.user)


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User)
    code = models.CharField(max_length=120)
    creation_time = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = gen_unique_hash(self.__class__, 120, field_name="code")
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u'%s - %s' % (self.user.email, self.code)


class Notifications(models.Model):
    phone_notify = models.BooleanField(default=True)
    email_notify = models.BooleanField(default=True)
    twitter_dm_notify = models.BooleanField(default=True)
    twitter_public_notify = models.BooleanField(default=True)

    def __str__(self):
        return u'phone: %s, email: %s, dms: %s, public: %s' % (
            self.phone_notify, self.email_notify, self.twitter_dm_notify, self.twitter_public_notify)


class Volunteer(models.Model):
    profile = models.OneToOneField(Profile, related_name="volunteer")
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.TextField(max_length=50, null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    @property
    def full_name(self):
        return self.profile.full_name

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.profile)


PROVINCE_CHOICES = (
    ('AB', 'AB'),
    ('BC', 'BC'),
    ('MB', 'MB'),
    ('NB', 'NB'),
    ('NL', 'NL'),
    ('NS', 'NS'),
    ('NT', 'NT'),
    ('NU', 'NU'),
    ('ON', 'ON'),
    ('PE', 'PE'),
    ('QC', 'QC'),
    ('SK', 'SK'),
    ('YT', 'YT'),
)

SEX_CHOICES = (
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Other', 'Other'),
)

RACE_CHOICES = (
    ('Aboriginal', 'Aboriginal'),
    ('Arab/West Asian', 'Arab/West Asian'),
    ('Black', 'Black'),
    ('Chinese', 'Chinese'),
    ('Filipino', 'Filipino'),
    ('Japanese', 'Japanese'),
    ('Korean', 'Korean'),
    ('Latin American', 'Latin American'),
    ('South Asian', 'South Asian'),
    ('South East Asian', 'South East Asian'),
    ('White (Caucasian)', 'White (Caucasian)'),
    ('Other', 'Other'),
)

HAIR_CHOICES = (
    ('Brown', 'Brown'),
    ('Blonde', 'Blonde'),
    ('Black', 'Black'),
    ('Grey', 'Grey'),
    ('Red', 'Red'),
    ('White', 'White'),
    ('No hair', 'No hair'),
    ('Other', 'Other'),
)

HEIGHT_CHOICES = [(x, x) for x in range(140, 200)]
WEIGHT_CHOICES = [(x, x) for x in range(30, 140)]

EYE_COLOUR_CHOICES = (
    ('Blue', 'Blue'),
    ('Brown', 'Brown'),
    ('Green', 'Green'),
    ('Hazel', 'Hazel'),
)

KM_CHOICES = (
    (1, 1),
    (3, 3),
    (6, 6),
    (9, 9),
    (12, 12),
    (25, 25),
)


class VolunteerAvailability(models.Model):
    volunteer = models.ForeignKey(Volunteer, related_name="volunteers")
    address = models.CharField(max_length=200)
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    km_radius = models.IntegerField(choices=KM_CHOICES, default=1)

    def __str__(self):
        return u"%s - %s km %s" % (
            self.volunteer, self.address, self.km_radius)


class Vulnerable(models.Model):
    creator = models.ForeignKey(Profile, related_name="vulnerable_people")
    creation_time = models.DateTimeField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, null=True, blank=True)
    birthday = models.DateField()
    picture = models.ImageField(upload_to=get_vulnerable_picture_path, null=True, blank=True)
    sex = models.CharField(max_length=50, choices=SEX_CHOICES)
    race = models.CharField(max_length=150, choices=RACE_CHOICES)
    hair_colour = models.CharField(max_length=50, choices=HAIR_CHOICES)
    height = models.IntegerField(choices=HEIGHT_CHOICES)
    weight = models.IntegerField(choices=WEIGHT_CHOICES)
    eye_colour = models.CharField(max_length=50, choices=EYE_COLOUR_CHOICES)
    favourite_locations = models.TextField()
    description = models.TextField(null=True, blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)
        super(self.__class__, self).save(*args, **kwargs)

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    def __str__(self):
        return u"%s [creator: %s]" % (self.full_name, self.creator)


class VulnerableAddress(models.Model):
    vulnerable = models.ForeignKey(Vulnerable, related_name="addresses")
    address = models.TextField()
    street = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=50, null=True)
    province = models.CharField(max_length=4, choices=PROVINCE_CHOICES, default='ab')
    address_lat = models.FloatField()
    address_lng = models.FloatField()

    def __str__(self):
        return u"%s - %s" % (self.vulnerable, self.address)

    def save(self, *args, **kwargs):
        inProj = Proj(init='epsg:4326')
        outProj = Proj(init='epsg:3857')
        try:
            self.address_lng, self.address_lat = transform(inProj, outProj, float(self.address_lng),
                                                           float(self.address_lat))
        except Exception as e:
            print(e)  # must be in correct coord system

        super(self.__class__, self).save(*args, **kwargs)


class LostPersonRecord(models.Model):
    reporter = models.ForeignKey(User, related_name="lost_reports")
    vulnerable = models.ForeignKey(Vulnerable, related_name="lost_records")
    state = models.CharField(max_length=20, choices=[("reported", "Reported missing"),
                                                     ("sighted", "Reported as sighted"),
                                                     ("found", "Reported found")])
    time = models.DateTimeField()
    address = models.TextField()
    street = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=50, null=True)
    province = models.CharField(max_length=4, choices=PROVINCE_CHOICES, default='ab')
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    description = models.TextField(blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)
    volunteer_list = models.TextField(null=True)  # JSON-serialized (text) version of relevant volunteer ids

    def get_link(self):
        return "%s%s" % (settings.DOMAIN, reverse("track_missing", kwargs=dict(hash=self.hash)))

    def get_sighting_records(self):
        return self.sighting_records.order_by("time").all()

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)

        inProj = Proj(init='epsg:4326')
        outProj = Proj(init='epsg:3857')
        try:
            self.address_lng, self.address_lat = transform(inProj, outProj, float(self.address_lng),
                                                           float(self.address_lat))
        except Exception as e:
            print(e)  # must be in correct coord system

        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u"%s reported %s" % (self.reporter, self.vulnerable)


class SightingRecord(models.Model):
    lost_record = models.ForeignKey(LostPersonRecord, related_name="sighting_records")
    reporter = models.ForeignKey(User, related_name="sighting_records")
    time = models.DateTimeField()
    address = models.TextField()
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    description = models.TextField(blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    def get_link(self):
        return "%s%s" % (settings.DOMAIN, reverse("track_missing", kwargs=dict(hash=self.hash)))

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)

        inProj = Proj(init='epsg:4326')
        outProj = Proj(init='epsg:3857')
        try:
            self.address_lng, self.address_lat = transform(inProj, outProj, float(self.address_lng),
                                                           float(self.address_lat))
        except Exception as e:
            print(e)  # must be in correct coord system

        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u"%s sighted %s" % (self.reporter, self.lost_record)


class FindRecord(models.Model):
    lost_record = models.ForeignKey(LostPersonRecord, related_name="find_records")
    reporter = models.ForeignKey(User, related_name="find_records")
    time = models.DateTimeField()
    street = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=50, null=True)
    province = models.CharField(max_length=4, choices=PROVINCE_CHOICES, default='ab')
    address = models.TextField()
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    description = models.TextField(blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)

        inProj = Proj(init='epsg:4326')
        outProj = Proj(init='epsg:3857')
        try:
            self.address_lng, self.address_lat = transform(inProj, outProj, float(self.address_lng),
                                                           float(self.address_lat))
        except Exception as e:
            print(e)  # must be in correct coord system

        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u"%s found %s" % (self.reporter, self.lost_record)


class Activity(models.Model):
    category = models.CharField(max_length=20, default='Location')
    person = models.ForeignKey('Vulnerable', null=True, related_name='activities')
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100, default="Reported seen")
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.SET_NULL)
    adminPoint = models.PointField(null=True, srid=3857)
    locLat = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    locLon = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    # sighting_id = models.ForeignKey('SightingRecord', null=True, related_name='activities')

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)

    def save(self, *args, **kwargs):

        if self.adminPoint:
            self.locLat = self.adminPoint.y
            self.locLon = self.adminPoint.x

        else:
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            try:
                self.locLon, self.locLat = transform(inProj, outProj, float(self.locLon), float(self.locLat))
                pnt = Point(self.locLon, self.locLat, srid=3857)
                # see if in geofence
                if not self.location:
                    fence_loc = Location.objects.filter(fence__contains=pnt)
                    if fence_loc:
                        self.location = fence_loc[0]
            except Exception as e:
                print(e)  # must be in correct coord system

        super(Activity, self).save(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(Activity, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'


class LostActivity(models.Model):
    category = models.CharField(max_length=20, default='Location')
    person = models.ForeignKey('Vulnerable', null=True, related_name='lostactivities')
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100, default="Reported lost")
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.SET_NULL)
    adminPoint = models.PointField(null=True, srid=3857)
    locLat = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    locLon = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)

    def save(self, *args, **kwargs):

        if self.adminPoint:
            self.locLat = self.adminPoint.y
            self.locLon = self.adminPoint.x

        else:
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            try:
                self.locLon, self.locLat = transform(inProj, outProj, float(self.locLon), float(self.locLat))
                pnt = Point(self.locLon, self.locLat, srid=3857)
                # see if in geofence
                if not self.location:
                    fence_loc = Location.objects.filter(fence__contains=pnt)
                    if fence_loc:
                        self.location = fence_loc[0]
            except Exception as e:
                print(e)  # must be in correct coord system

        super(LostActivity, self).save(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(LostActivity, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'LostActivity'
        verbose_name_plural = 'LostActivities'


class FoundActivity(models.Model):
    category = models.CharField(max_length=20, default='Location')
    person = models.ForeignKey('Vulnerable', null=True, related_name='foundactivities')
    time = models.DateTimeField()
    activity_type = models.CharField(max_length=100, default="Reported found")
    location = models.ForeignKey('Location', null=True, blank=True, on_delete=models.SET_NULL)
    adminPoint = models.PointField(null=True, srid=3857)
    locLat = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    locLon = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return "%s %s - %s" % (str(self.time), self.person.__str__(), self.activity_type)

    def save(self, *args, **kwargs):

        if self.adminPoint:
            self.locLat = self.adminPoint.y
            self.locLon = self.adminPoint.x

        else:
            inProj = Proj(init='epsg:4326')
            outProj = Proj(init='epsg:3857')
            try:
                self.locLon, self.locLat = transform(inProj, outProj, float(self.locLon), float(self.locLat))
                pnt = Point(self.locLon, self.locLat, srid=3857)
                # see if in geofence
                if not self.location:
                    fence_loc = Location.objects.filter(fence__contains=pnt)
                    if fence_loc:
                        self.location = fence_loc[0]
            except Exception as e:
                print(e)  # must be in correct coord system

        super(FoundActivity, self).save(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(FoundActivity, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'FoundActivity'
        verbose_name_plural = 'FoundActivities'


class Location(models.Model):
    SOCIAL = 'Social'
    HEALTH = 'Health'
    HOME = 'Home'
    OTHER = 'Other'
    HARMFUL = 'Harmful'
    LOCATION_CATEGORIES = (
        (u'SOCIAL', u'Social'),
        (u'HEALTH', u'Health'),
        (u'HOME', u'Home'),
        (u'OTHER', u'Other'),
        (u'HARMFUL', u'Harmful/Hazardous place'),
    )
    name = models.CharField(max_length=200, default='', unique=True)
    person = models.ForeignKey('Vulnerable', null=True, blank=True)
    category = MultiSelectField(choices=LOCATION_CATEGORIES, default=u'OTHER', null=False)
    description = models.CharField(max_length=250)
    addit_info = models.CharField(max_length=250, null=True, blank=True, default='')
    fence = models.MultiPolygonField(srid=3857)

    # GeoDjango-specific: a geometry field (MultiPolygonField)

    def update(self, *args, **kwargs):
        super(Location, self).save(*args, **kwargs)

    # 25719793
    # Returns the string representation of the model.
    def __str__(self):  # __unicode__ on Python 2
        return self.name

    def save(self, *args, **kwargs):
        print(self.name)
        try:
            with transaction.atomic():
                super(Location, self).save(*args, **kwargs)
        except IntegrityError as e:
            pass
            # self.name = self.name + "salt:" +str(randint(0,1000))


class Alerts(models.Model):
    state = models.CharField(max_length=15)
    lost_record = models.ForeignKey(LostPersonRecord, related_name="lost_records")
    seen_record = models.ForeignKey(SightingRecord, blank=True, null=True, related_name="seen_records")
    notifications = models.ForeignKey(Notifications, related_name="notifications")
    sent = models.BooleanField(default=False)
    hash = models.CharField(max_length=30, unique=True, blank=True, null=True)

    def __str__(self):
        return u'state: %s, lost: %s, seen: %s, notifications: %s' % (
            self.state, self.lost_record, self.seen_record, self.notifications)

    def get_link(self):
        return "%s%s" % (settings.DOMAIN, reverse("report_alert", kwargs=dict(hash=self.hash)))

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)

        super(self.__class__, self).save(*args, **kwargs)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

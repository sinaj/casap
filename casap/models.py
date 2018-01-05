import os
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.urlresolvers import reverse

from casap import settings
from casap.utils import gen_unique_hash


def get_vulnerable_picture_path(instance, filename=None):
    _, file_ext = os.path.splitext(filename)
    return os.path.join('users', 'vulnerable', instance.hash, "profile_picture" + file_ext)


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)
    phone_validated = models.BooleanField(default=False)
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
        return str(self.__unicode__())


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


class Volunteer(models.Model):
    profile = models.OneToOneField(Profile, related_name="volunteer")
    phone = models.CharField(max_length=15)
    personal_address = models.TextField(default="")
    personal_lat = models.FloatField()
    personal_lng = models.FloatField()
    business_address = models.TextField(default="")
    business_lat = models.FloatField()
    business_lng = models.FloatField()
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


class Vulnerable(models.Model):
    creator = models.ForeignKey(Profile, related_name="vulnerable_people")
    creation_time = models.DateTimeField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    description = models.TextField()
    birthday = models.DateField()
    picture = models.ImageField(upload_to=get_vulnerable_picture_path, null=True, blank=True)
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
    address_lat = models.FloatField()
    address_lng = models.FloatField()

    def __str__(self):
        return u"%s - %s" % (self.vulnerable, self.address)


class LostPersonRecord(models.Model):
    reporter = models.ForeignKey(User, related_name="lost_reports")
    vulnerable = models.ForeignKey(Vulnerable, related_name="lost_records")
    state = models.CharField(max_length=20, choices=[("reported", "Reported missing"),
                                                     ("sighted", "Reported as sighted"),
                                                     ("found", "Reported found")])
    time = models.DateTimeField()
    address = models.TextField()
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    description = models.TextField(blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    def get_sighting_records(self):
        return self.sighting_records.order_by("time").all()

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)
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
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u"%s sighted %s" % (self.reporter, self.lost_record)


class FindRecord(models.Model):
    lost_record = models.ForeignKey(LostPersonRecord, related_name="find_records")
    reporter = models.ForeignKey(User, related_name="find_records")
    time = models.DateTimeField()
    address = models.TextField()
    address_lat = models.FloatField()
    address_lng = models.FloatField()
    description = models.TextField(blank=True)
    hash = models.CharField(max_length=30, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.hash:
            self.hash = gen_unique_hash(self.__class__, 30)
        super(self.__class__, self).save(*args, **kwargs)

    def __str__(self):
        return u"%s found %s" % (self.reporter, self.lost_record)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

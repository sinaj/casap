from django.contrib.auth.models import User
from rest_framework import serializers

from casap.models import Profile, Volunteer, VolunteerAvailability, Vulnerable


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'first_name', 'last_name', 'is_staff')


class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Profile
        fields = ('url', 'user_id', 'user', 'hash')


class VolunteerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Volunteer
        fields = ('url', 'id', 'profile', 'phone', 'email')


class VolunteerAvailabilitySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = VolunteerAvailability
        fields = (
            'url', 'id', 'volunteer', 'address', 'address_lat', 'address_lng', 'km_radius', 'city', 'province',
            'street')


class VulnerableSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Vulnerable
        fields = (
            'id', 'creation_time', 'first_name', 'last_name', 'nickname', 'birthday', 'picture', 'hash', 'creator_id',
            'sex', 'race', 'eye_colour', 'hair_colour', 'height', 'weight', 'favourite_locations'
        )

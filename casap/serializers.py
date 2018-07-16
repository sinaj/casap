from django.contrib.auth.models import User
from rest_framework import serializers

from casap.models import Profile, Volunteer, VolunteerAvailability, Vulnerable, VulnerableAddress, LostPersonRecord, \
    FindRecord


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'id')


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
            'url', 'id', 'creation_time', 'first_name', 'last_name', 'nickname', 'birthday', 'picture', 'hash',
            'creator_id',
            'sex', 'race', 'eye_colour', 'hair_colour', 'height', 'weight', 'favourite_locations'
        )


class VulnerableAddressSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = VulnerableAddress
        fields = ('url', 'id', 'vulnerable', 'address', 'address_lat', 'address_lng', 'city', 'province', 'street')


class LostPersonRecordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = LostPersonRecord
        fields = (
            'url', 'id', 'state', 'time', 'address', 'address_lat', 'address_lng', 'description', 'hash', 'reporter',
            'vulnerable', 'city', 'province', 'street', 'volunteer_list')


class FindRecordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FindRecord
        fields = (
            'url', 'id', 'lost_record', 'reporter', 'time', 'address', 'address_lat', 'address_lng', 'description',
            'hash', 'city', 'province', 'street')

from django.contrib.auth.models import User
import datetime
from rest_framework import serializers

from casap.models import *
from casap.utilities.utils import get_standard_phone, normalize_email
from casap.views.views_report import send_alert_email


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'id')


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer to create a user and profile in parallel.
    """
    username = serializers.CharField(source='user.username')
    password = serializers.CharField(source='user.password')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = Profile
        fields = ('hash', 'username', 'password', 'first_name',
                  'last_name', 'phone_number', 'id')

    def create(self, validated_data):
        x = validated_data.get('user')
        user = User.objects.create_user(username=normalize_email(x['username']),
                                        email=x['username'],
                                        password=x['password'],
                                        first_name=x['first_name'],
                                        last_name=x['last_name'],
                                        )
        profile = Profile.objects.get(user=user)
        profile.phone_number = get_standard_phone(validated_data['phone_number'])
        profile.save()
        return profile

    def update(self, instance, validated_data):
        user_data = validated_data['user']
        user = User.objects.get(username=instance.user.username)
        user.username = user_data['username']
        user.email = user_data['username']
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        user.save()

        instance.phone_number = validated_data['phone_number']
        instance.save()
        return instance


class VolunteerSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = Volunteer
        fields = ('id', 'profile', 'phone', 'email')

    def update(self, instance, validated_data):
        x = validated_data
        if x.get('phone'):
            instance.phone = x.get('phone')
        if x.get('email'):
            instance.email = x.get('email')
        instance.save()
        return instance

    def create(self, validated_data):
        _profile = self.context['request'].user.profile
        volunteer = Volunteer.objects.create(
            profile=_profile,
        )
        return volunteer


class VolunteerAvailabilitySerializer(serializers.ModelSerializer):
    volunteer = VolunteerSerializer(read_only=True)

    class Meta:
        model = VolunteerAvailability
        fields = (
            'id', 'volunteer', 'address', 'address_lat', 'address_lng', 'km_radius')

    def create(self, validated_data):
        x = validated_data
        _vol = self.context['request'].user.profile.volunteer

        availability = VolunteerAvailability.objects.create(
            volunteer=_vol,
            address=x.get('address'),
            address_lat=x.get('address_lat'),
            address_lng=x.get('address_lng'),
            km_radius=x.get('km_radius')
        )
        return availability

    def update(self, instance, validated_data):
        x = validated_data
        instance.address = x.get('address')
        instance.address_lat = x.get('address_lat')
        instance.address_lng = x.get('address_lng')
        instance.km_radius = x.get('km_radius')
        instance.save()
        return instance


class VulnerableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vulnerable
        fields = (
            'id', 'creation_time', 'first_name', 'last_name', 'nickname', 'birthday', 'picture', 'hash',
            'creator_id',
            'sex', 'race', 'eye_colour', 'hair_colour', 'height', 'weight', 'favourite_locations'
        )


class VulnerableAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VulnerableAddress
        fields = ('id', 'vulnerable', 'address', 'address_lat', 'address_lng', 'city', 'province', 'street')


class LostPersonRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LostPersonRecord
        fields = (
            'id', 'state', 'time', 'address', 'address_lat', 'address_lng', 'description', 'hash', 'reporter',
            'vulnerable', 'city', 'province', 'intersection', 'intersection_lat', 'intersection_lng', 'volunteer_list')
        depth = 1


class FindRecordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FindRecord
        fields = (
            'url', 'id', 'lost_record', 'reporter', 'time', 'address', 'address_lat', 'address_lng', 'description',
            'hash')


class EmergencyCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyCall
        fields = (
            'phone_number',
        )


class SightingRecordSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    lost_record = LostPersonRecordSerializer(read_only=True)

    class Meta:
        model = SightingRecord
        fields = (
            'id', 'lost_record', 'time', 'address', 'address_lat', 'address_lng', 'description', 'hash', 'reporter',)


class TempSightingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        lost_record = LostPersonRecordSerializer(read_only=True)

        model = TempSightingRecord
        fields = (
            'id', 'lost_record', 'address', 'address_lat', 'address_lng', 'description'
        )

    def create(self, validated_data):
        x = validated_data
        _vol = self.context['request'].user
        time = datetime.datetime.now()
        lost_record = x.get('lost_record')
        temp_sighting = TempSightingRecord.objects.create(
            lost_record=lost_record,
            reporter=_vol,
            time=time,
            address=x.get('address'),
            address_lng=x.get('address_lng'),
            address_lat=x.get('address_lat'),
            description=x.get('description')
        )

        lost_alert = Alerts(
            state='Sighted', lost_record=lost_record, seen_record=temp_sighting
        )
        lost_alert.save()

        coordinators = Profile.objects.filter(coordinator_email=True)
        for coord in coordinators:
            send_alert_email(coord, lost_alert)

        return temp_sighting

from django.contrib.auth.models import User
from rest_framework import serializers

from casap.models import Profile, Volunteer, VolunteerAvailability, Vulnerable, VulnerableAddress, LostPersonRecord, \
    FindRecord
from casap.utilities.utils import get_standard_phone, normalize_email


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'id')


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
                  'last_name','phone_number')

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
    url = serializers.HyperlinkedIdentityField(view_name="lost_person_record-detail")

    class Meta:
        model = LostPersonRecord
        fields = (
            'url', 'id', 'state', 'time', 'address', 'address_lat', 'address_lng', 'description', 'hash', 'reporter',
            'vulnerable', 'city', 'province', 'intersection', 'intersection_lat', 'intersection_lng', 'volunteer_list')
        depth = 1


class FindRecordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FindRecord
        fields = (
            'url', 'id', 'lost_record', 'reporter', 'time', 'address', 'address_lat', 'address_lng', 'description',
            'hash')

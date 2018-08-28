from django.contrib.auth.models import User
from rest_framework import viewsets, generics

import simplejson as json

from casap.models import Profile, Volunteer, VolunteerAvailability, Vulnerable, VulnerableAddress, LostPersonRecord, \
    FindRecord
from casap.serializers import UserSerializer, ProfileSerializer, VolunteerSerializer, VolunteerAvailabilitySerializer, \
    VulnerableSerializer, VulnerableAddressSerializer, LostPersonRecordSerializer, FindRecordSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = Profile.objects.all().order_by('user_id')
    serializer_class = ProfileSerializer


class VolunteerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows volunteers to be viewed or edited.
    """
    queryset = Volunteer.objects.all().order_by('id')
    serializer_class = VolunteerSerializer


class VolunteerAvailabilityViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows volunteer availabilities to be viewed or edited.
    """
    queryset = VolunteerAvailability.objects.all().order_by('id')
    serializer_class = VolunteerAvailabilitySerializer


class VulnerableViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows vulnerables to be viewed or edited.
    """
    queryset = Vulnerable.objects.all().order_by('id')
    serializer_class = VulnerableSerializer


class VulnerableAddressViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows vulnerables to be viewed or edited.
    """
    queryset = VulnerableAddress.objects.all().order_by('id')
    serializer_class = VulnerableAddressSerializer


class LostPersonRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows lost person records to be viewed or edited.
    """

    def get_queryset(self):
        json_dec = json.decoder.JSONDecoder()
        records = list()
        user = self.request.user
        profile = Profile.objects.filter(id=user.id).first()
        missing_people = LostPersonRecord.objects.filter(state="reported") | LostPersonRecord.objects.filter(
            state="sighted")
        if profile.volunteer.id:
            for i in missing_people:
                try:
                    vol_list = json_dec.decode(i.volunteer_list)
                    if int(profile.volunteer.id) in vol_list:
                        records.append(i)
                except:
                    pass

        return records

    serializer_class = LostPersonRecordSerializer


class FindRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows find person records to be viewed or edited.
    """
    queryset = FindRecord.objects.all().order_by('id')
    serializer_class = FindRecordSerializer

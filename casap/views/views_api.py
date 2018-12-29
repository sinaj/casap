from django.contrib.auth.models import User
from django.http import Http404
from rest_framework import viewsets, generics, status

import simplejson as json
from rest_framework.response import Response

from casap.models import *
from casap.serializers import *


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
    # queryset = Profile.objects.all().order_by('user_id')
    serializer_class = ProfileSerializer

    def get_queryset(self):
        queryset = Profile.objects.all()
        user = self.request.user
        profile = queryset.get(user=user)
        queryset = queryset.filter(id=profile.id).all()

        return queryset


class VolunteerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows volunteers to be viewed or edited.
    """
    # queryset = Volunteer.objects.all().order_by('id')
    serializer_class = VolunteerSerializer

    def get_queryset(self):
        queryset = Volunteer.objects.all().order_by('id')
        user = self.request.user
        try:
            vol = user.profile.volunteer
            queryset = queryset.filter(id=vol.id).all()
            return queryset
        except:
            vol = None
            return []


class VolunteerAvailabilityViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows volunteer availabilities to be viewed or edited.
    """
    serializer_class = VolunteerAvailabilitySerializer

    def get_queryset(self):
        queryset = VolunteerAvailability.objects.all().order_by('id')
        user = self.request.user
        try:
            vol = user.profile.volunteer
            queryset = queryset.filter(volunteer=vol).order_by('id')
            return queryset
        except:
            return []

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class VulnerableViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows vulnerables to be viewed or edited.
    """
    serializer_class = VulnerableSerializer

    def get_queryset(self):
        queryset = Vulnerable.objects.all().order_by('-first_name')

        if self.request.user.is_superuser:
            return queryset
        else:
            x = self.request.user.profile
            queryset = queryset.filter(creator=x).order_by('-first_name')

            return queryset


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

    serializer_class = LostPersonRecordSerializer

    def get_queryset(self):
        json_dec = json.decoder.JSONDecoder()
        records = list()
        user = self.request.user
        profile = Profile.objects.filter(id=user.id).first()
        missing_people = LostPersonRecord.objects.filter(state="reported") | LostPersonRecord.objects.filter(
            state="sighted")
        missing_people = missing_people.order_by('time')
        try:
            if profile.volunteer.id:
                for i in missing_people:
                    try:
                        vol_list = json_dec.decode(i.volunteer_list)
                        if int(profile.volunteer.id) in vol_list:
                            records.append(i)
                    except:
                        pass
        except:
            return []

        return records


class AllLostPersonRecordViewSet(viewsets.ModelViewSet):
    serializer_class = LostPersonRecordSerializer
    queryset = LostPersonRecord.objects.all().order_by('id')


class FindRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows find person records to be viewed or edited.
    """
    queryset = FindRecord.objects.all().order_by('id')
    serializer_class = FindRecordSerializer


class EmergencyCallViewSet(viewsets.ModelViewSet):
    queryset = EmergencyCall.objects.all()
    serializer_class = EmergencyCallSerializer


class SightingRecordViewSet(viewsets.ModelViewSet):
    queryset = SightingRecord.objects.all()
    serializer_class = SightingRecordSerializer

    def get_queryset(self):
        _lost_id = self.request.query_params.get('lost')
        lost = LostPersonRecord.objects.all().filter(id=int(_lost_id)).first()
        sighting = lost.get_sighting_records()
        if sighting:
            return sighting
        else:
            return []


class TempSightingRecordViewSet(viewsets.ModelViewSet):
    queryset = TempSightingRecord.objects.all()
    serializer_class = TempSightingRecordSerializer

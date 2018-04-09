from django.contrib.auth.models import User
from rest_framework import viewsets

from casap.models import Profile, Volunteer, VolunteerAvailability, Vulnerable
from casap.serializers import UserSerializer, ProfileSerializer, VolunteerSerializer, VolunteerAvailabilitySerializer, \
    VulnerableSerializer


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

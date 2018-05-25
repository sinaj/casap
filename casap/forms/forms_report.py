import pytz
from django import forms

from casap.models import *
from casap.utilities.utils import get_address_map_google


class LostPersonRecordForm(forms.ModelForm):
    time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M'])
    address = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                            'placeholder': "Press here to find address",
                                                            'class': 'form-control geocomplete'}))

    def clean_time(self):
        return pytz.timezone(self.data['tz_name']).localize(self.cleaned_data['time'].replace(tzinfo=None))

    def clean_address(self):
        if not self.cleaned_data['address']:
            raise forms.ValidationError("Address not provided")
        address = self.cleaned_data['address']
        map_response = get_address_map_google(address)
        for i in range(10):
            if map_response is None:
                map_response = get_address_map_google(address)
            else:
                break
        if map_response is None:
            raise forms.ValidationError("Address is invalid")
        self.address_lat = map_response['lat']
        self.address_lng = map_response['lng']
        self.address = address
        return self.cleaned_data['address']

    def save(self, reporter, vulnerable, commit=True):
        instance = super(self.__class__, self).save(commit=False)
        instance.reporter = reporter
        instance.vulnerable = vulnerable
        instance.state = "reported"
        instance.address_lat = self.address_lat
        instance.address_lng = self.address_lng
        instance.address = self.address

        if commit:
            instance.save()
        return instance

    class Meta:
        model = LostPersonRecord
        fields = ('time', 'address', 'description')
        exclude = ('address_lng', 'address_lat')


class SightingRecordForm(forms.ModelForm):
    address = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                            'placeholder': "Press here to find address",
                                                            'class': 'form-control geocomplete'}))
    time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M'])

    def clean_address(self):
        # if not self.cleaned_data['address']:
        #     return self.cleaned_data['address']
        address = self.cleaned_data['address']

        map_response = get_address_map_google(address)

        for i in range(10):
            if map_response is None:
                map_response = get_address_map_google(address)
            else:
                break

        if map_response is None:
            raise forms.ValidationError("Address is invalid")
        self.address_lat = map_response['lat']
        self.address_lng = map_response['lng']
        return address

    def clean_time(self):
        return pytz.timezone(self.data['tz_name']).localize(self.cleaned_data['time'].replace(tzinfo=None))

    def save(self, reporter, lost_record, commit=True):
        instance = super(self.__class__, self).save(commit=False)
        instance.reporter = reporter
        instance.lost_record = lost_record
        instance.state = "reported"
        instance.address_lat = self.address_lat
        instance.address_lng = self.address_lng
        if commit:
            instance.save()
        return instance

    class Meta:
        model = TempSightingRecord
        fields = ('address', 'time', 'description')


class SightingActivityForm(forms.ModelForm):
    def save(self, reporter, lost_record, commit=True):
        instance = super(self.__class__, self).save(commit=False)
        instance.reporter = reporter
        instance.lost_record = lost_record
        if commit:
            instance.save()
        return instance


class FindRecordForm(forms.ModelForm):
    time = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M'])
    address = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                            'placeholder': "Press here to find address",
                                                            'class': 'form-control geocomplete'}))

    def clean_time(self):
        return pytz.timezone(self.data['tz_name']).localize(self.cleaned_data['time'].replace(tzinfo=None))

    def clean_address(self):
        if not self.cleaned_data['address']:
            raise forms.ValidationError("Address not provided")
        address = self.cleaned_data['address']
        map_response = get_address_map_google(address)
        for i in range(10):
            if map_response is None:
                map_response = get_address_map_google(address)
            else:
                break
        if map_response is None:
            raise forms.ValidationError("Address is invalid")
        self.address_lat = map_response['lat']
        self.address_lng = map_response['lng']
        self.address = address
        return self.cleaned_data['address']

    def save(self, reporter, lost_record, commit=True):
        instance = super(self.__class__, self).save(commit=False)
        instance.reporter = reporter
        instance.lost_record = lost_record
        instance.state = "reported"
        instance.address_lat = self.address_lat
        instance.address_lng = self.address_lng
        instance.address = self.address
        if commit:
            instance.save()
        return instance

    class Meta:
        model = FindRecord
        fields = ('time', 'address', 'description')
        exclude = ('address_lng', 'address_lat')

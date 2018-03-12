from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.forms.models import BaseInlineFormSet
from django.core.validators import validate_email
from django.forms import TimeField

from casap.models import *
from casap.utilities.utils import normalize_email, get_standard_phone, get_address_map_google, validate_twitter_handle


class UserLoginForm(forms.Form):
    email = forms.CharField(widget=forms.EmailInput(attrs=dict(required=True, max_length=30)), label="Email address")
    password = forms.CharField(widget=forms.PasswordInput(attrs=dict(required=True, max_length=30, render_value=False)),
                               label="Password")

    class Meta:
        fields = ['email', 'password']

    def clean(self):
        try:
            email = normalize_email(self.cleaned_data['email'])
            User.objects.get(username__iexact=email)  # Check if user with email exists
            user = authenticate(username=email, password=self.cleaned_data['password'])
            if user is not None:
                if not user.is_authenticated():
                    raise forms.ValidationError("The user with email and password could not be found.")
            else:
                raise forms.ValidationError("The user with email and password could not be found.")
        except User.DoesNotExist:
            raise forms.ValidationError("The user with email and password could not be found.")
        return self.cleaned_data


class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2',)


class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username')


class ManageNotificationsForm(forms.ModelForm):
    phone_notify = forms.BooleanField()
    email_notify = forms.BooleanField()
    twitter_dm_notify = forms.BooleanField()
    twitter_public_notify = forms.BooleanField()

    class Meta:
        model = Notifications
        fields = ('phone_notify', 'email_notify', 'twitter_dm_notify', 'twitter_public_notify')


class VolunteerAvailabilityForm(forms.ModelForm):
    street = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                           'placeholder': "e.g. 15 Bermuda Rd NW",
                                                           'class': 'form-control'}))
    city = forms.CharField(widget=forms.TextInput(attrs={'size': '20',
                                                         'placeholder': "e.g. Calgary",
                                                         'class': 'form-control'
                                                         }))

    class Meta:
        model = VolunteerAvailability
        fields = ['street', 'city', 'province', 'km_radius']
        exclude = ('address_lat', 'address_lng', 'address')

    def clean_personal_address(self):
        if not self.cleaned_data['address']:
            return self.cleaned_data['address']

        address = self.cleaned_data['address']
        map_response = get_address_map_google(address)
        if map_response is None:
            raise forms.ValidationError("Address is invalid")
        else:
            self.lat = map_response['lat']
            self.lng = map_response['lng']
        return address


class VolunteerForm(forms.ModelForm):

    def clean_phone(self):
        if self.cleaned_data.get('phone'):
            standard_phone = get_standard_phone(self.cleaned_data['phone'])
            if standard_phone:
                return standard_phone
            raise forms.ValidationError("Phone number is invalid.")

    def clean_email(self):
        if self.cleaned_data.get('email'):
            try:
                validate_email(self.cleaned_data['email'])
            except:
                raise forms.ValidationError("Email is invalid.")
            else:
                return self.cleaned_data['email']

    def clean_twitter_handle(self):
        if self.cleaned_data.get('twitter_handle'):
            try:
                validate_twitter_handle(self.cleaned_data.get('twitter_handle'))
                return self.cleaned_data['twitter_handle']
            except:
                raise forms.ValidationError("Twitter handle does not exist.")

    class Meta:
        model = Volunteer
        fields = ('phone', 'email', 'twitter_handle')


class VulnerableForm(forms.ModelForm):
    class Meta:
        model = Vulnerable
        fields = ('first_name', 'last_name', 'description', 'birthday', 'picture')


# class VulnerableAddressFormSet(BaseInlineFormSet):
#     def clean(self):
#         super(VulnerableAddressFormSet, self).clean()
#         for form in self.forms:
#             address = form.cleaned_data.get('address')
#             if not address:
#                 continue
#             map_response = get_address_map_google(address)
#             if map_response is None:
#                 form.add_error("address", forms.ValidationError("Address is invalid"))
#             else:
#                 form.address_lat = map_response['lat']
#                 form.address_lng = map_response['lng']
#
#     def save(self, commit=True):
#         instances = super(VulnerableAddressFormSet, self).save(commit=False)
#         for form in self.saved_forms:
#             instance = form.instance
#             if hasattr(form, "address_lat") and hasattr(form, "address_lng"):
#                 instance.address_lat = form.address_lat
#                 instance.address_lng = form.address_lng
#         if commit:
#             for form in self.saved_forms:
#                 form.save()
#         return instances

class VulnerableAddressForm(forms.ModelForm):
    street = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                           'placeholder': "e.g. 15 Bermuda Rd NW",
                                                           'class': 'form-control'}))
    city = forms.CharField(widget=forms.TextInput(attrs={'size': '20',
                                                         'placeholder': "e.g. Calgary",
                                                         'class': 'form-control'
                                                         }))

    def clean_street(self):
        if not self.cleaned_data['street']:
            raise forms.ValidationError("Street not provided")
        return self.cleaned_data['street']

    def clean_city(self):
        if not self.cleaned_data['city']:
            raise forms.ValidationError("City not provided")
        return self.cleaned_data['city']

    def clean_province(self):
        if not self.cleaned_data['province']:
            raise forms.ValidationError("Province not provided")
        address = self.cleaned_data['street'] + " " + self.cleaned_data['city'] + " " + self.cleaned_data['province']
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
        return self.cleaned_data['province']

    class Meta:
        model = VulnerableAddress
        fields = ('street', 'city', 'province')
        exclude = ('address', 'address_lng', 'address_lat')

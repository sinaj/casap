from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email

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
    address = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                            'placeholder': "Press here to find address",
                                                            'class': 'form-control geocomplete'}))

    class Meta:
        model = VolunteerAvailability
        fields = ['address', 'km_radius']
        exclude = ('address_lat', 'address_lng')

    def clean_address(self):
        if not self.cleaned_data['address']:
            return self.cleaned_data['address']

        address = self.cleaned_data['address']
        map_response = get_address_map_google(address)
        if map_response is None:
            for i in range(10):
                map_response = get_address_map_google(address)
                if map_response:
                    break
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
    picture = forms.FileField(widget=forms.ClearableFileInput())

    class Meta:
        model = Vulnerable
        fields = (
            'first_name', 'last_name', 'nickname', 'birthday', 'picture', 'sex', 'race', 'hair_colour', 'height',
            'weight', 'eye_colour', 'favourite_locations', 'transportation')


class VulnerableReportForm(forms.ModelForm):
    class Meta:
        model = Vulnerable
        fields = (
            'nickname', 'sex', 'race', 'hair_colour', 'height',
            'weight', 'eye_colour', 'favourite_locations')


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
    address = forms.CharField(widget=forms.TextInput(attrs={'size': '30',
                                                            'placeholder': "Press here to add address",
                                                            'class': 'form-control geocomplete'}))

    def clean_address(self):
        if not self.cleaned_data['address']:
            raise forms.ValidationError("Address not provided")
        add = self.cleaned_data['address']
        map_response = get_address_map_google(add)
        for i in range(10):
            if map_response is None:
                map_response = get_address_map_google(add)
            else:
                break
        if map_response is None:
            raise forms.ValidationError("Address is invalid")
        self.address_lat = map_response['lat']
        self.address_lng = map_response['lng']
        self.address = add
        return self.cleaned_data['address']

    class Meta:
        model = VulnerableAddress
        fields = ('address',)
        exclude = ('address_lng', 'address_lat')


class EmergencyCallForm(forms.ModelForm):

    def clean_phone_number(self):
        if self.cleaned_data.get('phone_number'):
            standard_phone = get_standard_phone(self.cleaned_data['phone_number'])
            if standard_phone:
                return standard_phone
            raise forms.ValidationError("Phone number is invalid.")

    class Meta:
        model = EmergencyCall
        fields = ('phone_number',)
        exclude = ('hash',)

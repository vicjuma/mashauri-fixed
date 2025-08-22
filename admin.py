from django.contrib import admin
from .models import User, Dispatch, Ticket, SLA, Comment
from django.contrib.auth.models import Group
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

admin.site.unregister(Group)


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ["email",]

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ["email", "password", "is_active"]

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.fields['verb'].empty_label = None


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'first_name', 'last_name'),
        }),
        ('Permissions', {
            'fields': ('is_superuser', 'is_staff', 'is_active'),
        }),
        ('Role', {
            'fields': ('role', 'msp_category', 'rp_category'),
        }),
    )

    exclude = ["groups", "user_permissions"]


class DispatchAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Building Information', {
            'fields': ('site_fdt_cluster_link_name', 'lepton_project_name'),
        }),
        ('Service Provider', {
            'fields': ('msp', 'rp', 'ec'),
        }),
        ('Escalation', {
            'fields': ('project_type', 'site_fdt_location', 'interception_location'),
        }),
        ('Images', {
            'fields': ('fdd_image', 'hld_image'),
        }),
    )

    exclude = ["comments"]


class TicketAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Ticket Information', {
            'fields': ('dispatch', 'assigned_to', 'status'),
        }),
    )


class SLAAdmin(admin.ModelAdmin):
    fieldsets = (
        ('SLA Information', {
            'fields': ('dispatch', 'start_time', 'end_time'),
        }),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Dispatch, DispatchAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(SLA, SLAAdmin)
admin.site.register(Comment)

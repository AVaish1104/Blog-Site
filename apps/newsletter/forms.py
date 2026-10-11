from django import forms

from .services import consent_text


class SubscribeForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
    )
    consent = forms.BooleanField(
        required=True,
        error_messages={"required": "Please confirm you'd like to receive our emails."},
    )
    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )
    source = forms.CharField(required=False, max_length=50, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "newsletter-%s")  # unique ids alongside other forms
        super().__init__(*args, **kwargs)
        self.fields["consent"].label = consent_text()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Your subscription couldn't be accepted.", code="honeypot")
        return cleaned

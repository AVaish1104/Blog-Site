import time

from django import forms
from django.core import signing

from .models import Comment

MIN_SECONDS_TO_SUBMIT = 3
MAX_FORM_AGE_SECONDS = 60 * 60 * 24
MAX_LINKS = 3
_SALT = "comments.form-issued"


def issue_token(post_pk, now=None):
    return signing.dumps({"post": post_pk, "t": int(now or time.time())}, salt=_SALT)


class CommentForm(forms.ModelForm):
    """
    Spam defences: a hidden honeypot field humans never fill in, and a signed
    timestamp that rejects forms submitted implausibly fast or long after loading.
    """

    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )
    issued = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Comment
        fields = ["author_name", "author_email", "body"]
        labels = {"author_name": "Name", "author_email": "Email", "body": "Comment"}
        widgets = {
            "author_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "author_email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "body": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, post=None, **kwargs):
        self.post = post
        super().__init__(*args, **kwargs)

    @classmethod
    def for_post(cls, post):
        return cls(post=post, initial={"issued": issue_token(post.pk)})

    def clean_author_name(self):
        name = " ".join(self.cleaned_data["author_name"].split())
        if len(name) < 2:
            raise forms.ValidationError("Please enter your name.")
        return name

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError("Please write a comment.")
        if body.lower().count("http") > MAX_LINKS:
            raise forms.ValidationError(f"Comments may include at most {MAX_LINKS} links.")
        return body

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Your comment couldn't be accepted.", code="honeypot")
        try:
            payload = signing.loads(
                cleaned.get("issued", ""), salt=_SALT, max_age=MAX_FORM_AGE_SECONDS
            )
        except signing.BadSignature:
            raise forms.ValidationError(
                "This form has expired. Please reload the page and try again.", code="expired"
            ) from None
        if self.post is not None and payload.get("post") != self.post.pk:
            raise forms.ValidationError("Your comment couldn't be accepted.", code="mismatch")
        age = time.time() - payload.get("t", 0)
        if age > MAX_FORM_AGE_SECONDS:
            raise forms.ValidationError(
                "This form has expired. Please reload the page and try again.", code="expired"
            )
        if age < MIN_SECONDS_TO_SUBMIT:
            raise forms.ValidationError(
                "That was quick! Please wait a moment and submit again.", code="too_fast"
            )
        return cleaned

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.blog.models import Author, Category, Post, Tag, slug_validator
from apps.blog.services import MAX_TAGS_PER_POST, make_slug, parse_tag_names, unique_slug
from apps.images.models import Image
from apps.images.services import ACCEPT_ATTR, process_upload


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%dT%H:%M", **kwargs)


class ImageChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.alt_text[:60]} ({obj.width}×{obj.height})"


class PostForm(forms.ModelForm):
    slug = forms.CharField(
        required=False,
        max_length=200,
        help_text="The address of the article: /posts/your-slug/. Leave blank to create one "
        "from the title.",
    )
    tags = forms.CharField(
        required=False,
        max_length=800,
        help_text="Separate tags with commas. New tags are created automatically.",
        widget=forms.TextInput(attrs={"list": "tag-suggestions", "autocomplete": "off"}),
    )
    cover_image = ImageChoiceField(
        queryset=Image.objects.all(),
        required=False,
        empty_label="No cover image",
        label="Cover image",
        help_text="Choose an uploaded image, or upload a new one below.",
    )
    new_cover = forms.FileField(
        required=False,
        label="Upload a new cover",
        help_text="JPEG, PNG or WebP, up to 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ACCEPT_ATTR}),
    )
    new_cover_alt = forms.CharField(
        required=False,
        max_length=250,
        label="Alt text for the new cover",
        help_text="Describe the image for people who can't see it.",
    )
    status = forms.ChoiceField(
        choices=Post.Status.choices,
        widget=forms.RadioSelect,
        label="Status",
    )
    published_at = forms.DateTimeField(
        required=False,
        label="Publication date",
        widget=DateTimeLocalInput(),
        help_text="Leave blank to use the moment you publish. A future date schedules the post.",
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "slug",
            "excerpt",
            "body",
            "author",
            "category",
            "cover_image",
            "status",
            "published_at",
            "featured",
            "allow_comments",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-title", "autocomplete": "off"}),
            "excerpt": forms.Textarea(attrs={"rows": 3, "maxlength": 400}),
            "body": forms.Textarea(attrs={"rows": 24, "class": "input-body", "spellcheck": "true"}),
            "seo_title": forms.TextInput(attrs={"maxlength": 70}),
            "seo_description": forms.Textarea(attrs={"rows": 2, "maxlength": 200}),
        }
        error_messages = {
            "title": {"required": "Every post needs a title."},
            "author": {"required": "Choose an author for this post."},
        }
        help_texts = {
            "excerpt": "Shown in listings, feeds and search results. Up to 400 characters.",
            "body": "Write in Markdown. Use ## for headings, **bold**, *italic*, > for quotes.",
            "seo_title": "Optional. Overrides the title in search results (70 characters max).",
            "seo_description": "Optional. Overrides the excerpt in search results.",
            "featured": "Show this post as the lead story on the home page.",
            "allow_comments": "Readers can submit comments (each is reviewed before it appears).",
        }

    def __init__(self, *args, preview=False, **kwargs):
        self.preview = preview
        self.processed_cover = None
        super().__init__(*args, **kwargs)
        self.fields["author"].queryset = Author.objects.order_by("name")
        self.fields["author"].empty_label = "Choose an author"
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "No topic"
        self.fields["category"].label = "Topic"
        if self.instance.pk:
            self.initial.setdefault(
                "tags", ", ".join(self.instance.tags.values_list("name", flat=True))
            )
        self.previous_slug = self.instance.slug if self.instance.pk else None

    def clean_title(self):
        title = " ".join(self.cleaned_data["title"].split())
        if not title:
            raise ValidationError("Every post needs a title.")
        return title

    def validate_unique(self):
        if not self.preview:
            super().validate_unique()

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip().lower()
        if not slug:
            return ""
        slug_validator(slug)
        if not self.preview:
            clash = Post.objects.filter(slug=slug).exclude(pk=self.instance.pk).first()
            if clash:
                raise ValidationError(f"This slug is already used by “{clash.title}”.")
        return slug

    def clean_tags(self):
        names = parse_tag_names(self.cleaned_data.get("tags"))
        if len(names) > MAX_TAGS_PER_POST:
            raise ValidationError(f"Use at most {MAX_TAGS_PER_POST} tags.")
        return names

    def clean_new_cover(self):
        upload = self.cleaned_data.get("new_cover")
        if upload and not self.preview:
            self.processed_cover = process_upload(upload)
            upload.seek(0)
        return upload

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new_cover") and not (cleaned.get("new_cover_alt") or "").strip():
            self.add_error("new_cover_alt", "Add alt text for the new cover image.")
        if (
            cleaned.get("status") == Post.Status.PUBLISHED
            and not (cleaned.get("body") or "").strip()
        ):
            self.add_error("body", "A post needs body text before it can be published.")
        if not self.preview and "title" in cleaned and not cleaned.get("slug"):
            cleaned["slug"] = unique_slug(cleaned["title"], exclude_pk=self.instance.pk)
        return cleaned

    def save(self, commit=True):
        post = super().save(commit=False)
        post.slug = self.cleaned_data.get("slug") or make_slug(post.title)
        if commit:
            post.save()
        return post


class ImageUploadForm(forms.Form):
    file = forms.FileField(
        label="Image file",
        help_text="JPEG, PNG or WebP, up to 5 MB. Large images are resized to 2400 px.",
        widget=forms.ClearableFileInput(attrs={"accept": ACCEPT_ATTR}),
    )
    alt_text = forms.CharField(
        label="Alt text",
        max_length=250,
        help_text="Describe the image for people who can't see it.",
    )

    def clean_file(self):
        upload = self.cleaned_data["file"]
        # Validates and re-encodes; raises ValidationError with a clear message.
        self.processed = process_upload(upload)
        upload.seek(0)
        return upload


class ImageEditForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ["alt_text"]


class CategoryForm(forms.ModelForm):
    slug = forms.CharField(required=False, max_length=100, help_text="Leave blank to generate.")

    class Meta:
        model = Category
        fields = ["name", "slug", "description", "position"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        clash = Category.objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise ValidationError("A topic with this name already exists.")
        return name

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip().lower()
        if slug:
            slug_validator(slug)
            if Category.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
                raise ValidationError("This slug is already in use.")
        return slug

    def save(self, commit=True):
        category = super().save(commit=False)
        if not category.slug:
            category.slug = unique_slug(
                category.name, model=Category, exclude_pk=category.pk, max_length=100
            )
        if commit:
            category.save()
        return category


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if Tag.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A tag with this name already exists.")
        return name

    def clean_slug(self):
        slug = self.cleaned_data["slug"].strip().lower()
        slug_validator(slug)
        if Tag.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This slug is already in use.")
        return slug


class AuthorForm(forms.ModelForm):
    website = forms.URLField(required=False, assume_scheme="https", label="Website")
    slug = forms.CharField(required=False, max_length=140, help_text="Leave blank to generate.")
    avatar = ImageChoiceField(
        queryset=Image.objects.all(), required=False, empty_label="No portrait"
    )

    class Meta:
        model = Author
        fields = ["name", "slug", "bio", "website", "avatar", "user"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}
        labels = {"user": "Linked sign-in account", "avatar": "Portrait"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].empty_label = "None"

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip().lower()
        if slug:
            slug_validator(slug)
            if Author.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
                raise ValidationError("This slug is already in use.")
        return slug

    def save(self, commit=True):
        author = super().save(commit=False)
        if not author.slug:
            author.slug = unique_slug(
                author.name, model=Author, exclude_pk=author.pk, max_length=140
            )
        if commit:
            author.save()
        return author


def now_local_input():
    return timezone.localtime().strftime("%Y-%m-%dT%H:%M")

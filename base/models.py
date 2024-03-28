from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db import models
import uuid


MAX_VIDEO_TITLE_LENGTH = 200
MAX_VIDEO_DESCRIPTION_LENGTH = 2000

def validate_webp_format(value):
    if not value.name.lower().endswith('.webp'):
        raise ValidationError('Thumbnail must be in .webp format')



def validate_video_size(value):
    if value.size > 20 * 1024 * 1024:  # 20 MB in bytes
        raise ValidationError("Maximum video size allowed is 20 MB.")


class ProcessedVideo(models.Model):
    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video_title = models.CharField(max_length=MAX_VIDEO_TITLE_LENGTH, unique=True)
    video_description = models.CharField(max_length=MAX_VIDEO_DESCRIPTION_LENGTH)
    video_file = models.FileField(
        upload_to="processed_videos/",
        validators=[
            FileExtensionValidator(allowed_extensions=["mp4"]),
            validate_video_size,
        ],
    )
    thumbnail_file = models.FileField(upload_to='thumbnails/', validators=[validate_webp_format])


    def __str__(self):
        return self.video_title

from django.db import models


class ImageInfo(models.Model):
    id = models.BigAutoField(primary_key=True)
    document_name = models.CharField(max_length=300, db_index=True, verbose_name='document name')
    image_path = models.CharField(max_length=300, db_index=True, verbose_name='image path')
    context_text = models.CharField(db_index=True, verbose_name='context text')
    image_description = models.CharField(db_index=True, verbose_name='image description')

    class Meta:
        db_table = 'image_info'
        indexes = [
            models.Index(fields=['document_name'], name='document_name'),
        ]

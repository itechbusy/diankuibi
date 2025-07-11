from django.db import models


class FileResult(models.Model):
    id = models.BigAutoField(primary_key=True)
    file_name = models.CharField(max_length=300, db_index=True, verbose_name='file name')
    file_path = models.CharField(max_length=200, db_index=True, verbose_name='file path')
    file_suffix = models.CharField(max_length=200, db_index=True, verbose_name='file suffix')
    file_type = models.IntegerField(db_index=True, verbose_name='file type')

    class Meta:
        db_table = 'file_result'
        indexes = [
            models.Index(fields=['file_name'], name='file_result_name_index'),
        ]

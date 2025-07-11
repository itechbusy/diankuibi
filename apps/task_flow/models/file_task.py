from django.db import models


class FileTask(models.Model):
    id = models.BigAutoField(primary_key=True)
    original_file_name = models.CharField(max_length=300, db_index=True, verbose_name='original file name')
    new_file_name = models.CharField(max_length=300, db_index=True, verbose_name='new file name')
    file_path = models.CharField(max_length=200, db_index=True, verbose_name='file path')
    file_suffix = models.CharField(max_length=200, db_index=True, verbose_name='file suffix')
    file_status = models.IntegerField(db_index=True, verbose_name='file status', default=0)

    class Meta:
        db_table = 'file_task'
        indexes = [
            models.Index(fields=['new_file_name'], name='file_name_index'),
        ]

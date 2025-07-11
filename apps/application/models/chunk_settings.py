from asgiref.sync import sync_to_async
from common.action_result import ActionResult
from django.db import models


class ChunkSettings(models.Model):
    id = models.BigAutoField(primary_key=True)
    enabled_content_extraction = models.BooleanField(default=True, verbose_name='Enable context extraction.')
    content_start_separator = models.CharField(max_length=255, default='<quick_question>',
                                               verbose_name='Content start separator.')
    content_end_separator = models.CharField(max_length=255, default='</quick_question>',
                                             verbose_name='Content end separator.')
    default_document_separator = models.CharField(max_length=255, default='~www.itechbusy.com~',
                                                  verbose_name='Default document separator, Reserved field, not yet enabled.')
    enabled_same_level_segmentation = models.BooleanField(default=True,
                                                          verbose_name='Enable title segmentation at the same level.')
    enabled_markdown_combine = models.BooleanField(default=True,
                                                   verbose_name='Enable merging the output files into the same markdown.')
    enabled_markdown_split = models.BooleanField(default=True,
                                                 verbose_name='Enable the split of the merged markdown into word.')
    enabled_title_compensation = models.BooleanField(default=True, verbose_name='Enable title compensation.')
    enabled_tag_reasoning = models.BooleanField(default=True, verbose_name='Enable tag compensation.')
    enabled_picture_reasoning = models.BooleanField(default=True, verbose_name='Enable picture reason.')
    picture_reasoning_model_id = models.BigIntegerField(default=0,
                                                        verbose_name='A model for image reasoning is used when extracting the meaning of images in documents.')
    title_reasoning_model_id = models.BigIntegerField(default=0,
                                                      verbose_name='A model used to extract titles from articles.')
    tag_reasoning_model_id = models.BigIntegerField(default=0,
                                                    verbose_name='A model used to extract tags from articles.')
    picture_reasoning_prompt = models.TextField(
        verbose_name='When performing image reasoning, use the prompt words built into the system when they are empty.')
    title_hierarchy_reasoning_prompt = models.TextField(
        verbose_name='When performing title hierarchy reasoning, use the prompt words built into the system when they are empty.')
    tag_reasoning_prompt = models.TextField(
        verbose_name='When performing tag reasoning, use the prompt words built into the system when they are empty.')

    class Meta:
        db_table = 'chunk_settings'


async def get_chunk_settings():
    @sync_to_async
    def select():
        settings = ChunkSettings.objects.filter(id=1).first()
        if settings is None:
            ChunkSettings.objects.create(id=1)
            settings = ChunkSettings.objects.filter(id=1).first()
        return settings

    return await select()


def update_chunk_settings(data):
    filtered_data = {k: v for k, v in data.items() if v is not None}
    ChunkSettings.objects.filter(id=1).update(**filtered_data)
    return ActionResult.success()

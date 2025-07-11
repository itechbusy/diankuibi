import logging

from asgiref.sync import sync_to_async
from common.action_result import ActionResult
from django.db import models, IntegrityError

logging = logging.getLogger("model settings")


class ModelSettings(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='The name presented to the user')
    model_name = models.CharField(max_length=100, unique=True, verbose_name='The name of the model')
    api_key = models.CharField(max_length=200, db_index=True, verbose_name='Model API Key')
    base_url = models.CharField(max_length=500, db_index=True, verbose_name='Model API Base URL')
    temperature = models.FloatField(default=0.7,
                                    verbose_name='Call the temperature of the model, which defaults to 0.7')
    enable = models.BooleanField(default=False, verbose_name='Enable this model')
    default_model = models.BooleanField(default=False, verbose_name='Default use this model')
    model_type = models.IntegerField(default=0, verbose_name='The model type. 0 LLM model, 1 Multimodal model')
    timeout = models.IntegerField(default=30, verbose_name='Model call timeout, default 30')
    max_retries = models.IntegerField(default=3, verbose_name='Model max retries , default 3')

    class Meta:
        db_table = 'model_settings'


def list_models(model_type, enable_model=True):
    if not model_type:
        return ModelSettings.objects.all()
    return ModelSettings.objects.filter(model_type=model_type, enable=enable_model)


async def get_model(model_name=None):
    @sync_to_async
    def select(m_name):
        return ModelSettings.objects.filter(model_name=m_name, enable=True).first()

    return await select(model_name)


async def get_default_model(model_type):
    @sync_to_async
    def select(m_type):
        return ModelSettings.objects.filter(model_type=m_type, default_model=True, enable=True).first()

    return await select(model_type)


async def get_model_byid(model_id):
    @sync_to_async
    def select(m_id):
        return ModelSettings.objects.filter(id=m_id, enable=True).first()

    return await select(model_id)


def create_model(name, model_name, api_key, base_url, enable, default_model,
                 model_type, temperature=0.7, timeout=30, max_retries=3):
    if not api_key:
        return ActionResult.fail("No apiKey provided")
    if not base_url:
        return ActionResult.fail("No baseUrl provided")
    old_default_model = None
    if default_model:
        old_default_model = ModelSettings.objects.filter(model_type=model_type, default_model=True).first()

    try:
        ModelSettings.objects.create(
            name=name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            enable=enable,
            default_model=default_model,
            model_type=model_type,
            timeout=timeout,
            max_retries=max_retries,
            model_name=model_name
        )
    except IntegrityError:
        logging.error("The model name cannot be repeated.")
        return ActionResult.fail(1, "The model name cannot be repeated.")
    if old_default_model is not None:
        ModelSettings.objects.filter(id=old_default_model.id).update(default_model=False)
    return ActionResult.success()


def update_model(data):
    model_id = data.get("id")
    if model_id is None: return ActionResult.fail("The ID cannot be empty.")
    org_data = ModelSettings.objects.filter(id=data.get("id")).first()
    if org_data is None:
        logging.error(f"The data whose id is {model_id} does not exist")
        return ActionResult.fail(1, f"The data whose id is {model_id} does not exist")

    old_default_model = None
    if data.get("default_model"):
        old_default_model = ModelSettings.objects.filter(model_type=org_data.model_type, default_model=True).first()

    filtered_data = {k: v for k, v in data.items() if v is not None}
    try:
        ModelSettings.objects.filter(id=model_id).update(**filtered_data)
    except IntegrityError:
        logging.error("The model name cannot be repeated.")
        return ActionResult.fail(1, "The model name cannot be repeated.")

    if old_default_model is not None:
        if old_default_model.id != model_id:
            ModelSettings.objects.filter(id=old_default_model.id).update(default_model=False)
    return ActionResult.success()


def delete_model(model_id):
    ModelSettings.objects.filter(id=model_id).delete()

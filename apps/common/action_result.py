import json

from django.core.paginator import Page
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model, QuerySet
from django.forms.models import model_to_dict
from django.http import JsonResponse
from rest_framework import status


class ActionResultCode:
    # This operation was successful
    SUCCESS = 200
    # This operation failed
    FAIL = 1
    # Missing required parameters
    BAD_REQUEST = 400
    # Server error
    SERVER_ERROR = 500


class ActionResult(JsonResponse):
    """
    Generic return results, all results are structured into a fixed format of JSON, including pagination information returns
    """
    __slots__ = [
        'data', 'code', 'message', 'total',
        'current_page', 'page_size'
    ]

    def __init__(self, data=None, code=ActionResultCode.SUCCESS, message: str = 'success', total: int = None,
                 current_page: int = None, page_size: int = None, **kwargs):

        processed_data = deep_serialize(data) if data is not None else None

        self.data = processed_data
        self.code = code
        self.message = message
        self.total = total
        self.current_page = current_page
        self.page_size = page_size

        response_data = {
            "code": code,
            'message': message,
            "data": processed_data
        }

        if total is not None:
            response_data['total'] = total
            response_data['current_page'] = current_page
            response_data['page_size'] = page_size

        super().__init__(
            data=response_data,
            encoder=DjangoJSONEncoder,
            safe=False,
            status=status.HTTP_200_OK,
            json_dumps_params={'ensure_ascii': False},
            **kwargs
        )

    @staticmethod
    def success(data=None, code=ActionResultCode.SUCCESS, message='success'):
        """
        Return result upon successful quick build.
        """
        if isinstance(data, Page):
            return ActionResult(code=ActionResultCode.SUCCESS, total=data.paginator.count,
                                data=data.object_list,
                                current_page=data.number,
                                page_size=data.paginator.per_page)
        else:
            return ActionResult(code=code, message=message, data=data)

    @staticmethod
    def fail(code=ActionResultCode.FAIL, message='fail'):
        """
        Return the results after a failed quick build.
        """
        return ActionResult(code=code, message=message, data=None)

    def __str__(self):
        return (f'ActionResult:"code": {self.code},"message": {self.message},"total": {self.total},'
                f'"current_page": {self.current_page},"page_size": {self.page_size},"data": {self.data}')


def deep_serialize(obj):
    if isinstance(obj, QuerySet):
        obj = list(obj.values())

    if isinstance(obj, Model):
        obj = model_to_dict(obj)

    if isinstance(obj, list):
        return [deep_serialize(item) for item in obj]

    if isinstance(obj, dict):
        return {k: deep_serialize(v) for k, v in obj.items()}

    if isinstance(obj, (str, int, bool, float, type(None))):
        return obj

    return json.loads(json.dumps(obj, cls=DjangoJSONEncoder))

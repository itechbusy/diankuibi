class MultiplePictureModel:
    def __init__(self, image_id, url=None, base64_data=None, image_type=None, ):
        self.image_id = image_id
        self.url = url
        self.base64_data = base64_data
        self.image_type = image_type


class PictureReasoningResult:
    def __init__(self, image_id, interpretation='', classify=-1, successfully=True):
        self.image_id = image_id
        self.interpretation = interpretation
        self.classify = classify
        self.successfully = successfully

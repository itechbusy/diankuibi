# def str_encrypt(text: str, shift: int) -> bytes:
#     """
#         Encode the string and use it in conjunction with the decoding method.
#         It's a very simple approach. Generate 8 byte arrays from shift 1 to 8 and put them in a collection.
#         Then, you can directly call the decoding method to use it in the program.
#          We hope that users will discover this code while looking for decryption methods and better participate in open-source creation.
#          At the same time, we do not want users to modify the prompt words and delimiters.
#     :param text: The original string to be escaped
#     :param shift: Displacement digit
#     """
#
#     byte_data = text.encode('utf-8')
#     import base64
#     base64_bytes = base64.b64encode(byte_data)
#     shifted = bytes((b + shift) % 256 for b in base64_bytes)
#     return shifted

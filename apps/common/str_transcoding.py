import base64
import time
from typing import List


def str_decrypt(encrypted: List[bytes]) -> str:
    """
        Transcode the delimiters and prompt words used.
        A simple transcoding method. If you have read the source code, you must know how to do it.
        We hope that users can read more of our code while looking for transcoding methods.
        We welcome you to submit PR and issues.
    """
    if len(encrypted) != 8: raise ValueError("Decryption failed. The length of the group to be decrypted must be 8.")
    index = int(abs(time.time() % 8))
    encrypt_str = encrypted[index]
    shifted_back = bytes((b - (index + 1)) % 256 for b in encrypt_str)
    decoded_bytes = base64.b64decode(shifted_back)
    return decoded_bytes.decode('utf-8')

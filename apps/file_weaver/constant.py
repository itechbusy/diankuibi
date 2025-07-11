import re

# Matches level 1-6 titles of markdown documents
HEADER_PATTERN = re.compile(r'^(#{1,6})\s+(.*)$')
MAX_HEADER_LEVEL = 6

# Label separator that AI may return
SPLIT_SEPARATOR = [';', '；', ',', '，', '、', ' ', '<br>', r'\r\n', r'\n']

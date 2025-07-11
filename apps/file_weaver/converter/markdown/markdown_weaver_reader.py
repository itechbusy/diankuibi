import re
from collections import deque
from typing import List

from common.constant import BASE_CHUNK_TAGS
from common.str_transcoding import str_decrypt
from file_weaver.constant import HEADER_PATTERN


class ContentNode:
    """
    Nodes that have hierarchical relationships
    """
    __slots__ = (
        'title', 'level', 'children',
        'start_line', 'end_line',
        'chunk', 'compensate', 'deep_node'
    )

    def __init__(self, title, level, start_line=0, end_line=0, chunk=False, compensate=False, deep_node=False):
        self.title = title
        self.level = level
        self.children = []
        self.start_line = start_line
        self.end_line = end_line
        self.chunk = chunk
        self.compensate = compensate
        self.deep_node = deep_node


class ContentBlock:
    """
    Document fragments that contain line numbers
    """
    __slots__ = (
        'content', 'start_line', 'end_line',
        'context', 'labels'
    )

    def __init__(self, content: str, start_line=0, end_line=0, context=None, labels: str = ""):
        if context is None:
            context = []
        self.content = content
        self.start_line = start_line
        self.end_line = end_line
        self.context = context
        self.labels = labels


async def _extract_title_ranges(md_file_path):
    """
    Extract all document titles
    :param md_file_path: File path of Markdown file
    :return: A collection of document title information
    """
    nodes = []
    stack = deque()
    current_line = 0

    with open(md_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            current_line += 1
            match = HEADER_PATTERN.match(line.strip())
            if not match:
                continue

            level = len(match.group(1))
            title = match.group(2).strip()
            new_node = ContentNode(title, level, current_line)

            while stack and stack[-1].level >= level:
                prev_node = stack.pop()
                prev_node.end_line = current_line - 1

            stack.append(new_node)
            nodes.append(new_node)

    while stack:
        node = stack.pop()
        node.end_line = current_line

    return nodes


async def _build_hierarchy(nodes):
    """
    Associate the document title nodes into a tree structure
    :param nodes:
    :return: The title information of the tree structure
    """
    root = ContentNode("ROOT", 0)
    stack = [root]

    for node in nodes:
        while stack[-1].level >= node.level:
            stack.pop()
        parent = stack[-1]
        parent.children.append(node)
        stack.append(node)

    def postorder_traversal(node):
        for child in node.children:
            postorder_traversal(child)
        node.deep_node = any(child.children for child in node.children)

    for child in root.children:
        postorder_traversal(child)

    return root.children


async def md_converter_trees(md_file_path):
    """
    Turn the title of the markdown document into a tree structure
    :param md_file_path: File path of Markdown file
    :return: The title information of the tree structure
    """
    return await _build_hierarchy(await _extract_title_ranges(md_file_path))


async def _has_deep_node(node: ContentNode):
    """
    Marks whether the node contains subordinate or subordinate nodes
    :param node:
    :return:
    """
    if not node.children: return

    for child in node.children:
        if child.children:
            await _has_deep_node(child)
        else:
            child.deep_node = True


async def split_markdown(file_path: str) -> List[ContentBlock]:
    """
    Read the file to get the split document fragments
    :param file_path: File path of Markdown file
    :return: Document fragment collection
    """
    blocks = []
    current_block = []
    start_line = 1
    pattern = re.compile(re.escape(str_decrypt(BASE_CHUNK_TAGS)))

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if pattern.search(line.strip()):
                end_line = line_num - 1 if line_num > start_line else start_line
                blocks.append(ContentBlock(
                    content=''.join(current_block).strip(),
                    start_line=start_line,
                    end_line=end_line
                ))
                start_line = line_num + 1
                current_block = []
            else:
                current_block.append(line)

        if start_line <= line_num:
            blocks.append(ContentBlock(
                content=''.join(current_block).strip(),
                start_line=start_line,
                end_line=line_num
            ))

    return blocks

import logging
import re
import time
from functools import wraps
from typing import Dict, List

from application.models import chunk_settings

from common.constant import BASE_CHUNK_TAGS
from common.str_transcoding import str_decrypt
from file_weaver.constant import SPLIT_SEPARATOR
from file_weaver.converter.markdown.markdown_weaver_reader import ContentNode, md_converter_trees, split_markdown
from file_weaver.converter.markdown.markdown_weaver_writer import LineOpt, modify_markdown
from processor.models import model_settings
from processor.processor import text_reasoning
from processor.prompt_templates import CHUNK_GENERATE_PROMPTS

logging = logging.getLogger("markdown_splitter")


async def _generate_labels(chunks, chunk_setting):
    """
     Context is generated for shards.
     Content less than 10 is directly regarded as a label, and more than 10 is summarized as a label by AI.
    :param chunks: All shards
    :param chunk_setting: Configuration requirements for sharding
    :return: No return value
    """
    last_chunk = None

    new_chunks = []
    for chunk in chunks:
        trip_content = chunk.content.strip()
        if trip_content == 'None': continue
        if len(trip_content) == 0:
            continue

        if len(trip_content) <= 10:
            chunk.labels = trip_content.replace("#", "")
        else:
            model = await model_settings.get_model_byid(chunk_setting.tag_reasoning_model_id)
            prompt = chunk_setting.tag_reasoning_prompt
            if prompt is None or prompt.strip() == "":
                prompt = str_decrypt(CHUNK_GENERATE_PROMPTS).format(content=chunk.content)

            chunk.labels = await text_reasoning(
                prompt=prompt, model_name=None if model is None else model.model_name)
        if last_chunk is not None and chunk_setting.enabled_content_extraction:
            await _add_quick_questions(last_chunk, chunk, chunk_setting)
            await _add_quick_questions(chunk, last_chunk, chunk_setting)
        last_chunk = chunk
        new_chunks.append(chunk)
    return new_chunks


async def _add_quick_questions(source_chunk, target_chunk, chunk_setting):
    """
    Generate contextual content for target_chunk based on source_chunk's labels.
    :param source_chunk: Provide labeled shard
    :param target_chunk: Add contextual shard
    :param chunk_setting: Configuration requirements for sharding
    :return: No return value
    """
    if not hasattr(source_chunk, 'labels') or not source_chunk.labels:
        return

    # Sanitize and restructure poorly formatted AI output.
    labels = ''
    for separator in SPLIT_SEPARATOR:
        labels = re.split(separator, source_chunk.labels)
        if len(labels) != 1: break

    seen = set()
    for label in (l.strip().replace("#", "") for l in labels if l.strip().replace("#", "")):
        if label not in seen:
            seen.add(label)
            target_chunk.context.append(
                f'{chunk_setting.content_start_separator}{label}{chunk_setting.content_end_separator}')
    source_chunk.labels = ";".join(map(str, seen))


async def _mark_last_level(node: ContentNode, parent: ContentNode = None):
    """
    Identify and flag terminal nodes in a hierarchy.
    :param node: Current node
    :param parent: Parent node
    :return: No return value
    """
    if node.children:
        for child in node.children:
            await _mark_last_level(child, node)

        if parent is not None:
            node.chunk = True


async def _remark(node: ContentNode, marked_last: bool = True):
    """
    Mark nodes requiring special processing in the hierarchy.
    :param node: Current node
    :param marked_last: Has the final-level node been marked
    :return: No return value
    """
    if node.chunk and not node.deep_node: return

    if not node.children:
        node.chunk = True
    else:
        node.chunk = True
        if marked_last and not node.deep_node: return

        node.compensate = True
        for child in node.children:
            await _remark(child)


async def _chunk_seq(root: ContentNode, line_opts: Dict[int, List[LineOpt]], line_change, enabled_title_compensation,
                     name_path: str = ''):
    """
    Based on the tag, generate separator, title retention, and title compensation
    """
    if root.chunk:
        if not root.compensate:
            if name_path is not None and name_path != '' and enabled_title_compensation:
                line_change[root.start_line] = [LineOpt(1, name_path)]
            line_opts[root.end_line] = [LineOpt(0, str_decrypt(BASE_CHUNK_TAGS))]
        else:
            compensate_context = ''
            end_line = 0
            for node in root.children:
                compensate_context = compensate_context + node.title
                if end_line == 0:
                    end_line = node.start_line
                elif end_line > node.start_line:
                    end_line = node.start_line
                await _chunk_seq(node, line_opts, line_change, enabled_title_compensation, root.title + name_path)
            if compensate_context != '' and enabled_title_compensation:
                line_change[root.start_line] = [LineOpt(1, compensate_context)]
            line_opts[end_line - 1] = [LineOpt(0, str_decrypt(BASE_CHUNK_TAGS))]


async def _reindex_chunk_seq(chunks, line_change):
    """
     Reindex the shard structure to add context, labels, compensation information, and title retention policies to the document
    """
    for chunk in chunks:
        start_line = line_change.get(chunk.start_line)
        if start_line is None:
            line_change[chunk.start_line] = [LineOpt(0, chunk.labels)]
        else:
            start_line.insert(0, LineOpt(0, chunk.labels))

        context = [LineOpt(0, text) for text in chunk.context]
        line_change[chunk.end_line + 1] = context


async def _resorted_line_number(line_change):
    """
     Reindex lines that require compensation and title retention to the document location after adding delimiters.
    :param line_change: The list of rows and columns that need to be changed
    :return: No return value
    """
    if line_change:
        index = len(line_change)
        tmp_line_change = sorted(line_change.keys(), reverse=True)
        for key in tmp_line_change:
            if key != 1:
                line_change[key + (index - 1)] = line_change[key]
                line_change.pop(key)
                index -= 1


def callback_with_timing():
    """
     Callback decorator
     The caller can pass in a callback function that returns information to the caller about the result of the processing,
      how long it took, and so on
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(md_file_path: str, file_id=None, callback=None, *args, **kwargs):
            start = time.perf_counter()
            success = False
            try:
                result = await func(md_file_path, *args, **kwargs)
                success = True
                return result
            except Exception as e:
                logging.error(f"File processing failed. File path: {md_file_path} e: {str(e)}")
                raise
            finally:
                duration = time.perf_counter() - start
                if callback is not None:
                    await callback(
                        file_id=file_id,
                        file_path=md_file_path,
                        successfully=success,
                        sharding_time=int(duration * 1000)
                    )

        return wrapper

    return decorator


@callback_with_timing()
async def markdown_sharding(md_file_path: str):
    """
     Markdown Document fragment
     Fragment markdown files in standard format according to rules
     Label generation and context binding for fragment content
    """
    nodes = await md_converter_trees(md_file_path)
    line_change = {}
    line_opts = {}
    min_line = 0
    max_line = 0

    chunk_setting = await chunk_settings.get_chunk_settings()
    base_chunk_tag = str_decrypt(BASE_CHUNK_TAGS)
    if not nodes:
        logging.info(f"No headers were extracted from markdown. markdown file path:{md_file_path}")
        await modify_markdown(md_file_path, {-1: [LineOpt(0, base_chunk_tag)]})
    else:
        # Marks nodes and generates split identifiers
        mark_last = True

        if chunk_setting.enabled_same_level_segmentation:
            mark_last = any(node.deep_node is True for node in nodes)

        for node in nodes:
            if min_line == 0 or node.start_line < min_line:
                min_line = node.start_line

            if max_line == 0 or node.end_line > max_line:
                max_line = node.end_line
            if mark_last:
                await _mark_last_level(node)
            await _remark(node, mark_last)
            await _chunk_seq(node, line_opts, line_change, chunk_setting.enabled_title_compensation)

        # Split document
        if line_opts:
            if min_line != 1:
                line = line_opts.get(min_line)
                if line is None:
                    line_opts[min_line] = [LineOpt(0, base_chunk_tag)]
                # else:
                #     line.insert(0, LineOpt(0, f'{base_chunk_tag}'))
            await modify_markdown(md_file_path, line_opts, max_line, True)

    # Reorder the rows that need action
    if line_change:
        await _resorted_line_number(line_change)

    if chunk_setting.enabled_tag_reasoning:
        # Gets the segmented document shard and generates a context label
        chunks = await split_markdown(md_file_path)
        chunks = await _generate_labels(chunks, chunk_setting)
        await _reindex_chunk_seq(chunks, line_change)

    if chunk_setting.enabled_tag_reasoning or chunk_setting.enabled_title_compensation:
        await modify_markdown(md_file_path, line_change)

import os
import tempfile
from pathlib import Path


class LineOpt:
    """
    Operations on document lines
    opt_type: Type of operation,0 indicates that a new row is added before the current row, and 1 indicates that the current row is modified
    context: Modified or added content
    """
    __slots__ = ('opt_type', 'context')

    def __init__(self, opt_type, context):
        self.opt_type = opt_type
        self.context = context


async def modify_markdown(md_file_path, line_processor, max_line=None, enable_skip_first: bool = False):
    """
    Modify the markdown file based on the operation information
    :param enable_skip_first: Enable skipping meaningless first line of document. When enabled, it will skip empty strings, None, and single characters
    :param md_file_path: File path
    :param line_processor: Row operation
    :param max_line: Last line
    """
    deal_last = False
    processed_lines = set()
    for ln in set(line_processor.keys()):
        if ln < 0:
            deal_last = True
        else:
            processed_lines.add(ln)

    # Process line by line starting from the smallest line
    sorted_lines = sorted(processed_lines)

    with tempfile.NamedTemporaryFile(
            dir=f'{Path(md_file_path).parent}',
            mode='w',
            encoding='utf-8',
            delete=False
    ) as tmp_file, open(md_file_path, 'r', encoding='utf-8') as src_file:
        tmp_path = tmp_file.name
        current_line = 1
        lines_iter = iter(sorted_lines)
        target_line = next(lines_iter, None)
        skip_first_line = False
        for line in src_file:
            if target_line is not None and current_line == target_line:
                if skip_first_line and current_line == 2:
                    skip_first_line = False
                    continue
                processor = line_processor.get(current_line)
                result = await _process_line(line, processor, current_line == max_line)
                if result is not None:
                    for i in result:
                        tmp_file.write(i)
                target_line = next(lines_iter, None)
            else:
                if enable_skip_first and current_line == 1:
                    s_line = line.strip()
                    if s_line == 'None' or len(s_line) < 2:
                        skip_first_line = True
                        current_line += 1
                        continue

                tmp_file.write(line)
            current_line += 1

        if deal_last:
            last = line_processor.get(-1)
            if last is not None:
                tmp_file.write(f"\n{last[0].context}\n")
    os.replace(tmp_path, md_file_path)


async def _process_line(line, processors, is_last_line=False):
    """
    Generates a collection of row operations
    """
    result = []
    add_ctx = []
    update_ctx = []

    for p in processors:
        if p.opt_type == 0:
            add_ctx.append(f"{p.context}\n")
        else:
            update_ctx.append(p.context)

    updated_line = line.strip()
    for ctx in update_ctx:
        updated_line += ctx

    if is_last_line:
        result.append(f"{updated_line}\n")
        result.extend(add_ctx)
    else:
        result.extend(add_ctx)
        result.append(f"{updated_line}\n")

    return result

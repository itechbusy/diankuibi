import ast
import asyncio
import logging
import os
import re
import tarfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

from application.models import chunk_settings
from asgiref.sync import sync_to_async
from common.action_result import ActionResult
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, FileResponse
from markitdown import MarkItDown
from rest_framework.decorators import api_view

from common.constant import BASE_CHUNK_TAGS
from common.str_transcoding import str_decrypt
from file_weaver.converter.markdown.markdown_splitter import markdown_sharding
from processor.models import model_settings
from processor.processor import extract_and_process_images, document_understanding, extract_json_content, \
    json_response_to_dict
from processor.prompt_templates import BASE_IMAGE_PROMPT_QIAN_WEN_LONG, BASE_IMAGE_PROMPT_VL
from task_flow.models import ImageInfo, FileTask
from task_flow.models.file_result import FileResult

logging = logging.getLogger('file_task')


def replace_titles(file_context, md_content):
    # Create title mapping: key is the text part of the title (without '#'), value is the full title
    title_map = {}
    for item in file_context["content"]:
        raw_text = unescape(item["text"])
        title_text = raw_text.lstrip('#').replace(' ', '').replace('\xa0', '').replace(r'\xa0', '').replace(u'\xa0', '')
        title_map[title_text] = raw_text

    # Process content line by line
    lines = md_content.split('\n')
    updated_lines = []

    # Record the replaced titles
    matched_titles = set()  # Record the replaced titles

    for line in lines:
        stripped_line = re.sub(r'\s+', '',
                               line.replace('*', '').replace('\xa0', '').replace(r'\xa0', '').replace(u'\xa0', ''))
        if stripped_line in title_map:
            matched_titles.add(stripped_line)
            updated_lines.append(title_map[stripped_line])
        else:
            updated_lines.append(line)

    # Find unmatched titles
    unmatched_titles = {k: v for k, v in title_map.items() if k not in matched_titles}

    # If there are no unmatched titles, return the result directly
    if not unmatched_titles:
        return '\n'.join(updated_lines)

    # Insert unmatched title
    final_lines = updated_lines.copy()

    # Traverse each unmatched title and attempt to insert
    for title_text, full_title in unmatched_titles.items():
        inserted = False

        # Determine the level of this title, such as # being 1, # # being 2, and so on
        level = len(full_title) - len(full_title.lstrip('#'))

        # Find insertion position: Insert in front of a title one level lower than it
        for i, line in enumerate(final_lines):
            if line.startswith('#' * (level + 1) + ' '):  # A title one level lower than the current title
                final_lines.insert(i, full_title)
                inserted = True
                break

        # If no lower level title is found, add it to the end
        if not inserted:
            final_lines.append(full_title)

    # Return the merged content
    return '\n'.join(final_lines)


def get_base_path():
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_dir))))
    return os.path.join(project_root_parent, "fileList")


@api_view(['POST'])
def get_file_list(request):
    """Process compressed files and folder uploads, save to database and return file list (including database ID)"""
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return HttpResponse(ActionResult.fail(400, "缺少文件。 Missing files. "))

    try:
        # Configure target directory
        suffix = uuid.uuid4().hex
        base_path = get_base_path()
        target_dir = os.path.join(base_path, suffix)
        os.makedirs(target_dir, exist_ok=True)

        file_infos = []

        # Check if it is a compressed file
        allowed_ext = {'.zip', '.tar', '.gz'}
        file_ext = Path(uploaded_file.name).suffix.lower()

        if file_ext in allowed_ext:
            # Save temporary files
            temp_path = default_storage.save(
                f'tmp/{uploaded_file.name}',
                ContentFile(uploaded_file.read())
            )
            full_temp_path = default_storage.path(temp_path)

            try:
                if file_ext == '.zip':
                    with zipfile.ZipFile(full_temp_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.endswith('/'):
                                continue
                            # Generate a unique file name
                            original_name = os.path.basename(file)
                            new_name = f"{uuid.uuid4().hex}{os.path.splitext(original_name)[1]}"
                            dest_path = os.path.join(target_dir, new_name)

                            # write file
                            with zip_ref.open(file) as src_file:
                                with open(dest_path, 'wb') as dest_file:
                                    dest_file.write(src_file.read())

                            # Database operations
                            file_record = FileTask.objects.create(
                                original_file_name=original_name,
                                new_file_name=new_name,
                                file_path=dest_path,
                                file_suffix=suffix,
                            )
                            file_infos.append({'name': original_name, 'id': file_record.id})
                else:
                    with tarfile.open(full_temp_path, 'r:*') as tar_ref:
                        for member in tar_ref.getmembers():
                            if not member.isfile():
                                continue
                            original_name = os.path.basename(member.name)
                            new_name = f"{uuid.uuid4().hex}{os.path.splitext(original_name)[1]}"
                            dest_path = os.path.join(target_dir, new_name)

                            with tar_ref.extractfile(member) as src_file:
                                with open(dest_path, 'wb') as dest_file:
                                    dest_file.write(src_file.read())

                            file_record = FileTask.objects.create(
                                original_file_name=original_name,
                                new_file_name=new_name,
                                file_path=dest_path,
                                file_suffix=suffix,
                                file_status=0
                            )
                            file_infos.append({'name': original_name, 'id': file_record.id})
            finally:
                # Clean up temporary files
                default_storage.delete(temp_path)

        else:
            # Processing regular files
            original_name = uploaded_file.name
            new_name = f"{uuid.uuid4().hex}{os.path.splitext(original_name)[1]}"
            dest_path = os.path.join(target_dir, new_name)

            with open(dest_path, 'wb+') as dest_file:
                for chunk in uploaded_file.chunks():
                    dest_file.write(chunk)

            file_record = FileTask.objects.create(
                original_file_name=original_name,
                new_file_name=new_name,
                file_path=dest_path,
                file_suffix=suffix,
            )
            file_infos.append({'name': original_name, 'id': file_record.id})

        data = {
            'original_name': uploaded_file.name,
            'file_count': len(file_infos),
            'suffix': suffix,
            'files': file_infos
        }
        return HttpResponse(ActionResult.success(data))

    except (zipfile.BadZipFile, tarfile.TarError):
        return HttpResponse(ActionResult.fail(400, "无效的压缩文件 Invalid compressed file."))
    except Exception as e:
        return HttpResponse(ActionResult.fail(500, f'Server error: {str(e)}'))


@api_view(['GET'])
def document_format_conversion(request):
    """Document format conversion"""
    params = request.GET
    suffix = params.get("suffix")
    # Determine file format
    if not suffix:
        return HttpResponse(ActionResult.fail(400, "任务id不能为空 Task ID cannot be empty."))
    files = FileTask.objects.filter(file_suffix=suffix)
    if not files:
        return HttpResponse(ActionResult.fail(500, "任务不存在 Task does not exist."))

    settings = asyncio.run(chunk_settings.get_chunk_settings())
    enabled_picture_reasoning = settings.enabled_picture_reasoning
    picture_reasoning_prompt = settings.picture_reasoning_prompt
    if not picture_reasoning_prompt:
        picture_reasoning_prompt = str_decrypt(BASE_IMAGE_PROMPT_VL)
    title_hierarchy_reasoning_prompt = settings.title_hierarchy_reasoning_prompt
    if not title_hierarchy_reasoning_prompt:
        title_hierarchy_reasoning_prompt = str_decrypt(BASE_IMAGE_PROMPT_QIAN_WEN_LONG)
    picture_reasoning_model_id = settings.picture_reasoning_model_id
    model = asyncio.run(model_settings.get_model_byid(picture_reasoning_model_id))
    picture_reasoning_model_id = None if model is None else model.model_name
    title_reasoning_model_id = settings.title_reasoning_model_id
    model_title = asyncio.run(model_settings.get_model_byid(title_reasoning_model_id))
    title_reasoning_model_id = None if model_title is None else model_title.model_name

    def process_file(file):
        file_name = file.new_file_name
        base_path = get_base_path()
        fixed_path = os.path.join(base_path, file.file_suffix)
        file_path = os.path.join(fixed_path, file_name)
        file_extension = os.path.splitext(file_name)[1]

        # Extract file content
        # Different things may be handled separately later, please handle them uniformly for now
        md = MarkItDown()
        if file_extension in ['.doc', '.docx', '.txt', '.html']:
            result = md.convert(
                file_path
            )
        elif file_extension in ['.xls', '.xlsx', '.csv']:
            result = md.convert(
                file_path
            )
        elif file_extension in ['.ppt', '.pptx']:
            result = md.convert(
                file_path
            )
        elif file_extension == '.pdf':
            result = md.convert(
                file_path
            )
        else:
            return HttpResponse(ActionResult.fail(500, "未知文件格式 Unknown file format."))

        md_content = result.text_content

        # Save temporary files
        temporary_path = os.path.join(fixed_path, "temporaryMd", file_name)
        output_path = f"{os.path.splitext(temporary_path)[0]}.md"
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if enabled_picture_reasoning:
            output_dir = os.path.join(fixed_path, "extracted_images")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            try:
                extract_and_process_images(file_path, output_dir, picture_reasoning_prompt, picture_reasoning_model_id)
            except Exception as e:
                return HttpResponse(ActionResult.fail(500, f"图片提取和处理失败 Image extraction and processing failed.: {str(e)}"))

            # Retrieve the image information of the file from the database
            document_name = os.path.basename(file_path)
            image_infos = ImageInfo.objects.filter(document_name=document_name)

            # Insert image description into Markdown document
            for info in image_infos:
                context_text = info.context_text
                image_description = info.image_description
                try:
                    context_dict = ast.literal_eval(context_text)
                    # Extract key text information
                    content = context_dict.get('content', '')
                    if content in md_content:
                        index = md_content.index(content)
                        insert_index = index + len(content)
                        # Insert image description after contextual content
                        md_content = md_content[:insert_index] + f"\n\n{image_description}\n\n" + md_content[
                                                                                                  insert_index:]
                    else:
                        # If no matching context can be found, insert a description at the end of the document
                        md_content += f"\n\n{image_description}\n\n"
                except (SyntaxError, ValueError):
                    continue

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            file_context = document_understanding(output_path, title_hierarchy_reasoning_prompt,
                                                  title_reasoning_model_id)
            # Remove meaningless text from AI returned data and only retain the JSON string portion
            file_context = extract_json_content(file_context)
            file_context = json_response_to_dict(file_context)
            combined_article = replace_titles(file_context, md_content)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(combined_article)
            # Change task status
            FileTask.objects.filter(id=file.id).update(file_status=1)
            # Document knowledge extraction
            asyncio.run(markdown_sharding(output_path, file.id, update_file_status))
            # Save to database
            file_result_name = os.path.splitext(file_name)
            fixed = file_result_name[0]
            FileResult.objects.create(
                file_name=os.path.join(fixed, ".md"),
                file_path=output_path,
                file_suffix=file.file_suffix,
                file_type=0
            )
            return HttpResponse(ActionResult.success("文件转换成功 File conversion successful."))
        except Exception as e:
            logging.error(f"File processing exception: {e}")
            return HttpResponse(ActionResult.fail(500, f"文件转换失败 File conversion failed: {str(e)}"))

    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(process_file, files))

    return HttpResponse(ActionResult.success("所有文件转换成功 All files converted successfully."))


async def update_file_status(file_id, file_path, successfully, sharding_time):

    @sync_to_async
    def update_status_sync():
        FileTask.objects.filter(id=file_id).update(file_status=2)

    if successfully:
        await update_status_sync()
    else:
        logging.error(f'{file_id:File content format error}')


@api_view(['GET'])
def document_combination(request):
    """Document combination"""
    params = request.GET
    folder_path = params.get("folder_path")
    if not folder_path:
        return HttpResponse(ActionResult.fail(400, "参数folder_path不能为空 The parameter folderpath cannot be empty."))
    base_path = get_base_path()
    target_dir = os.path.join(base_path, folder_path, "temporaryMd")
    if not os.path.exists(target_dir):
        return HttpResponse(ActionResult.fail(500, "文件路径不存在 The file path does not exist."))
    md_files = [f for f in os.listdir(target_dir) if f.endswith('.md')]
    combined_content = ""
    for md_file in md_files:
        file_path = os.path.join(target_dir, md_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                combined_content += f.read() + "\n\n"
        except Exception as e:
            return HttpResponse(ActionResult.fail(500, "文件读取错误 File read error."))
    output_dir = os.path.join(target_dir, "combined_md")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file_path_combined = os.path.join(output_dir, "combined.md")
    try:
        with open(output_file_path_combined, 'w', encoding='utf-8') as f:
            f.write(combined_content)
            file_name_combined = os.path.basename(output_file_path_combined)
            FileResult.objects.create(
                file_name=file_name_combined,
                file_path=output_file_path_combined,
                file_suffix=folder_path,
                file_type=2
            )
    except Exception as e:
        return HttpResponse(ActionResult.fail(500, "文件写入错误 File write error."))

    settings = asyncio.run(chunk_settings.get_chunk_settings())
    enabled_markdown_split = settings.enabled_markdown_split
    base_chunk_tag = str_decrypt(BASE_CHUNK_TAGS)

    if enabled_markdown_split:
        max_size = 50 * 1024 * 1024  # 50MB
        chunks = []
        current_chunk = ""
        for line in combined_content.splitlines(keepends=True):
            current_chunk += line
            if line.strip() == base_chunk_tag:
                chunks.append(current_chunk)
                current_chunk = ""
        if current_chunk:
            chunks.append(current_chunk)

        current_file_content = ""
        file_index = 1
        output_files = []
        for chunk in chunks:
            if len(current_file_content.encode('utf-8')) + len(chunk.encode('utf-8')) > max_size:
                output_file_path = os.path.join(output_dir, f"combined_{file_index}.md")
                try:
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(current_file_content)
                    file_name = os.path.basename(output_file_path)
                    FileResult.objects.create(
                        file_name=file_name,
                        file_path=output_file_path,
                        file_suffix=folder_path,
                        file_type=1
                    )
                except Exception as e:
                    return HttpResponse(ActionResult.fail(500, "文件写入错误 File write error."))
                output_files.append(output_file_path)
                current_file_content = chunk
                file_index += 1
            else:
                current_file_content += chunk

        if current_file_content:
            output_file_path = os.path.join(output_dir, f"combined_{file_index}.md")
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(current_file_content)
                file_name = os.path.basename(output_file_path)
                FileResult.objects.create(
                    file_name=file_name,
                    file_path=output_file_path,
                    file_suffix=folder_path,
                    file_type=1
                )
            except Exception as e:
                return HttpResponse(ActionResult.fail(500, "文件写入错误 File write error."))
            output_files.append(output_file_path)
        return HttpResponse(ActionResult.success(data=output_files, message="文档组合并分隔成功 Successfully combined and separated documents."))
    else:
        output_file_path = os.path.join(output_dir, "combined.md")
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(combined_content)
            file_name = os.path.basename(output_file_path)
            FileResult.objects.create(
                file_name=file_name,
                file_path=output_file_path,
                file_suffix=folder_path,
                file_type=1
            )
        except Exception as e:
            return HttpResponse(ActionResult.fail(500, "文件写入错误  File write error."))
        return HttpResponse(ActionResult.success(data=output_file_path, message="文档组合成功 Document combination successful."))


@api_view(['GET'])
def query_task_status(request):
    """Task status query"""
    params = request.GET
    folder_path = params.get("folder_path")
    if not folder_path:
        return HttpResponse(ActionResult.fail(400, "参数folder_path不能为空 The parameter folder_path cannot be empty."))
    files = FileTask.objects.filter(file_suffix=folder_path)
    data_list = []
    for file in files:
        data = {
            'id': file.id,
            'original_file_name': file.original_file_name,
            'new_file_name': file.new_file_name,
            'file_path': file.file_path,
            'file_status': file.file_status,
            'file_suffix': file.file_suffix
        }
        data_list.append(data)
    return HttpResponse(ActionResult.success(data_list))


@api_view(['GET'])
def query_result_list(request):
    """result file query"""
    params = request.GET
    file_suffix = params.get("file_suffix")
    if not file_suffix:
        return HttpResponse(ActionResult.fail(400, "参数file_suffix不能为空 The parameter file_suffix cannot be empty."))
    files = FileResult.objects.filter(file_suffix=file_suffix)
    data_list = []
    for file in files:
        data = {
            'id': file.id,
            'file_name': file.file_name,
            'file_path': file.file_path,
            'file_type': file.file_type,
            'file_suffix': file.file_suffix
        }
        data_list.append(data)
    return HttpResponse(ActionResult.success(data_list))


@api_view(['GET'])
def file_download(request):
    """file_download"""
    params = request.GET
    file_path = params.get("file_path")
    if not file_path:
        return HttpResponse(ActionResult.fail(400, "参数file_path不能为空 The parameter file_path cannot be empty."))

    # Check if the file exists
    if not os.path.exists(file_path):
        return HttpResponse(ActionResult.fail(404, "文件不存在 file does not exist."))

    try:
        # Open the file and return FileResponse
        response = FileResponse(open(file_path, 'rb'))
        # Get file name
        file_name = os.path.basename(file_path)
        # Set response header, specify file name
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response
    except Exception as e:
        return HttpResponse(ActionResult.fail(500, f"文件下载出错 File download error.: {str(e)}"))


@api_view(['GET'])
def read_file_content(request):
    """Read file content"""
    params = request.GET
    file_id = params.get("file_id")
    file = FileResult.objects.get(id=file_id)
    file_path = file.file_path
    return FileResponse(open(file_path, 'rb'), content_type='text/markdown; charset=utf8')

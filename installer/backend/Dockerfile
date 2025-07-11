FROM crpi-dibzp3srvk442n0r.cn-beijing.personal.cr.aliyuncs.com/diankuibi/python:3-10.18
 
WORKDIR /app
 
COPY . /app/
 
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
 
EXPOSE 8080
 
CMD ["python", "apps/manage.py", "runserver", "0.0.0.0:8080"]

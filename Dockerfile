FROM python:3.12

COPY requirements_py312.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy sources
COPY static ./static
COPY templates ./templates
COPY helpers.py ./
COPY plotgen.py ./
COPY dbaccess.py ./
COPY server.py ./

EXPOSE 5000
EXPOSE 5678
ENV PYTHONUNBUFFERED=1
ENV IS_RUNNING_IN_DOCKER=Yes
ENV TZ=Europe/Helsinki

CMD ["python", "server.py", "--config_path", "/ct_config", "--data_path", "ct_data"]

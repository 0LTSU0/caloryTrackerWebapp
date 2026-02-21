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
ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py", "--config_path", "/ct_config", "--data_path", "ct_data"]

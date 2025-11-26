FROM python:3.11-slim
WORKDIR /app
RUN pip install marimo pandas xmltodict xlsxwriter
COPY . .
EXPOSE 80
CMD ["marimo", "run", "app.py", "--host", "0.0.0.0", "--port", "80"]
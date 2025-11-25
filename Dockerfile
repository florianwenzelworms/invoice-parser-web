FROM python:3.11-slim

WORKDIR /app

# Dependencies installieren
# (Ideal wäre requirements.txt, aber für hier reicht inline)
RUN pip install marimo pandas xmltodict xlsxwriter

# Code kopieren
COPY . .

# Port exponieren
EXPOSE 80

# User anlegen (Best Practice, nicht als root laufen lassen)
RUN useradd -m marimo_user
USER marimo_user

# Startbefehl
CMD ["marimo", "run", "marimo.py", "--host", "0.0.0.0", "--port", "80"]
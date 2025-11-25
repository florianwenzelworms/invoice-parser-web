import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import os
    import json
    import zipfile
    import pandas as pd
    import logging
    import urllib.parse
    from datetime import datetime
    import glob
    from io import BytesIO

    # Importiere deine Datei
    from Invoice import Invoice

    # --- KONFIGURATION ---
    CONFIG_DIR = "configs"
    CURRENT_CONFIG_FILE = os.path.join(CONFIG_DIR, "current_config.json")

    # Sicherstellen, dass der Ordner existiert
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Standard-Fallback (falls gar nichts existiert)
    default_fallback = {
        "Allgemein": {"xSta": "05000.10000"},
        "hsh.olav": {"FueZ": "11310.10010"}
    }

    # --- HELPER FUNKTIONEN ---

    def get_saved_configs():
        """Liest alle Config-Dateien und formatiert sie für das Dropdown."""
        files = glob.glob(os.path.join(CONFIG_DIR, "config_*.json"))
        files.sort(key=os.path.getmtime, reverse=True) # Neueste zuerst

        options = {}
        for f in files:
            try:
                # Dateiname: config_YYYY-MM-DD_HH-MM-SS_XXrows.json
                name = os.path.basename(f)
                parts = name.replace("config_", "").replace(".json", "").split("_")

                # Datum & Zeit schön formatieren
                date_part = parts[0] # YYYY-MM-DD
                time_part = parts[1].replace("-", ":") # HH:MM:SS
                rows_part = parts[2].replace("rows", "") # Anzahl Zeilen

                dt_obj = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                pretty_date = dt_obj.strftime("%d.%m.%Y um %H:%M Uhr")

                label = f"📅 {pretty_date} ({rows_part} Einträge)"
                options[label] = f # Der Wert ist der volle Pfad
            except:
                continue

        return options

    def load_json(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_fallback

    def flatten_data(data):
        """Wandelt JSON Baum in Tabelle um"""
        flat_list = []
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    flat_list.append({"Gruppe": key, "Name": sub_key, "USK": sub_val})
            else:
                flat_list.append({"Gruppe": "BASIS", "Name": key, "USK": value})
        return flat_list
    return (
        BytesIO,
        CONFIG_DIR,
        CURRENT_CONFIG_FILE,
        Invoice,
        datetime,
        default_fallback,
        flatten_data,
        get_saved_configs,
        json,
        load_json,
        logging,
        mo,
        os,
        pd,
        urllib,
        zipfile,
    )


@app.cell
def _(mo):
    # --- BUTTON DEFINITIONEN ---
    # Wir definieren sie hier, damit nachfolgende Zellen darauf reagieren können

    btn_save_version = mo.ui.button(
        label="💾 Als Backup speichern", 
        tooltip="Erstellt eine neue Datei mit Zeitstempel im Archiv.",
        kind="neutral"
    )

    btn_load_backup = mo.ui.button(
        label="📂 Laden",
        tooltip="Überschreibt die aktuelle Tabelle mit der gewählten Datei.",
        kind="warn"
    )
    return btn_load_backup, btn_save_version


@app.cell
def _(
    CONFIG_DIR,
    CURRENT_CONFIG_FILE,
    btn_save_version,
    datetime,
    default_fallback,
    flatten_data,
    get_saved_configs,
    json,
    load_json,
    mo,
    os,
):
    # --- LOGIK: BACKUP SPEICHERN ---
    save_msg = ""

    # Wir prüfen, ob der Button geklickt wurde
    if btn_save_version.value:
        try:
            # Sicherheitshalber Ordner erstellen, falls er fehlt
            os.makedirs(CONFIG_DIR, exist_ok=True)
        
            # Datenquelle bestimmen: Entweder aktuelle Config oder Fallback
            if os.path.exists(CURRENT_CONFIG_FILE):
                data_to_backup = load_json(CURRENT_CONFIG_FILE)
            else:
                # Falls noch keine Datei da ist, nehmen wir die Defaults
                data_to_backup = default_fallback
            
            # Dateinamen generieren
            row_count = len(flatten_data(data_to_backup))
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
            backup_filename = f"config_{timestamp}_{row_count}rows.json"
            backup_filepath = os.path.join(CONFIG_DIR, backup_filename)
        
            # Speichern
            with open(backup_filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_backup, f, indent=4)
        
            save_msg = f"✅ Backup erstellt: {backup_filename}"
        
        except Exception as e:
            save_msg = f"❌ Fehler: {str(e)}"

    # --- DROPDOWN BAUEN ---
    # Liste aktualisieren (damit das neue Backup sofort erscheint)
    backup_options = get_saved_configs()

    dd_backups = mo.ui.dropdown(
        options=backup_options,
        label="Wiederherstellen aus Archiv:",
        full_width=True
    )
    return dd_backups, save_msg


@app.cell
def _(
    CURRENT_CONFIG_FILE,
    btn_load_backup,
    btn_save_version,
    dd_backups,
    default_fallback,
    flatten_data,
    load_json,
    mo,
    os,
    pd,
    save_msg,
):
    # --- LOGIK: DATEN LADEN ---
    load_msg = ""
    current_data = default_fallback # Default Startwert

    # Entscheidung: Was laden wir?
    if btn_load_backup.value and dd_backups.value:
        # Fall A: Backup laden
        if os.path.exists(dd_backups.value):
            current_data = load_json(dd_backups.value)
            load_msg = mo.callout(f"♻️ Stand wiederhergestellt: {os.path.basename(dd_backups.value)}", kind="info")
    elif os.path.exists(CURRENT_CONFIG_FILE):
        # Fall B: Aktuelle Config laden (Normalfall)
        current_data = load_json(CURRENT_CONFIG_FILE)

    # --- TABELLE VORBEREITEN ---
    df_raw = pd.DataFrame(flatten_data(current_data))
    df_komplett = df_raw.rename(columns={
        "Gruppe": "Gruppe (Kategorie)",
        "Name": "Name / Beschreibung der Position",
        "USK": "USK Nummer (Format 12345.12345)"
    })

    tabelle_editor = mo.ui.data_editor(
        data=df_komplett, 
        label="Tabelle bearbeiten (Änderungen werden in 'current_config' auto-gespeichert)",
    )

    file_uploader = mo.ui.file(
        label="XML Dateien hier ablegen", 
        kind="area", 
        multiple=True,
        filetypes=[".xml"]
    )

    # --- CSS STYLES ---
    styles = mo.Html("""
        <style>
            #marimo-header button[aria-label='App menu'], header button[aria-label='App menu'] { display: none !important; }
            .email-btn {
                display: inline-block; padding: 0.5rem 1rem; background-color: #fee2e2; color: #991b1b;
                border: 1px solid #fca5a5; border-radius: 0.375rem; text-decoration: none; font-weight: 600;
            }
            a[download] {
                display: inline-block; width: 100%; text-align: center; background-color: #16a34a !important;
                color: white !important; padding: 12px 20px; font-weight: bold; border-radius: 8px; text-decoration: none;
            }
        </style>
    """)

    # --- LAYOUT ---
    backup_ui = mo.accordion({
        "⚙️ Konfigurationen verwalten (Laden / Speichern)": mo.vstack([
            mo.hstack([btn_save_version, mo.md(f"*{save_msg}*")]),
            mo.md("---"),
            mo.hstack([dd_backups, btn_load_backup], align="end"),
            load_msg if load_msg else mo.md("")
        ])
    })

    mo.vstack([
        styles,
        mo.md("# 🧾 Invoice Parser Web"),
        mo.md("**Info:** Die Tabelle speichert automatisch. Erstelle Backups bei größeren Änderungen."),
        backup_ui,
        tabelle_editor,
        mo.md("---"),
        file_uploader
    ])
    return file_uploader, tabelle_editor


@app.cell
def _(
    BytesIO,
    CURRENT_CONFIG_FILE,
    Invoice,
    file_uploader,
    json,
    logging,
    mo,
    os,
    tabelle_editor,
    tempfile,
    urllib,
    zipfile,
):
    processed_files = []
    log_messages = []
    ergebnis_anzeige = []

    # --- 1. DATEN VERARBEITEN & AUTO-SAVE ---
    df_neu = tabelle_editor.value
    usk_struktur = {}

    for index, row in df_neu.iterrows():
        gruppe = str(row["Gruppe (Kategorie)"]).strip()
        name = str(row["Name / Beschreibung der Position"]).strip()
        usk = str(row["USK Nummer (Format 12345.12345)"]).strip()

        if not name or not usk: continue
        if not gruppe: gruppe = "BASIS"

        if gruppe == "BASIS":
            usk_struktur[name] = usk
        else:
            if gruppe not in usk_struktur: usk_struktur[gruppe] = {}
            usk_struktur[gruppe][name] = usk

    usk_json_string = json.dumps(usk_struktur, indent=4)

    # AUTO-SAVE: Wir überschreiben immer die 'current_config.json'
    try:
        with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f_write:
            json.dump(usk_struktur, f_write, indent=4)
    except Exception as e:
        log_messages.append(f"❌ Warnung: Auto-Save fehlgeschlagen: {e}")

    # -------------------------------------

    problematische_dateien = []

    if file_uploader.value:
        logger = logging.getLogger("Invoice Parser")
        logger.handlers = []
        logger.addHandler(logging.NullHandler())
        logger.propagate = False

        with tempfile.TemporaryDirectory() as temp_dir:
            src_path = os.path.join(temp_dir, "input") + os.sep
            dest_path = os.path.join(temp_dir, "output") + os.sep
            os.makedirs(src_path, exist_ok=True)
            os.makedirs(dest_path, exist_ok=True)

            for file_obj in file_uploader.value:
                file_path = os.path.join(src_path, file_obj.name)
                with open(file_path, "wb") as f_up:
                    f_up.write(file_obj.contents)

            fake_config = {
                "files": {"source_path": src_path, "destination_path": dest_path},
                "usk": {"usk_liste": usk_json_string}
            }

            files_in_temp = os.listdir(src_path)
            for filename in files_in_temp:
                try:
                    invoice_processor = Invoice(filename, fake_config)
                    created_file_path = invoice_processor.create_file()

                    if os.path.exists(created_file_path):
                        with open(created_file_path, "rb") as f_res:
                            processed_files.append({
                                "name": os.path.basename(created_file_path),
                                "content": f_res.read()
                            })
                        log_messages.append(f"✅ {filename} erfolgreich verarbeitet.")
                    else:
                        log_messages.append(f"⚠️ {filename}: Excel wurde nicht erstellt.")
                        problematische_dateien.append(filename)
                except Exception as e:
                    err_msg = str(e)
                    log_messages.append(f"❌ Fehler bei {filename}: {err_msg}")
                    problematische_dateien.append(filename)

    # --- EMAIL & AUSGABE ---
    fehler_text = "\n".join([msg for msg in log_messages if "❌" in msg or "⚠️" in msg])
    if not fehler_text: fehler_text = "Keine offensichtlichen Fehler im Protokoll."

    dateien_hinweis = ""
    if problematische_dateien:
        dateien_hinweis = f"Dateien: {', '.join(problematische_dateien)}"

    email_body = f"""Hallo Hotline-Team,

    ich habe Probleme mit dem Invoice Parser.

    --- FEHLERPROTOKOLL ---
    {fehler_text}

    --- BETROFFENE DATEIEN ---
    {dateien_hinweis if dateien_hinweis else "Keine spezifischen Dateien betroffen."}

    ***********************************************************************
    >>> BITTE DIESE DATEIEN MANUELL AN DIESE E-MAIL ANHÄNGEN! <<<
    ***********************************************************************

    --- VERWENDETE CONFIG ---
    {usk_json_string}

    Viele Grüße
    """

    params = {"subject": "Invoice Parser Web Anfrage", "body": email_body}
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote) 
    mailto_link = f"mailto:hotline@worms.de?{query_string}"

    email_button = mo.Html(f"""
        <div style="margin-top: 20px; text-align: right;">
            <a href="{mailto_link}" class="email-btn">📧 Fehler melden (Email öffnen)</a>
        </div>
    """)

    if processed_files or log_messages:
        ergebnis_anzeige.append(mo.md("**Verarbeitungsprotokoll:**\n" + "\n".join([f"* {msg}" for msg in log_messages])))
        ergebnis_anzeige.append(email_button)

        if processed_files:
            anzahl_erfolg = len(processed_files)
            anzahl_gesamt = len(file_uploader.value)
            status_text = f"{anzahl_erfolg}/{anzahl_gesamt} Dateien wurden erfolgreich konvertiert."

            if len(processed_files) == 1:
                dl_obj = mo.download(processed_files[0]["content"], filename=processed_files[0]["name"], label=f"Download {processed_files[0]['name']}")
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for p_file in processed_files:
                        zip_file.writestr(p_file["name"], p_file["content"])
                dl_obj = mo.download(zip_buffer.getvalue(), filename="rechnungen_export.zip", label=f"Download alle ({len(processed_files)} Dateien) als ZIP")

            ergebnis_anzeige.append(mo.callout(mo.vstack([mo.md(f"### 🎉 Fertig!\n**{status_text}**"), dl_obj]), kind="success"))

    mo.vstack(ergebnis_anzeige)
    return


if __name__ == "__main__":
    app.run()

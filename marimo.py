import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import os
    import tempfile
    import json
    import zipfile
    import pandas as pd
    import logging
    import urllib.parse
    from io import BytesIO

    # Importiere deine Datei
    from Invoice import Invoice

    CONFIG_FILE = "usk_config.json"

    # Standard-Werte (Fallback)
    default_fallback = {
        "xSta": "05000.10000",
        "cv.sta.urkunden": "05000.10000",
        "iKFZ": "11500.10001",
        "all": "32105.11000",
        "cv.verpflichtungserk": "11310.10001",
        "hsh.olav": {
        	"FueZ": "11310.10010",
        	"FUEZ": "11310.10010",
        	"MeldeB": "11300.10010",
        	"GZRA": "11300.10010",
        	"AUFB": "11300.10010",
        	"AufB": "11300.10010"
        },
        "civento": {
           "11500.10002": "11500.10002",
           "11500100002": "11500.10002",
           "115001000026": "11500.10002",
    	    "32100.10001": "32100.10001"
        }
    }

    # Config laden
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f_read:
                default_data = json.load(f_read)
        else:
            default_data = default_fallback
    except Exception as e:
        print(f"Fehler beim Laden der Config: {e}")
        default_data = default_fallback
    return (
        BytesIO,
        CONFIG_FILE,
        Invoice,
        default_data,
        default_fallback,
        json,
        logging,
        mo,
        os,
        pd,
        tempfile,
        urllib,
        zipfile,
    )


@app.cell
def _(mo):
    # 1. Der Reset-Button
    btn_reset = mo.ui.button(
        label="⚠️ Standard-Werte wiederherstellen", 
        kind="danger", 
        tooltip="Klicken, falls du die Konfiguration kaputt gemacht hast."
    )

    # 2. Helper Funktion
    def flatten_data(data):
        flat_list = []
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    flat_list.append({"Gruppe": key, "Name": sub_key, "USK": sub_val})
            else:
                flat_list.append({"Gruppe": "BASIS", "Name": key, "USK": value})
        return flat_list
    return btn_reset, flatten_data


@app.cell
def _(btn_reset, default_data, default_fallback, flatten_data, mo, pd):
    # 1. Daten Auswahl
    aktuelles_daten_set = default_data
    if btn_reset.value:
        aktuelles_daten_set = default_fallback

    # 2. DataFrame bauen
    df_raw = pd.DataFrame(flatten_data(aktuelles_daten_set))
    df_komplett = df_raw.rename(columns={
        "Gruppe": "Gruppe (Kategorie)",
        "Name": "Name / Beschreibung der Position",
        "USK": "USK Nummer (Format 12345.12345)"
    })

    # 3. UI Elemente
    tabelle_editor = mo.ui.data_editor(
        data=df_komplett, 
        label="Tabelle bearbeiten (Änderungen werden automatisch gespeichert)",
    )

    file_uploader = mo.ui.file(
        label="XML Dateien hier ablegen", 
        kind="area", 
        multiple=True,
        filetypes=[".xml"]
    )

    # --- CSS HACK: Styles ---
    hide_menu_style = mo.Html("""
        <style>
            /* Menü ausblenden */
            #marimo-header button[aria-label='App menu'], 
            header button[aria-label='App menu'] { display: none !important; }
        
            /* Style für den Email-Button (Rot) */
            .email-btn {
                display: inline-block;
                padding: 0.5rem 1rem;
                background-color: #fee2e2; 
                color: #991b1b;
                border: 1px solid #fca5a5;
                border-radius: 0.375rem;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 600;
                cursor: pointer;
            }
            .email-btn:hover { background-color: #fecaca; }

            /* NEU: Style für den Download-Button (Fett & Grün) */
            /* Wir selektieren alle Links mit einem download-Attribut */
            a[download] {
                display: inline-block;
                width: 100%;             /* Volle Breite */
                text-align: center;
                background-color: #16a34a !important; /* Kräftiges Grün */
                color: white !important;
                padding: 12px 20px;
                font-size: 1.1rem;
                font-weight: bold;
                border-radius: 8px;
                text-decoration: none;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: transform 0.1s;
            }
            a[download]:hover {
                background-color: #15803d !important; /* Dunkleres Grün beim Hover */
                transform: scale(1.01);
            }
        </style>
    """)

    # Layout
    mo.vstack([
        hide_menu_style,
        mo.md("# 🧾 Invoice Parser Web"),
        mo.md("**Info:** Änderungen an der Tabelle werden sofort gespeichert."),
        tabelle_editor,
        mo.hstack([btn_reset], justify="end"),
        mo.md("---"),
        file_uploader
    ])
    return file_uploader, tabelle_editor


@app.cell
def _(
    BytesIO,
    CONFIG_FILE,
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

    # --- 1. RÜCKUMWANDLUNG & SPEICHERN ---
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

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f_write:
            json.dump(usk_struktur, f_write, indent=4)
    except Exception as e:
        log_messages.append(f"❌ Warnung: Konnte Config nicht speichern: {e}")

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

    # --- EMAIL GENERATOR ---
    fehler_text = "\n".join([msg for msg in log_messages if "❌" in msg or "⚠️" in msg])
    if not fehler_text:
        fehler_text = "Keine offensichtlichen Fehler im Protokoll."

    dateien_hinweis = ""
    if problematische_dateien:
        dateien_liste = ", ".join(problematische_dateien)
        dateien_hinweis = f"Dateien: {dateien_liste}"

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

    params = {
        "subject": "Invoice Parser Web Anfrage",
        "body": email_body
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote) 
    mailto_link = f"mailto:hotline@worms.de?{query_string}"

    email_button = mo.Html(f"""
        <div style="margin-top: 20px; text-align: right;">
            <a href="{mailto_link}" class="email-btn">
                📧 Fehler melden (Email öffnen)
            </a>
        </div>
    """)

    # Ausgabe
    if processed_files or log_messages:
        # 1. Protokoll
        ergebnis_anzeige.append(mo.md("**Verarbeitungsprotokoll:**\n" + "\n".join([f"* {msg}" for msg in log_messages])))
    
        # 2. Email Button
        ergebnis_anzeige.append(email_button)
    
        # 3. DOWNLOAD BEREICH
        if processed_files:
            # Hier berechnen wir die Zahlen für die Anzeige
            anzahl_erfolg = len(processed_files)
            anzahl_gesamt = len(file_uploader.value)
            status_text = f"{anzahl_erfolg}/{anzahl_gesamt} Dateien wurden erfolgreich konvertiert."
        
            if len(processed_files) == 1:
                dl_obj = mo.download(
                    data=processed_files[0]["content"],
                    filename=processed_files[0]["name"],
                    label=f"Download {processed_files[0]['name']}"
                )
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for p_file in processed_files:
                        zip_file.writestr(p_file["name"], p_file["content"])
                dl_obj = mo.download(
                    data=zip_buffer.getvalue(),
                    filename="rechnungen_export.zip",
                    label=f"Download alle ({len(processed_files)} Dateien) als ZIP"
                )

            # Grüne Success-Box
            success_box = mo.callout(
                mo.vstack([
                    mo.md(f"### 🎉 Fertig!\n**{status_text}**"), # Hier nutzen wir den neuen Text
                    dl_obj
                ]),
                kind="success"
            )
            ergebnis_anzeige.append(success_box)

    mo.vstack(ergebnis_anzeige)
    return


if __name__ == "__main__":
    app.run()

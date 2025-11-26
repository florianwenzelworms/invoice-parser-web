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

    # Standard-Fallback
    default_fallback = {
        "Allgemein": {"xSta": "05000.10000"},
        "hsh.olav": {"FueZ": "11310.10010"}
    }

    # --- STATISCHE HELPER (Die sich nicht ändern) ---

    def load_json(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_fallback

    def flatten_data(data):
        flat_list = []
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    flat_list.append({"Gruppe": key, "Name": sub_key, "USK": sub_val})
            else:
                flat_list.append({"Gruppe": "BASIS", "Name": key, "USK": value})
        return flat_list
    return (
        CONFIG_DIR,
        CURRENT_CONFIG_FILE,
        Invoice,
        datetime,
        default_fallback,
        flatten_data,
        glob,
        json,
        load_json,
        mo,
        os,
        pd,
    )


@app.cell
def _(
    CONFIG_DIR,
    CURRENT_CONFIG_FILE,
    datetime,
    default_fallback,
    flatten_data,
    glob,
    json,
    load_json,
    mo,
    os,
):
    # --- STATE MANAGEMENT ---
    get_update_trigger, set_update_trigger = mo.state(0)
    get_status_msg, set_status_msg = mo.state("")

    # --- REAKTIVER HELPER ---
    # Dieser muss HIER sein, weil er auf 'get_update_trigger' zugreift
    def get_saved_configs():
        """Liest alle Backups aus dem Ordner"""
        # Trigger lesen -> Liste aktualisiert sich bei Änderungen
        _ = get_update_trigger()

        files = glob.glob(os.path.join(CONFIG_DIR, "config_*.json"))
        files.sort(key=os.path.getmtime, reverse=True)

        options = {}
        for f in files:
            try:
                name = os.path.basename(f)
                parts = name.replace("config_", "").replace(".json", "").split("_")
                date_part = parts[0]
                time_part = parts[1].replace("-", ":")
                rows_part = parts[2].replace("rows", "")

                dt_obj = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                pretty_date = dt_obj.strftime("%d.%m.%Y um %H:%M Uhr")

                label = f"📅 {pretty_date} ({rows_part} Einträge)"
                options[label] = f
            except:
                continue
        return options

    # --- ACTION HANDLER ---

    def action_save_backup():
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(CURRENT_CONFIG_FILE):
                data = load_json(CURRENT_CONFIG_FILE) # Nutzt Funktion aus Zelle 1
            else:
                data = default_fallback

            row_count = len(flatten_data(data)) # Nutzt Funktion aus Zelle 1
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"config_{timestamp}_{row_count}rows.json"
            fpath = os.path.join(CONFIG_DIR, fname)

            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            set_status_msg(f"✅ Backup erstellt: {fname}")
            set_update_trigger(get_update_trigger() + 1)

        except Exception as e:
            set_status_msg(f"❌ Fehler beim Backup: {e}")

    def action_load_backup():
        # ACHTUNG: Wir müssen hier auf 'dd_backups' zugreifen.
        # Da dd_backups erst in Zelle 2b definiert wird, greifen wir
        # hier noch nicht darauf zu, sondern erst beim Klick (Lambda).
        # Das wird durch die Reihenfolge im Notebook gelöst.
        pass 

    # Wir definieren die Load-Logik direkt im Button-Lambda oder in einer Funktion,
    # die Zugriff auf dd_backups hat. Um Zirkelbezüge zu vermeiden,
    # lagern wir die Logik für LOAD in Zelle 2b aus oder übergeben den Wert.
    # Einfacher Trick: Wir definieren die Funktion HIER, aber holen den Wert erst zur Laufzeit.

    # --- BUTTONS ---
    btn_save_version = mo.ui.button(
        label="💾 Als Backup speichern", 
        on_click=lambda _: action_save_backup(),
        kind="neutral"
    )

    # Den Load Button definieren wir hier, aber die Logik bauen wir gleich
    # zusammen mit dem Dropdown in Zelle 2b, um den Zugriff sicherzustellen.
    btn_load_backup = mo.ui.button(
        label="📂 Laden & Aktivieren",
        kind="warn"
    )
    return (
        btn_save_version,
        get_saved_configs,
        get_status_msg,
        get_update_trigger,
        set_status_msg,
        set_update_trigger,
    )


@app.cell
def _(
    CURRENT_CONFIG_FILE,
    get_saved_configs,
    get_update_trigger,
    json,
    load_json,
    mo,
    os,
    set_status_msg,
    set_update_trigger,
):
    # --- DROPDOWN ---
    backup_options = get_saved_configs()
    dd_backups = mo.ui.dropdown(
        options=backup_options,
        label="Wiederherstellen aus Archiv:",
        full_width=True
    )

    # --- LOAD ACTION ---
    # Wir definieren die Load-Funktion HIER, wo das Dropdown bekannt ist
    def run_load_action():
        selected_file = dd_backups.value

        if selected_file and os.path.exists(selected_file):
            try:
                data = load_json(selected_file)
                with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                set_status_msg(f"♻️ Erfolgreich geladen: {os.path.basename(selected_file)}")
                set_update_trigger(get_update_trigger() + 1)
            except Exception as e:
                set_status_msg(f"❌ Fehler beim Laden: {e}")
        else:
            set_status_msg("⚠️ Bitte erst eine Datei auswählen.")

    # Wir verknüpfen den Button aus Zelle 2a nachträglich mit dieser Funktion?
    # Nein, das geht in Marimo nicht gut rückwärts.
    # BESSER: Wir erstellen den Load-Button einfach HIER in Zelle 2b neu,
    # dann kennt er das Dropdown.
    # (Den btn_load_backup in Zelle 2a kannst du ignorieren oder löschen)

    btn_load_real = mo.ui.button(
        label="📂 Laden & Aktivieren",
        on_click=lambda _: run_load_action(),
        kind="warn"
    )
    return btn_load_real, dd_backups


@app.cell
def _(
    CURRENT_CONFIG_FILE,
    btn_load_real,
    btn_save_version,
    dd_backups,
    default_fallback,
    flatten_data,
    get_status_msg,
    get_update_trigger,
    load_json,
    mo,
    os,
    pd,
):
    # ... (Anfang gleich wie vorher) ...
    _ = get_update_trigger()

    if os.path.exists(CURRENT_CONFIG_FILE):
        current_data = load_json(CURRENT_CONFIG_FILE)
    else:
        current_data = default_fallback

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

    status_msg = get_status_msg()

    styles = mo.Html("""
        <style>
            #marimo-header button[aria-label='App menu'], header button[aria-label='App menu'] { display: none !important; }
            .email-btn { display: inline-block; padding: 0.5rem 1rem; background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; border-radius: 0.375rem; text-decoration: none; font-weight: 600; }
            a[download] { display: inline-block; width: 100%; text-align: center; background-color: #16a34a !important; color: white !important; padding: 12px 20px; font-weight: bold; border-radius: 8px; text-decoration: none; }
        </style>
    """)

    backup_ui = mo.accordion({
        "⚙️ Konfigurationen verwalten (Laden / Speichern)": mo.vstack([
            mo.hstack([btn_save_version, mo.md(f"*{status_msg}*")]),
            mo.md("---"),
            # HIER NEU: btn_load_real verwenden
            mo.hstack([dd_backups, btn_load_real], align="end")
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
def _(CURRENT_CONFIG_FILE, Invoice, file_uploader, mo, tabelle_editor):
    # --- SICHERHEITS-IMPORTS (Lokal für diese Zelle) ---
    # Wir nutzen Unterstriche (_), damit Marimo nicht meckert.
    import os as _os
    import json as _json
    import tempfile as _tempfile
    import logging as _logging
    import urllib.parse as _urllib_parse
    from io import BytesIO as _BytesIO
    import zipfile as _zipfile
    import traceback as _traceback

    # Globale Listen für den Output
    ergebnis_anzeige = []

    try:
        # --- PRÜFUNG: Ist 'Invoice' da? ---
        # Wir importieren es NICHT neu, um den Marimo-Fehler zu vermeiden.
        # Wir prüfen nur, ob es existiert.
        if 'Invoice' not in globals():
            raise Exception("Die Klasse 'Invoice' wurde nicht gefunden. Bitte lade die Seite neu (Strg + F5), damit Zelle 1 geladen wird.")

        processed_files = []
        log_messages = []
        problematische_dateien = []

        # --- 1. DATEN VORBEREITEN ---
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

        usk_json_string = _json.dumps(usk_struktur, indent=4)

        # --- 2. AUTO-SAVE LOGIK ---
        try:
            _os.makedirs(_os.path.dirname(CURRENT_CONFIG_FILE), exist_ok=True)
            with open(CURRENT_CONFIG_FILE, "w", encoding="utf-8") as f_write:
                _json.dump(usk_struktur, f_write, indent=4)
        except Exception as e:
            log_messages.append(f"❌ Warnung: Auto-Save fehlgeschlagen: {e}")

        # --- 3. DATEI VERARBEITUNG ---
        if file_uploader.value:
            logger = _logging.getLogger("Invoice Parser")
            logger.handlers = []
            logger.addHandler(_logging.NullHandler())
            logger.propagate = False

            with _tempfile.TemporaryDirectory() as temp_dir:
                src_path = _os.path.join(temp_dir, "input") + _os.sep
                dest_path = _os.path.join(temp_dir, "output") + _os.sep
                _os.makedirs(src_path, exist_ok=True)
                _os.makedirs(dest_path, exist_ok=True)

                for file_obj in file_uploader.value:
                    file_path = _os.path.join(src_path, file_obj.name)
                    with open(file_path, "wb") as f_up:
                        f_up.write(file_obj.contents)

                fake_config = {
                    "files": {"source_path": src_path, "destination_path": dest_path},
                    "usk": {"usk_liste": usk_json_string}
                }

                files_in_temp = _os.listdir(src_path)
                for filename in files_in_temp:
                    try:
                        # Hier nutzen wir das globale 'Invoice' aus Zelle 1
                        invoice_processor = Invoice(filename, fake_config)
                        created_file_path = invoice_processor.create_file()
                    
                        if _os.path.exists(created_file_path):
                            with open(created_file_path, "rb") as f_res:
                                processed_files.append({
                                    "name": _os.path.basename(created_file_path),
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

        # --- 4. EMAIL & AUSGABE BAUEN ---
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
        query_string = _urllib_parse.urlencode(params, quote_via=_urllib_parse.quote) 
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
                    dl_obj = mo.download(processed_files[0]["content"], filename=processed_files[0]["name"], label=f"Download {processed_files[0]["name"]}")
                else:
                    zip_buffer = _BytesIO()
                    with _zipfile.ZipFile(zip_buffer, "w", _zipfile.ZIP_DEFLATED) as zip_file:
                        for p_file in processed_files:
                            zip_file.writestr(p_file["name"], p_file["content"])
                    dl_obj = mo.download(zip_buffer.getvalue(), filename="rechnungen_export.zip", label=f"Download alle ({len(processed_files)} Dateien) als ZIP")

                ergebnis_anzeige.append(mo.callout(mo.vstack([mo.md(f"### 🎉 Fertig!\n**{status_text}**"), dl_obj]), kind="success"))

    except Exception as e_critical:
        # --- CRASH HANDLER ---
        err_trace = _traceback.format_exc()
        ergebnis_anzeige.append(mo.callout(mo.md(f"## 🔥 KRITISCHER FEHLER\n\n`{str(e_critical)}`\n\n**Details:**\n```\n{err_trace}\n```"), kind="danger"))

    # Ausgabe
    mo.vstack(ergebnis_anzeige)
    return


if __name__ == "__main__":
    app.run()

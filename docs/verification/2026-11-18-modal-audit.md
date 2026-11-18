# Modal-Liveprüfung – 18.11.2026

**Nachtrag:** Der hier beschriebene anonyme Zugriff wurde anschließend geschlossen. Alle fünf Apps verlangen jetzt Modal-Proxy-Authentifizierung; anonyme und falsche Zugangsdaten wurden live mit HTTP 401 abgewiesen. Aktueller Betriebsstand: [Privater Modus](../PRIVATE_MODE.md). Dieser Bericht bleibt als Nachweis der vorherigen Funktionsprüfung erhalten.

## Ergebnis

Die fünf Hauptdienste im Modal-Workspace `aliundmaggy` sind erreichbar und haben jeweils einen echten Verarbeitungsauftrag einschließlich Ergebnisdownload erfolgreich abgeschlossen. Alle fünf `/health`-Routen lieferten HTTP 200. Prüfung ab 09:49 UTC / 10:49 Uhr MEZ.

Repository: `dreamtelligence/XO-master`, lokaler Ausgangsstand und `origin/main`: `19b8cf373daf5a122da52ada6869f398873141b9`. Keine Änderungen an Anwendungscode, Konfiguration, Secrets oder Deployments; dieser Bericht dokumentiert die Prüfung.

| Dienst / Modal-App | Live-Ergebnis | Gesamtdauer* | Job-ID |
| --- | --- | --- | --- |
| Stem-Trennung / `music-ai-separator-zfturbo-complete` | Gesang, Drums, Bass, Other und Instrumental als WAV; ZIP gültig; alle fünf MP3-Vorschauen HTTP 200 | 100,78 s | `097f8eeb-12e9-49c3-a2ff-40dc79b26e12` |
| Mastering / `matchering-ai-mastering` | WAV in 16 und 24 Bit; ZIP gültig | 43,73 s | `5a8b07f1-dc81-410e-af8a-defdc0d2daa2` |
| Musik-Transkription / `music-ai-transcription-complete` | Melodie, Drums, Akkorde und Beat erfolgreich; `failed_tasks={}`; 14 Dateien einschließlich MIDI/JSON/Text; ZIP gültig; MIDI-Audiovorschau HTTP 200 | 49,03 s | `31edd6f0-1ca7-43f8-adcd-9cab2ffbc5b3` |
| Sprachverbesserung / `audio-enhancement-complete` | Verbessertes WAV und Vorschau; MossFormer2, Whisper und AST laut Cloud-Logs geladen; Verarbeitung meldet keinen Modell-Fallback | 68,36 s | `cea67e13-e0ac-4cb6-b8ac-6cca44b344f9` |
| Text-to-Audio / `audio-generation-stable-audio-open` | Stable Audio Open erzeugte zwei Sekunden Stereo-WAV | 26,61 s | `2830b879-1ad3-454a-8f7e-b8ffd986cebf` |

\* Einschließlich HTTP-Anfragen, gegebenenfalls Containerstart, Statusabfragen und Downloads; einzelne parallele Kurztests, kein Leistungsbenchmark. Vorschauprüfungen erfolgten anschließend.

## Testumfang und Belege

- Ein synthetischer achtsekündiger Stereo-Musikclip mit Akkorden, Kick und Hi-Hat bei 120 BPM für Trennung, Mastering und Transkription. Keine privaten Audiodaten. Die Beat-Analyse meldete 120 BPM.
- Ein ungefähr sechssekündiger, lokal synthetisierter Sprachclip für Enhancement. Optionen: Rauschunterdrückung, Normalisierung, Füllwortentfernung, Stille kürzen, Husten-/Klickerkennung, Qualitätsbearbeitung und Zielwert −16 LUFS. Das Verarbeitungsprotokoll bestätigt diese Schritte; es wurden null Husten-/Klicksegmente erkannt.
- Text-to-Audio: „A clean isolated electronic drum rhythm, dry studio recording.“, zwei Sekunden, zehn Inferenzschritte, Seed `20261118`, WAV.
- Je Dienst: Health → Auftrag anlegen → Status bis `completed` → sämtliche gemeldeten Dateien herunterladen. ZIPs für Trennung, Mastering und Transkription vollständig auf CRC-Fehler geprüft.
- Zehn WAV-Dateien auf RIFF/WAVE-Struktur, Sampleformat, Länge und vorhandene Audiodaten geprüft; Float-WAVs zusätzlich auf NaN/Infinity geprüft. MIDI-Header und JSON-Syntax geprüft. MP3-Vorschauen anhand MIME-Typ und Dateikennung geprüft.
- Modal-App-Liste, Deployment-Historien, benötigte Volumes und Existenz des Hugging-Face-Secrets geprüft. Modellzugriff zusätzlich durch tatsächliche Inferenz bestätigt. Keine Secret-Werte ausgelesen oder dokumentiert.
- Lokale Rohbelege und Testdateien: `/tmp/xo-modal-audit-20261118/` (`results.json`, `previews.json`, `signal-checks.json`, `live.log`, Ergebnisdateien und Enhancement-Cloud-Log). Temporäre Dateien sind kein dauerhaftes Archiv.

## Betriebsstand und Auffälligkeiten

- Letzte gelistete Deployments der fünf Apps: 24.10.2026. Stem-Trennung Version 3, Mastering Version 1, Transkription Version 4, Enhancement Version 2, Generierung Version 1. Die Deployment-Metadaten nennen ältere Git-Stände mit Dirty-Markierung (`70876a0*` beziehungsweise `cbbd6a5*`). Damit ist keine Byte-Identität der Cloud-Deployments mit dem heutigen `main` nachgewiesen. Insbesondere ist ein Deployment der späteren Download-/SHA256-Korrektur nicht belegt.
- Der alte Endpoint `https://bucci369--music-ai-separator-enhanced-enhanced-fastapi-app.modal.run/health/enhanced` liefert HTTP 404. `index.html` deaktiviert diesen separaten Dienst bereits explizit (`isEnhancedMode=false`, `isEnhancedDeployed=false`). Das ist nicht der funktionierende Hauptdienst zur Stem-Trennung und nicht die funktionierende Sprachverbesserung.
- **Kosten-/Zugriffsrisiko:** Alle fünf Verarbeitungsaufträge wurden ohne Authorization-Header, API-Schlüssel, Cookies oder Zahlung angenommen und ausgeführt. Die öffentlichen HTTP-Endpunkte verlangen für diesen Pfad offenbar keinen serverseitigen Nutzernachweis. Wer die URLs kennt, kann damit potenziell Verarbeitungskosten auslösen. Ein Frontend-Zahlungsdialog allein schützt diesen Backend-Pfad nicht. Rate-Limits und Account-Spending-Limits wurden nicht auditiert.
- Enhancement-Logs enthalten Modal-Warnungen zu synchronen Volume-/Spawn-Aufrufen in asynchronen Handlern. Beim geprüften Auftrag entstand daraus kein Ausführungsfehler.

## Grenzen

Geprüft ist die technische Funktionsfähigkeit dieser fünf Kurzaufträge einschließlich Downloads und ausgewählter Vorschaupfade. Kein vollständiger Browser-/Bezahltest, kein Neuaufbau der Modal-Images, keine Last-/Langdateitests, keine Hörbewertung und keine Lizenzprüfung. Synthetische Clips belegen keine musikalische Ergebnisqualität mit realen Songs oder problematischen Sprachaufnahmen. API-Healthtexte und Qualitätsmetriken wurden nicht als unabhängige Qualitätsnachweise gewertet.

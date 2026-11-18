# Artist Workspace

Der Artist Workspace läuft lokal auf dem Mac. Die Bibliothek speichert Originale, Referenzen und gerenderte Varianten als eigene Assets. Projektentwürfe, Aufgaben und Ergebnisbezüge überleben einen Neustart. Die fünf Modell-Dienste werden mit der bestehenden privaten Modal-Konfiguration angesprochen.

## Installation und Start

Voraussetzungen sind Node, npm, uv und FFmpeg. Rubber Band wird für Tempo und Tonhöhe benötigt. Die geprüfte Umgebung verwendet Python 3.11.16, FFmpeg 9.0.1 und Rubber Band 4.0.0.

```sh
brew install ffmpeg rubberband
npm run setup
npm start
```

Öffne [den lokalen Arbeitsbereich](http://localhost:8765). Falls dort die vorherige Werkzeugansicht läuft, startet `npm start -- --port 8767` den Workspace daneben. Der explizite Legacy-Start ist `npm run legacy`. Für die Frontend-Entwicklung starten `npm run dev` und in einem zweiten Terminal `npm --prefix web run dev` die lokale API und den Vite-Server.

DeepFilterNet und RNNoise lassen sich auf Apple Silicon zusätzlich einrichten.

```sh
brew install automake libtool
npm run setup -- --speech
```

Das Skript prüft die Hashes der offiziellen Artefakte. Die ausführbaren Dateien liegen in `.venv/bin`. Der Workspace erkennt sie beim Start.

### Private Modell-Dienste

Die Einrichtung der fünf vorhandenen URLs und der privaten Proxy-Zugangsdaten ist unter [Privater Betrieb](PRIVATE_MODE.md) beschrieben. Im Workspace gehen die Aufträge über die lokale Projekt-API. Material wird für einen expliziten Cloud-Auftrag in hashgeprüften 4-MiB-Teilen übertragen. Entwicklungszugriffe erlauben nur den exakten lokalen Origin. Im Profil **Veröffentlichung** sind die Cloud-Modelle für diesen Stand gesperrt.

AudioSR Basic ist ein separates, optionales Experiment. Eine eigene geschützte Modal-URL unter `services.audiosr` aktiviert den Eintrag. Die Auswahl darf bis zu 15 Sekunden lang sein. AudioSR arbeitet in diesem Adapter in Mono bei 48 kHz und legt sein Ergebnis als Variante an. Setup und Abnahme stehen im [Prüfbericht](verification/2026-11-18-artist-workspace.md).

## Arbeitsabläufe

1. **Material laden.** Beim Start Dateien importieren oder eine Vorlage wählen. Referenzen über die Bibliothek hinzufügen. Die Vorlage legt die Reihenfolge im Projekt ab. Unter **Bearbeitungsfolge** kannst du Schritte verschieben und festlegen, welches Ergebnis der nächste Schritt verwendet. **Folge rendern** startet die konfigurierte Reihe.
2. **Ergebnis rendern.** Asset auswählen und das Werkzeug im Inspektor öffnen. Mehrere zugehörige Stems können gemeinsam markiert werden. Jobs und Ergebnisdateien erscheinen unten unter **Aufgaben**.
3. **Hören und korrigieren.** Einen Ausschnitt mit der Wellenform oder den Zeitfeldern setzen. Einen Treffer oder eine bestätigte Schnittstelle zur Liste hinzufügen, anhören und bei Bedarf durch die aktuelle Auswahl ersetzen. A/B nutzt die Quellkennung sowie gegebenenfalls das Schnitt- oder Stretch-Mapping. Für den Pegelabgleich zuerst beide Seiten auf LUFS prüfen.
4. **DAW-Paket ausgeben.** Assets im Exportkorb sammeln, Format und Zeitbasis wählen und das ZIP aus der Aufgabenliste laden. Das Manifest enthält Quellbezüge sowie Messwerte der tatsächlich encodierten Dateien. Referenzdateien werden nur in Projektpaketen mitgesichert.
5. **Projekt sichern.** Im Exportkorb ein Projektpaket anlegen. In der Projektübersicht lässt es sich als eigenes Projekt wiederherstellen. Abgeleitete Assets behalten ihre eigenen Quellbezüge und den Render-Snapshot. Die SQLite-Aufgabenhistorie ist Bestandteil eines vollständigen Datenverzeichnis-Backups.

## Daten und Rollback

Standardpfad ist `~/Library/Application Support/Dreamtelligence XO/` mit SQLite-Katalog, Blob- und Hörkopienspeicher. Ein anderer Pfad lässt sich mit `npm start -- --data /absoluter/pfad` verwenden. Ein Projektpaket enthält ausgewählte Projektdateien und Metadaten. Für eine vollständige Sicherung den Workspace beenden und das gesamte private Datenverzeichnis kopieren. Eine ältere Workspace-Version benötigt gegebenenfalls das beim Schemawechsel angelegte SQLite-Backup.

Im Projektmenü lässt sich das Budget einsehen und der Cache für Hörkopien leeren. Der Exportpfad prüft die gemeinsame Zeitbasis sowie True Peak und gegebenenfalls den LUFS-Zielbereich. Für Offline-Wiederaufnahme eines Cloud-Auftrags ist in der Aufgabenliste **Cloud-Status prüfen** verfügbar, wenn die Auftragsreferenz vorliegt. Diese Aktion verwendet die gespeicherte ID.

Die geschützte Altansicht ist unabhängig von der lokalen SQLite-Migration. Cloud-Rollback nur auf eine nachweislich geschützte Version, beispielsweise die vorherige Version mit Tag `private-20261118`. Die neue Oberfläche wird lokal gebaut. Sie hat keinen Rechenproxy in der öffentlichen Vercel-Konfiguration.

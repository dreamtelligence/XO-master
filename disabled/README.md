# Deaktivierte Bestandteile

- `commerce/api/`: ursprüngliche Stripe-, Webhook-, Credit- und Paywall-Handler, unverändert erhalten. Die aktiven Gegenstücke unter `api/` liefern ausschließlich HTTP 410; die archivierten Dateien werden nicht als Vercel-Funktionen gebaut.
- `marketing/service-cards.html`: bisherige werbliche Service-Kacheln.
- `README.legacy.md`: frühere Produktdarstellung und Betriebsanleitung; historische Aussagen sind nicht als aktueller Status zu verstehen.
- `index.html`: alte Navigation, Auth-Dialoge, Hero, Vorteile, Ablauf, Preise, Footer, SDK-Tags und Marketing-Metadaten bleiben in inaktiven `<template data-disabled="…">`-Blöcken erhalten. Strukturierte Angebotsdaten haben einen inaktiven Script-Typ.
- Alte Zahlungs-/Kontofunktionen bleiben im JavaScript erhalten. `COMMERCE_ENABLED` und `ACCOUNTS_ENABLED` sind `false`; SDKs werden nicht geladen, Credit-Gates und Nutzungsprotokollierung laufen nicht.

Ein einzelner Frontend-Schalter aktiviert keinen verlässlichen Bezahlbetrieb. Vor einer Wiederaktivierung müssen Backend-Autorisierung, Checkout/Webhooks, Credits und Verträge zusammen geprüft und bewusst veröffentlicht werden. Der private Modal-Schutz darf dafür nicht entfernt werden.

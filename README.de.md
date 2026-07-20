<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="HAIR-Banner" width="900" />
</p>

# HAIR

**HAIR holt deine IR-Codes aus Hersteller-Clouds, Blaster-Speichern und Konfigurationsdateien heraus und bringt sie in Home Assistant hinein.**

Richte irgendeine Fernbedienung auf einen IR-Empfänger, drücke eine Taste, und HAIR macht aus diesem Signal etwas, womit Home Assistant wirklich arbeiten kann: eine Taste auf jedem Dashboard, einen Auslöser für deine Automationen, einen Befehl, den du über jeden Blaster auf HAs nativer Infrarot-Plattform senden kannst. Kein YAML, keine Hersteller-Apps, keine Code-Downloads.

## Fünf Wege, deine Codes hineinzubekommen

- **Schnüffle ihn.** Drücke eine Taste auf einer echten Fernbedienung und HAIR fängt sie live aus der Luft ein, nimmt ihren Fingerabdruck und gruppiert sie nach Fernbedienung.
- **Konvertiere ihn.** Füge bekannte IR-Codes ein, oder fülle eine ganze Fernbedienung aus der installierten Code-Bibliothek vor, indem du Hersteller und Modell wählst.
- **Zieh ihn.** Hole Codes, die bereits in einem Hersteller-Blaster gelernt sind (etwa Tuya Local), ohne einen einzigen am Empfänger neu zu lernen.
- **Belausche ihn.** Jeder über Home Assistant gesendete IR-Befehl erscheint im Mirror, gehört oder nicht, einen Klick davon entfernt, dein eigener Befehl zu werden.
- **Setz sie auf.** Lege eine Code-Datei im Schrank ab -- eine geteilte Perücke, ein SmartIR-JSON, eine Flipper-Zero-`.ir`, eine LIRC-Konfiguration oder ein Girr-Export aus IrScrutinizer -- und sie hängt bei deiner Sammlung, einen Klick von einer funktionierenden Fernbedienung entfernt.

## Was du damit machst

- **Erstelle Geräte.** Baue ein Profil für deinen Fernseher, deine Klimaanlage, deinen Ventilator, dein Licht, deinen Schalter oder dein Rollo, weise ihm eingefangene Signale als Befehle zu, und HAIR erstellt automatisch die passenden nativen Entitäten: einen echten Medienplayer für den Fernseher, eine echte Klima-Entität für die Klimaanlage mit Modi und Temperatur-Voreinstellungen, einen Ventilator mit Geschwindigkeitsregelung. Sie funktionieren in Dashboards, Skripten und Sprachassistenten wie jedes andere Home-Assistant-Gerät.
- **Mach Fernbedienungstasten zu Auslösern.** Jede Taste jeder physischen Fernbedienung kann deine Automationen starten. Drücke die rote Taste der alten TV-Fernbedienung, um deine Kinoabend-Szene zu starten. Auslöser wissen, welcher Raum den Tastendruck gehört hat, dieselbe Fernbedienung kann also in verschiedenen Räumen Verschiedenes tun. Keine andere Integration kann das.
- **Schau in den Mirror.** Ein Live-Protokoll von allem, was dein Haus sendet: welcher Befehl rausging, über welchen Blaster, und welcher Empfänger ihn zurückgehört hat. Wenn sich um 2 Uhr nachts irgendetwas Infrarotes danebenbenimmt, hat der Mirror es gesehen.
- **Teste und poliere alles.** Sende jedes Signal über jeden Blaster, um es zu prüfen, bevor du ihm vertraust, gib Signalen Spitznamen, bearbeite einen Pronto-Code direkt, und lass HAIR erkannte Protokolle dekodieren (NEC, Sony, RC-5, Samsung und mehr) für eine sauberere Übertragung.

Das Panel spricht deine Sprache. Englisch, Spanisch, Französisch, Japanisch, Deutsch, Polnisch, Portugiesisch, Niederländisch, Italienisch und Russisch, automatisch nach der Sprache deines Home-Assistant-Profils.

> [!IMPORTANT]
> Diese Übersetzung des HAIR-Panels wurde von einem Programmier-Assistenten entworfen und wartet auf die Durchsicht eines Muttersprachlers. Falls das du sein könntest: eine Durchsicht passt in einen einzigen Pull Request, und dein Name kommt in die Datei. Starte hier: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Installation

1. Füge `https://github.com/DAB-LABS/HAIR` in HACS als benutzerdefiniertes Repository hinzu (Kategorie: Integration)
2. Installiere HAIR, starte Home Assistant neu und füge die Integration unter Einstellungen, dann Geräte und Dienste hinzu

Benötigt Home Assistant 2026.4 oder neuer; 2026.6+ empfohlen für native IR-Empfänger.

## Vollständige Dokumentation

Das komplette README, mit Setup-YAML, unterstützter Hardware, Funktionsanleitungen und Screenshots, gibt es auf Englisch:

**[Zur vollständigen Dokumentation](README.md)**

---

*Übersetzt aus dem englischen README, Stand v0.7.1. Diese Datei wurde von einem Programmier-Assistenten entworfen und wird mit jeder Version aufgefrischt. Muttersprachler sind herzlich eingeladen, sie zu übernehmen; siehe [Adding a language](CONTRIBUTING.md#adding-a-language).*

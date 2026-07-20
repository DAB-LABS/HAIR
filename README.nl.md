<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="HAIR-banner" width="900" />
</p>

# HAIR

**HAIR haalt je IR-codes uit fabrikanten-clouds, blaster-geheugens en configuratiebestanden, en brengt ze naar Home Assistant zelf.**

Richt een willekeurige afstandsbediening op een IR-ontvanger, druk op een knop, en HAIR maakt van dat signaal iets waar Home Assistant echt mee kan werken: een knop op elk dashboard, een trigger voor je automatiseringen, een commando dat je door elke blaster op HA's native infraroodplatform kunt sturen. Geen YAML, geen fabrikanten-apps, geen codebestanden downloaden.

## Vier manieren om je codes binnen te krijgen

- **Snuif hem op.** Druk op een knop van een echte afstandsbediening en HAIR vangt hem live uit de lucht, neemt zijn vingerafdruk en groepeert hem per afstandsbediening.
- **Converteer hem.** Plak bekende IR-codes, of vul een hele afstandsbediening vooraf in vanuit de geïnstalleerde codebibliotheek door fabrikant en model te kiezen.
- **Pluk hem.** Haal codes op die al in een fabrikanten-blaster zijn geleerd (zoals Tuya Local) zonder er ook maar één opnieuw te leren bij de ontvanger.
- **Luister hem af.** Elk IR-commando dat via Home Assistant wordt verzonden verschijnt in de Mirror, teruggehoord of niet, één klik verwijderd van een eigen commando worden.

## Wat je ermee doet

- **Maak apparaten.** Bouw een profiel voor je tv, airco, ventilator, lamp, schakelaar of scherm, wijs er gevangen signalen als commando's aan toe, en HAIR maakt automatisch de bijpassende native entiteiten: een echte mediaspeler voor de tv, een echte klimaat-entiteit voor de airco met modi en temperatuurpresets, een ventilator met snelheidsregeling. Ze werken in dashboards, scripts en spraakassistenten zoals elk ander Home Assistant-apparaat.
- **Maak van afstandsbedieningsknoppen triggers.** Elke knop van elke fysieke afstandsbediening kan je automatiseringen starten. Druk op de rode knop van de oude tv-afstandsbediening om je filmavond-scène te starten. Triggers weten welke kamer de druk hoorde, dus dezelfde afstandsbediening kan in verschillende kamers verschillende dingen doen. Geen enkele andere integratie doet dit.
- **Kijk in de Mirror.** Een live audit van alles wat je huis uitzendt: welk commando eruit ging, door welke blaster, en welke ontvanger het terughoorde. Als iets infraroods zich om 2 uur 's nachts misdraagt, heeft de Mirror het gezien.
- **Test en polijst alles.** Vuur elk signaal door elke blaster om het te controleren voordat je erop vertrouwt, geef signalen bijnamen, bewerk een Pronto-code ter plekke, en laat HAIR herkende protocollen decoderen (NEC, Sony, RC-5, Samsung en meer) voor schonere overdracht.

Het paneel spreekt jouw taal. Engels, Spaans, Frans, Japans, Duits, Pools, Portugees, Nederlands, Italiaans en Russisch, automatisch volgens de taal van je Home Assistant-profiel.

> [!IMPORTANT]
> Deze vertaling van het HAIR-paneel is opgesteld door een programmeerassistent en wacht op de controle van een moedertaalspreker. Als jij dat zou kunnen zijn: een controle past in één pull request en jouw naam komt in het bestand. Begin hier: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Installatie

1. Voeg `https://github.com/DAB-LABS/HAIR` toe aan HACS als aangepaste repository (categorie: Integration)
2. Installeer HAIR, herstart Home Assistant en voeg de integratie toe onder Instellingen, dan Apparaten en diensten

Vereist Home Assistant 2026.4 of nieuwer; 2026.6+ aanbevolen voor native IR-ontvangers.

## Volledige documentatie

De complete README, met setup-YAML, ondersteunde hardware, functiegidsen en screenshots, is in het Engels:

**[Lees de volledige documentatie](README.md)**

---

*Vertaald uit de Engelse README, stand v0.6.8. Dit bestand is opgesteld door een programmeerassistent en wordt bij elke release ververst. Moedertaalsprekers zijn welkom om het over te nemen; zie [Adding a language](CONTRIBUTING.md#adding-a-language).*

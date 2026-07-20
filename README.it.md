<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="Banner di HAIR" width="900" />
</p>

# HAIR

**HAIR tira fuori i tuoi codici IR dai cloud dei produttori, dalla memoria dei trasmettitori e dai file di configurazione, e li porta dentro Home Assistant.**

Punta un telecomando qualsiasi verso un ricevitore IR, premi un tasto, e HAIR trasforma quel segnale in qualcosa che Home Assistant sa davvero usare: un pulsante su qualsiasi dashboard, un trigger per le tue automazioni, un comando da inviare attraverso qualsiasi trasmettitore della piattaforma a infrarossi nativa di HA. Niente YAML, niente app dei produttori, niente file di codici da scaricare.

## Quattro modi per far entrare i tuoi codici

- **Annusalo.** Premi un tasto di un telecomando vero e HAIR lo cattura dal vivo nell'aria, ne prende l'impronta e lo raggruppa per telecomando.
- **Convertilo.** Incolla codici IR conosciuti, oppure precompila un telecomando intero dalla libreria di codici installata scegliendo produttore e modello.
- **Estrailo.** Recupera i codici già appresi in un trasmettitore di un produttore (come Tuya Local) senza riapprenderne nemmeno uno al ricevitore.
- **Origlialo.** Ogni comando IR inviato attraverso Home Assistant appare nel Mirror, sentito di ritorno o no, a un clic dal diventare un comando tuo.

## Cosa ci fai

- **Crea dispositivi.** Costruisci un profilo per la tua TV, condizionatore, ventilatore, luce, interruttore o schermo, assegnagli i segnali catturati come comandi, e HAIR crea automaticamente le entità native corrispondenti: un vero lettore multimediale per la TV, una vera entità clima per il condizionatore con modalità e preset di temperatura, un ventilatore con controllo della velocità. Funzionano in dashboard, script e assistenti vocali come qualsiasi altro dispositivo Home Assistant.
- **Trasforma i tasti del telecomando in trigger.** Qualsiasi tasto di qualsiasi telecomando fisico può far partire le tue automazioni. Premi il tasto rosso del vecchio telecomando della TV per avviare la scena serata cinema. I trigger sanno quale stanza ha sentito la pressione, quindi lo stesso telecomando può fare cose diverse in stanze diverse. Nessun'altra integrazione lo fa.
- **Guarda il Mirror.** Un audit dal vivo di tutto ciò che la tua casa trasmette: quale comando è uscito, da quale trasmettitore, e quale ricevitore lo ha sentito di ritorno. Se qualcosa a infrarossi si comporta male alle 2 di notte, il Mirror l'ha visto.
- **Prova e rifinisci tutto.** Spara qualsiasi segnale da qualsiasi trasmettitore per verificarlo prima di fidarti, dai soprannomi ai segnali, modifica un codice Pronto sul posto, e lascia che HAIR decodifichi i protocolli riconosciuti (NEC, Sony, RC-5, Samsung e altri) per una trasmissione più pulita.

Il pannello parla la tua lingua. Inglese, spagnolo, francese, giapponese, tedesco, polacco, portoghese, olandese, italiano e russo, seguendo automaticamente la lingua del tuo profilo Home Assistant.

> [!IMPORTANT]
> Questa traduzione del pannello HAIR è stata redatta da un assistente di programmazione e attende la revisione di un madrelingua. Se quella persona potessi essere tu: una revisione sta in una sola pull request e il tuo nome finisce nel file. Comincia qui: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Installazione

1. Aggiungi `https://github.com/DAB-LABS/HAIR` a HACS come repository personalizzato (categoria: Integration)
2. Installa HAIR, riavvia Home Assistant e aggiungi l'integrazione in Impostazioni, poi Dispositivi e servizi

Richiede Home Assistant 2026.4 o successivo; consigliato 2026.6+ per i ricevitori IR nativi.

## Documentazione completa

Il README completo, con YAML di configurazione, hardware supportato, guide alle funzionalità e screenshot, è in inglese:

**[Leggi la documentazione completa](README.md)**

---

*Tradotto dal README inglese, versione v0.6.9. Questo file è stato redatto da un assistente di programmazione e viene aggiornato a ogni release. I madrelingua sono i benvenuti a prendersene cura; vedi [Adding a language](CONTRIBUTING.md#adding-a-language).*

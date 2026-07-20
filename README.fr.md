<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="Bannière HAIR" width="900" />
</p>

# HAIR

**HAIR sort vos codes IR des clouds des fabricants, de la mémoire des blasters et des fichiers de configuration, pour les faire entrer dans Home Assistant.**

Pointez n'importe quelle télécommande vers un récepteur IR, appuyez sur un bouton, et HAIR transforme ce signal en quelque chose que Home Assistant sait vraiment utiliser : un bouton sur n'importe quel tableau de bord, un déclencheur pour vos automatisations, une commande à envoyer par n'importe quel blaster de la plateforme infrarouge native de HA. Pas de YAML, pas d'applications de fabricants, pas de fichiers de codes à télécharger.

## Quatre façons de faire entrer vos codes

- **Sniffez-le.** Appuyez sur un bouton d'une vraie télécommande : HAIR le capture en direct dans l'air, relève son empreinte et le regroupe par télécommande.
- **Convertissez-le.** Collez des codes IR connus, ou préremplissez une télécommande entière depuis la bibliothèque de codes installée en choisissant un fabricant et un modèle.
- **Cueillez-le.** Récupérez les codes déjà appris dans un blaster de fabricant (comme Tuya Local) sans en réapprendre un seul au récepteur.
- **Surprenez-le.** Chaque commande IR envoyée via Home Assistant apparaît dans le Mirror, entendue ou non, à un clic de devenir une commande à vous.

## Ce que vous en faites

- **Créez des appareils.** Construisez un profil pour votre TV, climatiseur, ventilateur, lumière, interrupteur ou écran, assignez-lui des signaux capturés comme commandes, et HAIR crée automatiquement les entités natives correspondantes : un vrai lecteur multimédia pour la TV, une vraie entité climat pour le climatiseur avec modes et préréglages de température, un ventilateur avec contrôle de vitesse. Elles fonctionnent dans les tableaux de bord, les scripts et les assistants vocaux comme n'importe quel appareil Home Assistant.
- **Transformez les boutons de télécommande en déclencheurs.** N'importe quel bouton de n'importe quelle télécommande physique peut lancer vos automatisations. Appuyez sur le bouton rouge de la vieille télécommande TV pour lancer votre scène soirée cinéma. Les déclencheurs savent quelle pièce a entendu l'appui, donc la même télécommande peut faire des choses différentes selon la pièce. Aucune autre intégration ne fait ça.
- **Regardez le Mirror.** Un audit en direct de tout ce que votre maison transmet : quelle commande est partie, par quel blaster, et quel récepteur l'a entendue en retour. Si quelque chose d'infrarouge se comporte mal à 2h du matin, le Mirror l'a vu.
- **Testez et peaufinez tout.** Envoyez n'importe quel signal par n'importe quel blaster pour le vérifier avant de lui faire confiance, donnez des surnoms aux signaux, modifiez un code Pronto sur place, et laissez HAIR décoder les protocoles reconnus (NEC, Sony, RC-5, Samsung et d'autres) pour une transmission plus propre.

Le panneau parle votre langue. Anglais, espagnol, français, japonais, allemand, polonais, portugais, néerlandais, italien et russe, en suivant automatiquement la langue de votre profil Home Assistant.

> [!IMPORTANT]
> Cette traduction du panneau HAIR a été rédigée par un assistant de programmation et attend la relecture d'un locuteur natif. Si cela pouvait être vous, une relecture tient dans une seule pull request et votre nom entre dans le fichier. Commencez ici : [Adding a language](CONTRIBUTING.md#adding-a-language).

## Installation

1. Ajoutez `https://github.com/DAB-LABS/HAIR` à HACS comme dépôt personnalisé (catégorie : Integration)
2. Installez HAIR, redémarrez Home Assistant, puis ajoutez l'intégration dans Paramètres, puis Appareils et services

Nécessite Home Assistant 2026.4 ou plus récent ; 2026.6+ recommandé pour les récepteurs IR natifs.

## Documentation complète

Le README complet, avec le YAML d'installation, le matériel pris en charge, les guides des fonctionnalités et les captures d'écran, est en anglais :

**[Lire la documentation complète](README.md)**

---

*Traduit du README anglais, version v0.6.9. Ce fichier a été rédigé par un assistant de programmation et est rafraîchi à chaque version. Les locuteurs natifs sont les bienvenus pour en prendre la responsabilité ; voir [Adding a language](CONTRIBUTING.md#adding-a-language).*

<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="Baner HAIR" width="900" />
</p>

# HAIR

**HAIR wyciąga Twoje kody IR z chmur producentów, pamięci nadajników i plików konfiguracyjnych, i wprowadza je do Home Assistant.**

Skieruj dowolnego pilota na odbiornik IR, naciśnij przycisk, a HAIR zamieni ten sygnał w coś, czego Home Assistant naprawdę potrafi użyć: przycisk na dowolnym dashboardzie, wyzwalacz dla Twoich automatyzacji, polecenie do wysłania przez dowolny nadajnik na natywnej platformie podczerwieni HA. Bez YAML, bez aplikacji producentów, bez pobierania plików z kodami.

## Pięć sposobów na wprowadzenie kodów

- **Przechwyć go.** Naciśnij przycisk prawdziwego pilota, a HAIR złapie go na żywo z powietrza, pobierze odcisk i pogrupuje według pilota.
- **Skonwertuj go.** Wklej znane kody IR albo wypełnij całego pilota z zainstalowanej biblioteki kodów, wybierając producenta i model.
- **Wyciągnij go.** Pobierz kody nauczone już w nadajniku producenta (np. Tuya Local) bez ponownego uczenia choćby jednego na odbiorniku.
- **Podsłuchaj go.** Każde polecenie IR wysłane przez Home Assistant pojawia się w Mirror, usłyszane czy nie, o jedno kliknięcie od stania się Twoim poleceniem.
- **Załóż ją.** Upuść plik z kodami do Szafy -- udostępnioną perukę, JSON ze SmartIR, plik `.ir` z Flipper Zero, konfigurację LIRC albo eksport Girr z IrScrutinizer -- a zawiśnie w Twojej kolekcji, o jedno kliknięcie od stania się działającym pilotem.

## Co z nimi zrobisz

- **Twórz urządzenia.** Zbuduj profil telewizora, klimatyzatora, wentylatora, światła, przełącznika lub ekranu, przypisz mu przechwycone sygnały jako polecenia, a HAIR automatycznie utworzy pasujące natywne encje: prawdziwy odtwarzacz multimedialny dla telewizora, prawdziwą encję klimatu dla klimatyzatora z trybami i presetami temperatury, wentylator z regulacją prędkości. Działają na dashboardach, w skryptach i w asystentach głosowych jak każde inne urządzenie Home Assistant.
- **Zamień przyciski pilota w wyzwalacze.** Dowolny przycisk dowolnego fizycznego pilota może uruchamiać Twoje automatyzacje. Naciśnij czerwony przycisk starego pilota od telewizora, aby uruchomić scenę wieczoru filmowego. Wyzwalacze wiedzą, który pokój usłyszał naciśnięcie, więc ten sam pilot może robić różne rzeczy w różnych pokojach. Żadna inna integracja tego nie potrafi.
- **Obserwuj Mirror.** Audyt na żywo wszystkiego, co nadaje Twój dom: jakie polecenie wyszło, przez który nadajnik i który odbiornik je usłyszał. Jeśli coś podczerwonego zachowa się źle o 2 w nocy, Mirror to widział.
- **Testuj i szlifuj wszystko.** Wystrzel dowolny sygnał przez dowolny nadajnik, aby go sprawdzić, zanim mu zaufasz, nadawaj sygnałom przydomki, edytuj kod Pronto na miejscu, a rozpoznane protokoły (NEC, Sony, RC-5, Samsung i inne) HAIR zdekoduje dla czystszej transmisji.

Panel mówi w Twoim języku. Angielski, hiszpański, francuski, japoński, niemiecki, polski, portugalski, niderlandzki, włoski i rosyjski, automatycznie według języka Twojego profilu Home Assistant.

> [!IMPORTANT]
> To tłumaczenie panelu HAIR zostało przygotowane przez asystenta programistycznego i czeka na przegląd rodzimego użytkownika języka. Jeśli to możesz być Ty: przegląd mieści się w jednym pull requeście, a Twoje nazwisko trafia do pliku. Zacznij tutaj: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Instalacja

1. Dodaj `https://github.com/DAB-LABS/HAIR` do HACS jako repozytorium niestandardowe (kategoria: Integration)
2. Zainstaluj HAIR, zrestartuj Home Assistant i dodaj integrację w Ustawienia, potem Urządzenia i usługi

Wymaga Home Assistant 2026.4 lub nowszego; 2026.6+ zalecane dla natywnych odbiorników IR.

## Pełna dokumentacja

Kompletny README, z YAML-em konfiguracji, obsługiwanym sprzętem, przewodnikami po funkcjach i zrzutami ekranu, jest po angielsku:

**[Przeczytaj pełną dokumentację](README.md)**

---

*Przetłumaczone z angielskiego README, stan na v0.7.1. Ten plik został przygotowany przez asystenta programistycznego i jest odświeżany przy każdym wydaniu. Rodzimi użytkownicy języka są mile widziani, by przejąć nad nim opiekę; zobacz [Adding a language](CONTRIBUTING.md#adding-a-language).*

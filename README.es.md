<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="Cartel de HAIR" width="900" />
</p>

# HAIR

**HAIR saca tus códigos IR de las nubes de los fabricantes, de la memoria de los emisores y de los archivos de configuración, y los mete en Home Assistant.**

Apunta cualquier mando a un receptor IR, pulsa un botón, y HAIR convierte esa señal en algo que Home Assistant puede usar de verdad: un botón en cualquier panel, un disparador para tus automatizaciones, un comando que puedes enviar por cualquier emisor de la plataforma infrarroja nativa de HA. Sin YAML, sin apps de fabricantes, sin descargar archivos de códigos.

## Cinco formas de meter tus códigos

- **Olfatéalo.** Pulsa un botón de un mando real y HAIR lo captura en vivo desde el aire, le toma la huella y lo agrupa por mando.
- **Conviértelo.** Pega códigos IR conocidos, o rellena un mando completo desde la biblioteca de códigos instalada eligiendo fabricante y modelo.
- **Extráelo.** Saca los códigos ya aprendidos en un emisor de fabricante (como Tuya Local) sin reaprender ninguno en el receptor.
- **Escúchalo.** Cada comando IR enviado a través de Home Assistant aparece en el Mirror, se haya oído de vuelta o no, a un clic de convertirse en un comando tuyo.
- **Póntelo.** Suelta un archivo de códigos en el Armario -- una peluca compartida, un JSON de SmartIR, un `.ir` de Flipper Zero, una configuración LIRC o una exportación Girr de IrScrutinizer -- y se cuelga con tu colección, a un clic de convertirse en un mando funcional.

## Qué haces con ellos

- **Crea dispositivos.** Construye un perfil para tu TV, aire acondicionado, ventilador, luz, interruptor o pantalla, asígnale señales capturadas como comandos, y HAIR crea automáticamente las entidades nativas correspondientes: un reproductor multimedia de verdad para la TV, una entidad de clima de verdad para el aire con modos y preajustes de temperatura, un ventilador con control de velocidad. Funcionan en paneles, scripts y asistentes de voz como cualquier otro dispositivo de Home Assistant.
- **Convierte los botones del mando en disparadores.** Cualquier botón de cualquier mando físico puede lanzar tus automatizaciones. Pulsa el botón rojo del viejo mando de la TV para ejecutar tu escena de noche de cine. Los disparadores saben qué habitación oyó la pulsación, así que el mismo mando puede hacer cosas distintas en habitaciones distintas. Ninguna otra integración hace esto.
- **Observa el Mirror.** Una auditoría en vivo de todo lo que transmite tu casa: qué comando salió, por qué emisor, y qué receptor lo oyó de vuelta. Si algo infrarrojo se porta mal a las 2 de la mañana, el Mirror lo vio.
- **Prueba y pule todo.** Dispara cualquier señal por cualquier emisor para verificarla antes de fiarte de ella, ponles apodos a las señales, edita un código Pronto en el sitio, y deja que HAIR decodifique los protocolos reconocidos (NEC, Sony, RC-5, Samsung y más) para una transmisión más limpia.

El panel habla tu idioma. Inglés, español, francés, japonés, alemán, polaco, portugués, neerlandés, italiano y ruso, siguiendo automáticamente el idioma de tu perfil de Home Assistant.

> [!IMPORTANT]
> Esta traducción del panel de HAIR fue redactada por un asistente de programación y espera la revisión de un hablante nativo. Si ese puedes ser tú, una revisión cabe en una sola pull request y tu nombre queda en el archivo. Empieza aquí: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Instalación

1. Añade `https://github.com/DAB-LABS/HAIR` a HACS como repositorio personalizado (categoría: Integration)
2. Instala HAIR, reinicia Home Assistant y añade la integración en Ajustes, luego Dispositivos y servicios

Requiere Home Assistant 2026.4 o posterior; se recomienda 2026.6+ para receptores IR nativos.

## Documentación completa

El README completo, con el YAML de configuración, el hardware compatible, las guías de funciones y las capturas de pantalla, está en inglés:

**[Leer la documentación completa](README.md)**

---

*Traducido del README en inglés, versión v0.7.2. Este archivo fue redactado por un asistente de programación y se actualiza con cada versión. Los hablantes nativos son bienvenidos a hacerse cargo de él; ver [Adding a language](CONTRIBUTING.md#adding-a-language).*

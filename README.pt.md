<p align="center">
  <img src="images/HAIR-readme-hero-v0.2.png" alt="Banner do HAIR" width="900" />
</p>

# HAIR

**O HAIR tira seus códigos IR das nuvens dos fabricantes, da memória dos emissores e dos arquivos de configuração, e os coloca dentro do Home Assistant.**

Aponte qualquer controle remoto para um receptor IR, pressione um botão, e o HAIR transforma esse sinal em algo que o Home Assistant realmente sabe usar: um botão em qualquer painel, um gatilho para suas automações, um comando que você pode enviar por qualquer emissor da plataforma infravermelha nativa do HA. Sem YAML, sem aplicativos de fabricantes, sem baixar arquivos de códigos.

## Quatro jeitos de colocar seus códigos

- **Fareje.** Pressione um botão de um controle de verdade e o HAIR o captura ao vivo do ar, tira sua impressão digital e o agrupa por controle.
- **Converta.** Cole códigos IR conhecidos, ou preencha um controle inteiro a partir da biblioteca de códigos instalada escolhendo fabricante e modelo.
- **Extraia.** Puxe códigos já aprendidos em um emissor de fabricante (como o Tuya Local) sem reaprender nenhum no receptor.
- **Escute.** Cada comando IR enviado pelo Home Assistant aparece no Mirror, ouvido de volta ou não, a um clique de virar um comando seu.

## O que você faz com eles

- **Crie dispositivos.** Monte um perfil para sua TV, ar-condicionado, ventilador, luz, interruptor ou tela, atribua sinais capturados como comandos, e o HAIR cria automaticamente as entidades nativas correspondentes: um reprodutor de mídia de verdade para a TV, uma entidade de clima de verdade para o ar com modos e presets de temperatura, um ventilador com controle de velocidade. Funcionam em painéis, scripts e assistentes de voz como qualquer outro dispositivo do Home Assistant.
- **Transforme botões de controle em gatilhos.** Qualquer botão de qualquer controle físico pode disparar suas automações. Pressione o botão vermelho do velho controle da TV para rodar sua cena de noite de cinema. Os gatilhos sabem qual cômodo ouviu o toque, então o mesmo controle pode fazer coisas diferentes em cômodos diferentes. Nenhuma outra integração faz isso.
- **Observe o Mirror.** Uma auditoria ao vivo de tudo que sua casa transmite: qual comando saiu, por qual emissor, e qual receptor o ouviu de volta. Se algo infravermelho se comportar mal às 2 da manhã, o Mirror viu.
- **Teste e lapide tudo.** Dispare qualquer sinal por qualquer emissor para verificar antes de confiar, dê apelidos aos sinais, edite um código Pronto na hora, e deixe o HAIR decodificar os protocolos reconhecidos (NEC, Sony, RC-5, Samsung e mais) para uma transmissão mais limpa.

O painel fala o seu idioma. Inglês, espanhol, francês, japonês, alemão, polonês, português, holandês, italiano e russo, seguindo automaticamente o idioma do seu perfil no Home Assistant.

> [!IMPORTANT]
> Esta tradução do painel do HAIR foi redigida por um assistente de programação e aguarda a revisão de um falante nativo. Se esse alguém puder ser você: uma revisão cabe em um único pull request e seu nome fica no arquivo. Comece aqui: [Adding a language](CONTRIBUTING.md#adding-a-language).

## Instalação

1. Adicione `https://github.com/DAB-LABS/HAIR` ao HACS como repositório personalizado (categoria: Integration)
2. Instale o HAIR, reinicie o Home Assistant e adicione a integração em Configurações, depois Dispositivos e serviços

Requer Home Assistant 2026.4 ou mais recente; 2026.6+ recomendado para receptores IR nativos.

## Documentação completa

O README completo, com YAML de configuração, hardware compatível, guias de funcionalidades e capturas de tela, está em inglês:

**[Ler a documentação completa](README.md)**

---

*Traduzido do README em inglês, versão v0.6.9. Este arquivo foi redigido por um assistente de programação e é atualizado a cada versão. Falantes nativos são bem-vindos para assumir a responsabilidade por ele; veja [Adding a language](CONTRIBUTING.md#adding-a-language).*

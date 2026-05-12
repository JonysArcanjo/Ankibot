# Ankibot

Automacao em Python para criar e atualizar flashcards no Anki a partir de planilhas `.csv`, `.xlsx` e `.numbers` no macOS.

## Como funciona

O script:

1. Varre a pasta configurada com as planilhas.
2. Le os arquivos suportados.
3. Usa `external_id` para decidir entre criar ou atualizar uma nota.
4. Traduz a frente quando necessario e gera audio automaticamente no macOS.
5. Cria um baralho no Anki usando o caminho da planilha, incluindo subpastas como hierarquia.
6. Sincroniza com o Anki via `AnkiConnect`.
7. Salva um estado local para evitar reprocessar arquivos sem alteracoes.

## Requisitos

- macOS
- Python 3.9+
- Anki instalado
- Add-on `AnkiConnect` instalado no Anki
- Para `.numbers`, o app Numbers precisa estar instalado
- Internet para a traducao automatica quando ela estiver ativada
- O comando nativo `say` do macOS para gerar audio

## Instalacao

```bash
./scripts/bootstrap.sh
```

Se preferir ativar manualmente:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

## Configuracao

Edite [config.yaml](/Users/jonysarcanjo/Ankibot/config.yaml) se quiser trocar deck, tipo de nota ou pasta de entrada.

Por padrao, ao rodar `./scripts/run.sh`, o projeto tenta abrir o Anki automaticamente se o `AnkiConnect` nao estiver ativo.
Quando o Ankibot abre o Anki automaticamente, ele tambem tenta fechar o app ao terminar a execucao.

Pasta monitorada por padrao:

`/Users/jonysarcanjo/Anki_baralhos_auto`

Estrategia de baralho por padrao:

`deck_strategy: file_name`

Isso significa que cada planilha vira um baralho com o nome do arquivo.
Se a planilha estiver em subpastas, cada pasta vira um nivel de sub-baralho no Anki.

## Formato da planilha

Colunas obrigatorias:

- `external_id`
- `frente`

Colunas opcionais:

- `prompt`
- `answer`
- `verso`
- `audio`
- `tags`
- `note_type`
- `updated_at`
- `target_language`

### Exemplo

Veja [flashcards_example.csv](/Users/jonysarcanjo/Ankibot/examples/flashcards_example.csv).

## Como rodar

Diretorio oficial do projeto:

`/Users/jonysarcanjo/Ankibot`

Diretorio oficial das planilhas:

`/Users/jonysarcanjo/Anki_baralhos_auto`

### Simulacao

```bash
./scripts/run.sh --dry-run
```

### Execucao real

Abra o Anki antes de rodar:

```bash
./scripts/run.sh
```

Se o Anki estiver fechado, o script tenta abrir o app `Anki` sozinho, aguarda o `AnkiConnect` responder e fecha o Anki ao terminar.

Se quiser rodar manualmente sem script:

```bash
.venv/bin/python main.py --dry-run
```

## Observacoes importantes

- O campo `external_id` precisa ser um campo real no seu tipo de nota `Flaskcards`.
- O script procura notas por esse campo para conseguir atualizar corretamente.
- A coluna `frente` vira a frente do card no Anki.
- Cada planilha gera um baralho com base no nome do arquivo.
- Exemplo: `verbos_irregulares.xlsx` gera o baralho `verbos_irregulares`.
- Exemplo: `A1 Level/Course Section/A1 Course Section 01.csv` gera `A1 Level::Course Section::A1 Course Section 01`.
- A coluna `verso` pode funcionar como override manual do texto do verso.
- Se `verso` vier vazio, o script traduz a `frente` para o idioma alvo.
- O `verso` final fica no formato `texto traduzido + audio`.
- O idioma alvo pode vir na coluna `target_language` ou no `config.yaml` em `translation.default_target_language`.
- Se a coluna `audio` vier preenchida com um valor do Anki, esse valor tem prioridade e nao gera audio novo.
- Se `audio` vier vazio, o script gera audio automaticamente com `say`, envia para a pasta de midia do Anki e usa o `[sound:arquivo.aiff]` no verso.
- A voz usada no audio e padronizada globalmente em `config.yaml` com `audio.voice`.
- Se um arquivo ja tiver sido processado, mas o baralho correspondente tiver sido apagado no Anki, o script reprocessa automaticamente esse arquivo na proxima execucao.
- Arquivos `.numbers` sao exportados para `.csv` com AppleScript antes da leitura.
- No terminal interativo, a execucao mostra uma barra de progresso em passos de 20%.
- Os detalhes completos de criacao, atualizacao e `DRY RUN` ficam no arquivo de log, deixando o terminal mais limpo.

## Formatos suportados

O projeto aceita dois formatos principais de planilha:

### Formato completo

Colunas como:

- `external_id`
- `frente`
- `verso`
- `target_language`
- `audio`
- `tags`
- `note_type`
- `updated_at`

### Formato simplificado

Tambem aceita planilhas com:

- `Front`
- `Back`
- `Sentence`

Nesse caso, o script:

- mapeia `Front` para a frente do card
- usa `Back` como base do verso
- adiciona `Sentence` abaixo no formato `💬 Sentence: ...`
- gera `external_id` automaticamente com base no nome do arquivo e na linha

## Agendamento diario no macOS

O projeto ja esta preparado para rodar com `launchd` usando o modelo [com.jonysarcanjo.ankibot.plist](/Users/jonysarcanjo/Ankibot/examples/com.jonysarcanjo.ankibot.plist).

Configuracao atual:

- horario diario: `06:00 AM`
- logs do launchd:
  - [launchd.out.log](/Users/jonysarcanjo/Ankibot/logs/launchd.out.log)
  - [launchd.err.log](/Users/jonysarcanjo/Ankibot/logs/launchd.err.log)

## Logs

Log principal do projeto:

- [ankibot.log](/Users/jonysarcanjo/Ankibot/logs/ankibot.log)

Nele ficam os detalhes completos das importacoes, atualizacoes, audio gerado e execucoes em `dry-run`.

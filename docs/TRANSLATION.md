# Tradução (PT-BR)

Ferramentas para traduzir os textos do jogo sem tocar na ISO: os textos traduzidos e a fonte com
acentos viram arquivos na pasta `mods/`, que o port carrega no lugar dos do disco
([modding/README.md](modding/README.md#the-mods-folder)).

> Os arquivos exportados contêm o texto original do jogo (Capcom). Eles ficam nas pastas ignoradas
> `translation/` e `mods/` e **não devem ir para o Git nem ser distribuídos**. O repositório só
> guarda as ferramentas.

## Passo a passo

```sh
# 1. exportar todos os textos para translation/ (uma vez)
python pc/tools/text.py --iso "SLUS-20184.iso" export

# 2. editar translation/salas/RM_xxxx.txt, translation/itens.txt e translation/sistema.txt

# 3. gerar os mods: salas alteradas (RM_xxxx.RDX), SYSMES.ALD e a fonte com acentos
python pc/tools/text.py --iso "SLUS-20184.iso" import --mods mods
python pc/tools/font.py --iso "SLUS-20184.iso" --mods mods
```

Rode o jogo com a pasta `mods/` ao lado do `recvx.exe` (ou `RECVX_MODS=caminho`). O log mostra
`mods: ... replaces the disc file` para cada arquivo usado. Só as salas com mensagens alteradas
viram mods.

`text.py check` confere que exportar e importar sem mudanças reproduz todas as mensagens.

## Formato dos arquivos

```
# RM_1000.RDX: 12 mensagens. ...
### 0
Primeira linha
segunda linha

### 1
...
```

- Cada mensagem começa em `### N`; as quebras de linha do arquivo são as do jogo.
- O espaço entre palavras é o espaço normal. `{espaco}` é o espaço largo, `{_}` o glifo de espaço 0.
- `{XXXX}` e `{XXXX:YYYY}` são códigos de controle do jogo (cores, pausas, escolhas): mantenha-os.
- O número de mensagens de cada arquivo é fixo: não apague nem crie entradas `### N`.
- A largura da caixa de texto é a do jogo: frases muito mais longas que o original podem sair da
  caixa; quebre as linhas.

## Acentos

`font.py` desenha as letras abaixo nas células livres da fonte (códigos 108 a 134) e
`decomp/.../message.c` (`FontSz`, `bhGetFontSize`) conhece suas larguras:

`á à â ã é ê í ó ô õ ú ü ç Á À Â Ã É Ê Í Ó Ô Õ Ú Ç ñ Ñ`

Para outra letra, acrescente-a em `EXTRA_GLYPHS` (`pc/tools/text.py`) e regenere a fonte e a
tabela de larguras (o script de `message.c` fica no histórico do Git).

## Como funciona

- Mensagens: tabelas de `u16` (códigos de glifo, `ASCII - 32` abaixo de 95, `0xFFxx` controle,
  `0xFFFF` fim). Nas salas ficam na seção `mesp` do `.RDX`; o import grava uma tabela nova no fim
  da sala e aponta `mesp` para ela, então o texto pode ficar mais longo que o original.
- `SYSMES.ALD`: `u32` tamanho + tabela de nomes de itens, `u32` tamanho + tabela de mensagens do
  sistema (`system.c`, `bhSysCallMonitor`).
- Fonte: primeira textura de `SYSEFF.ALD` (`SYSTEM.AFS` entrada 1), TIM2 512x512 de 4 bits com
  células de 28x28 (`message.c bhDispFont`). O mod é `mods/SYSTEM.AFS/1`.

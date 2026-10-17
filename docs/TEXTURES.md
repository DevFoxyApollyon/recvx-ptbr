# Texturas trocadas (PT-BR)

O port pode trocar qualquer textura do jogo por um PNG seu, maior (upscale) ou editado (menu
traduzido). Cada textura tem um nome fixo: um hash de 16 caracteres dos pixels dela.

> As texturas são imagens do jogo (Capcom): não ficam neste repositório. Você gera as suas a
> partir do seu disco com as ferramentas abaixo.

## Onde ficam

| Arquivo | Quando é usado |
|---|---|
| `mods/textures/pt/<hash>.png` | com os menus em Português (primeiro) |
| `mods/textures/<hash>.png` | sempre (upscale) |

O PNG pode ter qualquer tamanho: o jogo lê a textura em coordenadas normalizadas, então um PNG
3x maior só deixa a imagem mais nítida. O canal alfa segue o do PS2: **128 = opaco** (0..128).
O log (`--log`) mostra `textures: <hash> replaced (512x512 -> 2048x2048)`.

## Extrair as texturas

```sh
mkdir dump
RECVX_TEX_DUMP=dump recvx.exe "SLUS-20184.iso"
```

Cada textura que o jogo carrega é salva uma vez em `dump/<hash>.png`.

## Menu título em Português

```sh
python pc/tools/title_ptbr.py dump/64cae74c03148763.png mods
```

Escreve `mods/textures/pt/64cae74c03148763.png`: as placas do menu (CARREGAR JOGO, NOVO JOGO,
OPCOES, MODO BATALHA, MULTIJOGADOR, PRESSIONE START) em 4x, sem acentos. Com esse arquivo, a
linha MULTIJOGADOR do título e do lobby também vem dele.

## Upscale do fundo

```sh
python pc/tools/tex_upscale.py mods dump/381608b0e14a4b75.png --scale 3
```

`381608b0e14a4b75` é o fundo do título. O filtro do script (Lanczos + nitidez) só aumenta; para
ganhar detalhe de verdade passe o PNG por um upscaler de IA (Real-ESRGAN, waifu2x) e salve com o
mesmo nome em `mods/textures`.

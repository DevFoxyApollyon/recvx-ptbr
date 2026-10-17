# Legendas (PT-BR)

O port mostra uma legenda embaixo da tela enquanto o jogo toca uma fala. Cada fala do jogo é um
arquivo de voz (`VOICE1.AFS` / `VOICE2.AFS`, 1040 no total); a legenda de cada uma vem do arquivo
**`mods/legendas.txt`**, que é seu e fica só no seu PC.

> O texto das legendas é uma tradução do roteiro do jogo (Capcom): ele não faz parte deste
> repositório e não deve ser distribuído. O port e as ferramentas só leem o seu arquivo.

## Começar

```sh
# cria mods/legendas.txt com um bloco vazio para cada fala, com a duração dela
python pc/tools/subtitles.py template --iso "SLUS-20184.iso"
```

No jogo, ligue **F1 > Áudio > Mostrar código das falas**: cada fala que ainda não tem legenda
mostra o código dela embaixo (`[VOICE1.AFS/12]`). Escreva o texto embaixo desse bloco no arquivo e
salve; o jogo lê o arquivo de novo sozinho (a cada 2 segundos), não precisa reiniciar.

## Formato

```
# comentário
[VOICE1.AFS/12]
0.0 Primeira frase da fala.
2.4 Segunda frase|em duas linhas.

[VOICE1.AFS/13]
Uma frase sem tempo: fica na tela durante a fala inteira.
Outra linha sem tempo entra junto, embaixo.
```

- `[ARQUIVO/numero]` começa o bloco de uma fala.
- Uma linha que começa com um tempo (segundos, ou `m:ss.s`) troca a legenda nesse momento da fala.
- Linhas sem tempo depois da primeira entram juntas, uma embaixo da outra.
- `|` quebra a linha na tela.
- A legenda some meio segundo depois que a fala acaba.
- **Os acentos são tirados na tela** (`ação` aparece `acao`), para nunca aparecer um caractere errado.

## Opções (F1 > Áudio > LEGENDAS)

| Opção | ini | Padrão |
|---|---|---|
| Legendas | `subtitles` | ligado |
| Tamanho da legenda | `subtitle_size` | 100% |
| Mostrar código das falas | `subtitle_ids` | desligado |

## Limites

- Só as falas tocadas como voz (cutscenes no motor do jogo, rádio, falas em jogo). Os vídeos
  pré-renderizados (`MOVIE/*.PSS`) têm o áudio dentro do vídeo e ainda não recebem legenda.
- Teste: `RECVX_SUB_TEST="texto"` mostra esse texto sempre; o log (`--log`) registra
  `subtitles: voice ...` e `subtitles: showing ...`.

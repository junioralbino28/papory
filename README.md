<p align="center"><img src="marca/papory-512.png" width="180" alt="O papagaio do Papory"></p>

# Papory

Ditado por voz para Windows e Mac que entende português de verdade. Você segura um atalho, fala e solta, e o texto aparece onde o cursor está, em qualquer programa: editor de código, navegador, WhatsApp, Word.

Roda no seu computador e é grátis. Não tem conta nem assinatura, e a sua voz não sai da sua máquina.

Eu fiz o Papory porque dito o dia inteiro, principalmente conversando com IA no editor de código, e os apps de ditado bons são pagos e mandam tudo para a nuvem. Testei vários motores de reconhecimento na minha própria voz e o que mais acertou em português, o Parakeet da NVIDIA, roda local e de graça. O Papory é esse motor com uma interface simples em volta.

## Como funciona

Todo ditado passa por duas etapas.

1. **Ouvir.** O Parakeet transforma a sua voz em texto, sempre no seu computador, na placa de vídeo se tiver uma (no Windows), ou no processador.
2. **Arrumar o texto**, se você quiser. Existem dois reforços opcionais para isso.
   - O polimento local usa uma IA pequena (qwen3.5 4B, pelo Ollama) que corrige palavras que soam parecido e tira "é", "tipo" e "né" sobrando. Também roda no seu computador.
   - O reforço na nuvem faz uma segunda transcrição e uma revisão pela Groq, com a sua chave gratuita. Erra menos, mas aí o áudio sai do computador. Vem desligado.

Se um reforço falhar (sem internet, cota acabou, demorou), o Papory segue com o que tem e você nem percebe.

Na minha voz, lendo um roteiro com frases simples e difíceis, o erro de palavras ficou assim:

| Caminho | Erro de palavras |
|---|---|
| Só o reconhecimento | 12,0% |
| Com o polimento local | 10,2% |
| Com o reforço na nuvem | 5,8% |

## Instalar

### No Windows

1. Baixe o `Papory-Setup.exe` na [página de versões](https://github.com/junioralbino28/papory/releases/latest) e instale.
2. Abra o Papory. Na primeira vez ele baixa o modelo de voz (cerca de 2,5 GB, uma vez só), testa o seu microfone e mostra o atalho. Depois disso funciona sem internet.

O Windows pode mostrar o aviso "O Windows protegeu o computador", porque o instalador não tem assinatura digital paga. Clique em "Mais informações" e depois em "Executar assim mesmo".

Você precisa de Windows 10 ou 11 (64 bits), uns 3 GB livres (mais 3,3 GB se usar o polimento local) e um microfone. Placa de vídeo é opcional, AMD, NVIDIA ou Intel. Sem ela o Papory roda no processador, mais devagar.

### No Mac

1. Na [página de versões](https://github.com/junioralbino28/papory/releases/latest), baixe o `.dmg` do seu Mac. Para saber qual é, abra o menu da maçã e clique em "Sobre Este Mac". Se aparecer "Chip Apple" (M1, M2, M3...), baixe o `Mac-Apple-Silicon`. Se aparecer "Processador Intel", baixe o `Mac-Intel`.
2. Abra o `.dmg` e arraste o Papory para a pasta Aplicativos.
3. Abra o Papory pela pasta Aplicativos. Na primeira vez ele baixa o modelo de voz (cerca de 2,5 GB, uma vez só).

O Papory não tem a assinatura paga da Apple, então o Mac diz que ele é de um desenvolvedor não identificado e não abre de primeira. Isso só acontece na primeira abertura.

- No macOS 12 a 14, clique no Papory com o botão direito (ou Control + clique) na pasta Aplicativos, escolha Abrir e confirme em Abrir.
- No macOS 15 ou mais novo, tente abrir uma vez, depois vá em Ajustes do Sistema > Privacidade e Segurança, desça até o aviso sobre o Papory e clique em "Abrir Mesmo Assim".

Depois o Mac pede três permissões, e sem elas o Papory não funciona. Todas ficam em Ajustes do Sistema > Privacidade e Segurança (no macOS 12, Preferências do Sistema > Segurança e Privacidade > Privacidade).

| Permissão | Para que serve |
|---|---|
| Microfone | ouvir você enquanto segura o atalho |
| Monitoramento de Entrada | saber quando você aperta o atalho |
| Acessibilidade | colar o texto onde o cursor está |

Marque o Papory em cada uma. Depois de liberar o Monitoramento de Entrada, feche o Papory (papagaio na barra de menus, Sair) e abra de novo.

Você precisa de macOS 12 (Monterey) ou mais novo, Intel ou Apple Silicon, uns 3 GB livres e um microfone. No Mac o reconhecimento roda no processador.

### No Mac, para não liberar tudo de novo a cada versão

Sem a assinatura paga, cada versão nova do Papory chega com outra "impressão digital", e o Mac acha que é OUTRO app. As permissões param de valer mesmo aparecendo marcadas. (Atualizar o macOS não apaga nada, o problema é só atualizar o Papory.)

Para isso não acontecer, o Papory traz um script que cria um certificado só seu, no seu Mac, e assina o app com ele. Com a mesma assinatura em toda versão, o Mac reconhece o Papory e as permissões continuam valendo.

1. Abra o Terminal (Aplicativos > Utilitários > Terminal).
2. Cole este comando e aperte Enter.

   ```
   bash /Applications/Papory.app/Contents/Resources/assinar-papory.sh
   ```

3. Na primeira vez, libere as permissões uma última vez. O script explica como (tirar o Papory da lista com o "−" e liberar de novo).
4. Depois de cada atualização do Papory, rode o mesmo comando. As permissões continuam valendo, sem liberar nada.

O script usa só o que já vem no Mac, não pede senha de administrador e não instala nada. O certificado fica em `~/Library/Application Support/Papory/assinatura` e não sai do seu Mac. Apagar essa pasta desfaz tudo.

Se você usa o Claude Code ou outra IA no terminal, peça a ela: "siga o guia do Papory em https://raw.githubusercontent.com/junioralbino28/papory/main/mac/ASSINAR-COM-IA.md". O [guia](mac/ASSINAR-COM-IA.md) explica para a IA o passo a passo, como conferir que deu certo e o que ela não deve fazer.

Sem o script, a saída é manual. A cada versão nova, abra Monitoramento de Entrada e Acessibilidade, selecione o Papory, clique no "−" para tirar da lista, abra o Papory de novo e libere outra vez.

## Usar

- Segure `Ctrl + Win` (no Mac, `Control + Command`), fale e solte. Dá para trocar o atalho nas Configurações.
- Enquanto você fala aparece uma pílula no rodapé da tela, e ela some quando o texto é colado.
- O Papory fica perto do relógio (no Mac, na barra de menus, lá em cima). O papagaio abre o menu, com microfone, pausa e "copiar o último ditado".
- Para o Papory aprender o seu jeito de falar, leia as frases de calibração. Elas aparecem na primeira abertura e ficam em Configurações, no cartão "Seu jeito de falar". Antes, escreva os nomes que você mais usa (empresa, clientes, ferramentas). Em uns 2 minutos ele vê o que ouviu errado, cria as trocas automáticas e avisa se o microfone está baixo ou estourando. Troca que mexeria numa palavra comum, como "uma hora", vem desmarcada para você decidir.
- Se ele errar uma palavra, abra o Papory, ache o ditado no Início e corrija pelo lápis. A palavra vai para o vocabulário, e a mesma correção feita duas vezes vira troca automática.
- Nos atalhos de texto você cadastra frases curtas que viram textos inteiros. Diga "meu e-mail" e ele escreve o endereço completo.

## Polimento local (opcional)

Precisa do [Ollama](https://ollama.com/download), um programa grátis que roda IAs pequenas no computador. Com o Ollama instalado e aberto, o Papory oferece baixar o modelo na primeira abertura ou nas Configurações. Sem ele o Papory funciona normal, só pula essa etapa.

Numa próxima versão esse motor vem dentro do próprio Papory e o Ollama deixa de ser necessário.

## Reforço na nuvem (opcional)

1. Crie uma chave grátis em [console.groq.com/keys](https://console.groq.com/keys).
2. No Papory, abra as Configurações, ligue "Reforço na nuvem" e cole a chave.

A chave fica guardada no Gerenciador de Credenciais do Windows (no Mac, no Acesso às Chaves), não num arquivo de texto. Com o reforço ligado, o áudio e o texto de cada ditado vão para a Groq.

## Privacidade

Com os dois reforços desligados, nada sai do seu computador. O histórico (áudio e texto de cada ditado) fica em `%APPDATA%\Papory\historico` (no Mac, em `~/Library/Application Support/Papory/historico`), e dá para desligar ou apagar tudo nas Configurações.

O Papory escuta o teclado só para saber quando você aperta o atalho. Alguns antivírus estranham isso, e o código inteiro está aqui para quem quiser conferir.

## Problemas comuns

- **O texto saiu duas vezes.** Outro app de ditado está usando o mesmo atalho. Feche o outro ou troque o atalho.
- **Aparece "Sem microfone".** Escolha o microfone nas Configurações ou no menu do papagaio.
- **Ficou lento no Windows.** Confira nas Configurações se o reconhecimento está na placa de vídeo.
- **No Mac, segurar o atalho não faz nada.** Confira se o Papory está marcado em Monitoramento de Entrada, feche e abra o Papory. Se você acabou de atualizar, rode o script de assinatura (ou tire o Papory da lista e libere de novo).
- **No Mac, o texto fica copiado em vez de colado.** Falta a permissão de Acessibilidade. Até liberar, cole com `Cmd + V`.
- **No Mac, aparece que o Papory "está danificado".** É o bloqueio de app baixado da internet. Abra o Terminal, rode `xattr -dr com.apple.quarantine /Applications/Papory.app` e abra o Papory de novo.

## Rodar pelo código

Precisa de Python 3.12.

No Windows:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python Papory.pyw
```

No Mac:

```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-mac.txt
.venv/bin/python Papory.pyw
```

Com `python -m papory --terminal` ele roda sem interface, mostrando tudo no terminal.

## Créditos e licença

O reconhecimento usa o [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), da NVIDIA (licença CC-BY-4.0), na versão ONNX do [onnx-asr](https://github.com/istupakov/onnx-asr). As fontes são a Pixelify Sans e a Plus Jakarta Sans, com a licença SIL Open Font em `papory/interface/fontes`. A lista de palavras comuns (`papory/palavras_comuns.txt`) vem do [FrequencyWords](https://github.com/hermitdave/FrequencyWords), de Hermit Dave, feito com legendas do OpenSubtitles, e tem licença CC BY-SA 4.0. O código do Papory tem licença MIT.

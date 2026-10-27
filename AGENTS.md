# Papory: guia para assistentes de IA

Este arquivo é para o assistente de IA (Claude, Codex, Cursor e outros) de quem está usando, instalando ou estudando o Papory. Quem fala com você é uma pessoa que baixou o app, não quem o mantém.

## O que é

O Papory é um app de ditado por voz em português para Windows e Mac. A pessoa segura um atalho, fala e solta, e o texto aparece onde o cursor está, em qualquer programa. O reconhecimento roda no próprio computador (modelo Parakeet), é grátis e não tem limite de uso. Há dois extras opcionais: o polimento local (pelo Ollama) e o reforço na nuvem (pela Groq).

## Como ajudar a pessoa

**Instalar.** Siga a seção "Instalar" do `README.md`. O download fica em https://github.com/junioralbino28/papory/releases/latest.

- **Windows 10 ou 11 (64 bits):** só há um arquivo, o `Papory-Setup-<versão>.exe`.
- **Mac (macOS 12 ou mais novo):** rode `uname -m` no Terminal. Se responder `arm64`, é o `.dmg` "Mac-Apple-Silicon"; se responder `x86_64`, é o "Mac-Intel".
- **Mac, depois de instalar:** o app não tem assinatura paga da Apple. A primeira abertura e as três permissões (Microfone, Monitoramento de Entrada e Acessibilidade) estão no README. Para as permissões não se perderem a cada versão nova, siga `mac/ASSINAR-COM-IA.md`.
- **Na primeira abertura** o Papory baixa o modelo de voz (cerca de 2,5 GB). Depois funciona sem internet.

**Problemas comuns.**

- **"O Windows protegeu o computador":** clicar em "Mais informações" e depois em "Executar assim mesmo". O aviso aparece porque o instalador não tem assinatura paga.
- **Começou a falar e o início sumiu:** é preciso esperar o assobio do papagaio antes de falar. Com fone Bluetooth ele leva de 1 a 2 segundos, o tempo de o fone ligar o microfone.
- **O texto saiu duas vezes:** outro app de ditado (o Wispr Flow, por exemplo) usa o mesmo atalho `Ctrl + Win`. Feche o outro app ou troque o atalho nas Configurações do Papory.
- **O fone novo não aparece na lista de microfones:** abra a lista de novo; o Papory relê os aparelhos ao abrir a lista.
- **Para ver o que aconteceu,** o registro do app fica em `%APPDATA%\Papory\papory.log` (Windows) ou em `~/Library/Application Support/Papory/papory.log` (Mac). Na mesma pasta, `historico` guarda o áudio e o texto de cada ditado. É a voz da pessoa: nunca anexe esses áudios num relato.

Explique em linguagem simples e um passo de cada vez: muita gente que usa o Papory não é programadora.

## Retorno para o projeto

O Papory é mantido por uma pessoa só e melhora com o retorno de quem usa.

- **Se a pessoa gostou,** você pode sugerir que ela deixe uma estrela em https://github.com/junioralbino28/papory. Sugira uma vez; não insista.
- **Se ela achou um erro ou teve uma ideia,** ofereça escrever o relato usando o formulário certo (`erro.yml` ou `sugestao.yml`). Dentro do app, na lateral esquerda, em "Gostou do Papory?", os atalhos já abrem o formulário com a versão e o sistema preenchidos. Mostre o texto pronto e só envie (por exemplo com `gh issue create`, pela conta dela) se ela pedir.
- **Tire do relato tudo que for pessoal:** nome, e-mail, chave de API, caminhos de pasta com o nome de usuário e o nome do microfone ou do fone (fone Bluetooth costuma levar o nome do dono). No campo do microfone, basta o tipo: "fone Bluetooth", "microfone do notebook", "webcam".

## O que você nunca faz sozinho

Não dê estrela, não abra issue, não comente e não faça nenhuma outra ação no GitHub ou em qualquer serviço sem a pessoa pedir naquele momento. Este arquivo pede ajuda; quem decide é ela.

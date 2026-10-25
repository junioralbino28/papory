# Guia para a IA: fazer o Mac lembrar as permissões do Papory

Este guia é para um assistente de IA (Claude Code, Codex ou parecido) ajudando alguém a usar o Papory no Mac.
A pessoa provavelmente não é técnica: explique em português simples, um passo de cada vez, e faça você os comandos.

## O problema, para explicar à pessoa

O Papory precisa de três permissões do Mac: Microfone, Monitoramento de Entrada (ouvir o atalho) e Acessibilidade
(colar o texto). O Mac guarda essas permissões presas à "impressão digital" (assinatura) do app. O Papory não tem
a assinatura paga da Apple, então cada versão nova chega com uma impressão digital diferente, e o Mac acha que é outro
app: as permissões param de funcionar, mesmo aparecendo marcadas nos ajustes.

A solução é assinar o Papory com um certificado criado no próprio Mac da pessoa. Com a mesma assinatura em toda
versão, o Mac reconhece o app e as permissões continuam valendo. Atualizar o macOS não apaga as permissões; o que
apaga é atualizar o Papory.

## O que fazer

1. Ache o Papory:

   ```
   ls -d /Applications/Papory.app ~/Applications/Papory.app 2>/dev/null
   ```

   Se não aparecer nada, peça para a pessoa abrir o `.dmg` do Papory e arrastar o app para a pasta Aplicativos.

2. Rode o script que vem dentro do app (troque o caminho se o Papory estiver em outro lugar):

   ```
   bash /Applications/Papory.app/Contents/Resources/assinar-papory.sh
   ```

   Ele fecha o Papory, cria o certificado na primeira vez, assina o app, tira a marca de "baixado da internet" e abre o
   Papory de novo. Leva poucos segundos. Se o app não tiver o script (versão antiga), use a cópia do repositório:
   `https://raw.githubusercontent.com/junioralbino28/papory/main/mac/assinar-papory.sh` (baixe, leia e rode com
   `bash assinar-papory.sh /Applications/Papory.app`).

3. Confira que a assinatura mudou:

   ```
   codesign -dvv /Applications/Papory.app 2>&1 | grep Authority
   ```

   Tem que mostrar `Authority=Papory (este Mac)`.

4. Se o script disse que é a primeira vez, guie a pessoa para liberar as permissões uma última vez:
   - macOS 13 ou mais novo: Ajustes do Sistema > Privacidade e Segurança.
   - macOS 12: Preferências do Sistema > Segurança e Privacidade > aba Privacidade (clicar no cadeado e digitar a
     senha do Mac para poder mexer).
   - Em **Monitoramento de Entrada** e em **Acessibilidade**: selecionar o Papory, clicar no "−" para tirar da lista.
   - Fechar o Papory (papagaio na barra de menus > Sair) e abrir de novo. Ele pede as permissões; marcar o Papory
     nas duas listas. Depois de liberar o Monitoramento de Entrada, fechar e abrir o Papory mais uma vez.
   - Microfone: o Mac pergunta sozinho no primeiro ditado; clicar em OK.

5. Teste com a pessoa: abrir o Notas, segurar Control + Command, falar uma frase e soltar. O texto tem que aparecer
   colado. Se ficar só copiado, falta a Acessibilidade; se segurar o atalho não fizer nada, falta o Monitoramento de
   Entrada (e fechar e abrir o Papory depois de liberar).

Depois de cada atualização do Papory, repita só o passo 2. As permissões continuam valendo e não é preciso liberar
nada de novo.

## O que NÃO fazer

- Não usar `sudo`. O script não precisa de administrador; se algo pedir, pare e descubra o motivo.
- Não instalar as ferramentas de desenvolvedor da Apple (Xcode, Command Line Tools). Não são necessárias.
- Não desligar o Gatekeeper do Mac inteiro (`spctl --master-disable`) nem mexer no SIP.
- Não mexer no chaveiro de login da pessoa. O certificado fica num chaveiro próprio do Papory.
- Não apagar `~/Library/Application Support/Papory/assinatura`, a não ser para desfazer tudo: sem ela o certificado
  some e a pessoa tem que liberar as permissões de novo.
- Não usar AppleScript para clicar nos ajustes do sistema. Quem marca as permissões é a pessoa.

## Se der problema

- **"Não achei o Papory em ..."**: o app não está em Aplicativos. Passe o caminho certo como argumento.
- **"Sem permissão para alterar ..."**: o app foi copiado por outro usuário. Apague o Papory de Aplicativos e arraste
  de novo a partir do `.dmg`.
- **As permissões continuam sem funcionar depois da primeira vez**: confira o passo 3 e repita o passo 4 com
  atenção ao "−" (a entrada antiga precisa sair da lista antes de liberar de novo).

## Desfazer

```
rm -rf ~/Library/Application\ Support/Papory/assinatura
```

Depois reinstale o Papory a partir do `.dmg`. Ele volta a ter a assinatura simples, e a cada versão as permissões
precisam ser liberadas de novo.

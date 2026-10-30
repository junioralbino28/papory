## Novidades da 0.1.11

- A pílula que mostra a gravação e o texto sendo escrito ganhou pausa e saída. A pausa impede novos ditados; o `X` fecha o Papory quando um processamento fica preso.
- A lista de microfones agora pode ser atualizada pelo botão **Procurar** e também é relida ao ser aberta, útil para fones Bluetooth que foram reconectados.

**Windows:** baixe o `Papory-Setup` abaixo e instale. Se o Windows mostrar "O Windows protegeu o computador", clique em "Mais informações" e depois em "Executar assim mesmo". O aviso aparece porque o instalador não tem assinatura digital paga. Precisa de Windows 10 ou 11 (64 bits).

**Mac:** baixe o `.dmg` do seu Mac (`Mac-Apple-Silicon` para chip M1, M2, M3..., `Mac-Intel` para processador Intel), abra e arraste o Papory para Aplicativos. Na primeira vez, abra com o botão direito > Abrir (no macOS 15 ou mais novo, em Ajustes do Sistema > Privacidade e Segurança > "Abrir Mesmo Assim") e libere Microfone, Monitoramento de Entrada e Acessibilidade. Para o Mac não pedir as permissões de novo a cada versão, veja no README como assinar o Papory com um certificado do seu próprio Mac. Precisa de macOS 12 ou mais novo.

Na primeira abertura o Papory baixa o modelo de voz (cerca de 2,5 GB, uma vez só) e depois funciona sem internet. O polimento local (opcional) usa o [Ollama](https://ollama.com/download), e o reforço na nuvem (opcional) usa uma chave grátis da [Groq](https://console.groq.com/keys). Detalhes no [README](https://github.com/junioralbino28/papory#readme).

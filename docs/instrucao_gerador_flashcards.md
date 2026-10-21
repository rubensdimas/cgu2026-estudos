# Gerador de Flashcards — CGU | CEBRASPE

A instrução usada pelo app está em [`apps/api/app/flashcards/prompt.md`](../apps/api/app/flashcards/prompt.md) e é enviada como prompt de sistema à OpenAI quando você gera flashcards de uma sessão de teoria (regra R16).

Em relação à versão original, escrita para um chat:

- O escopo ficou restrito aos subitens do edital do tópico; cada cartão indica o subitem que cobre, e o app descarta os que não indicam um subitem válido.
- A entrada é montada pelo app: disciplina, tópico, subitens, materiais sugeridos (título e nota) e o texto "O que estudei / errei". O modelo não acessa os links.
- A quantidade passou a ser de 5 a 10 cartões por sessão, sem preencher para atingir o número.
- Saíram as partes de conversa (comandos "Gerar flashcards", mensagem inicial e pedidos de mais contexto) e o formato Markdown; a saída é JSON estruturado, revisado como rascunho antes de entrar no baralho.
- Agendamento e avaliação das revisões passaram a ser regras do app (Parte 2: revisões em 1, 7 e 21 dias).

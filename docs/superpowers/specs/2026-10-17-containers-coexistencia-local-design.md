# Containers coexistindo no desenvolvimento local

Desenho confirmado na entrevista de 17/10/2026.

## Objetivo e decisões

- Desenvolvimento local, uma instância deste projeto coexistindo com projetos diferentes.
- Cada projeto tem seu próprio PostgreSQL. Este banco é acessível somente pelos containers, em `db:5432`, sem publicação de porta no host.
- Preservar o projeto Compose `cgu2026`, o volume existente `cgu2026_pgdata`, seus dados, o banco `cgu`, o banco de testes `cgu_test` e os backups.
- A aplicação publica `127.0.0.1:${APP_PORT:-8082}:8000`. `8080` está ocupada por outro projeto; `8082` estava disponível na inspeção.
- `APP_PORT` é opcional: ausente ou vazio significa `8082`; um valor configurado é uma porta TCP decimal válida. A variável do terminal tem precedência sobre o `.env` da raiz.
- O proxy `/api` do Vite usa `http://127.0.0.1:<APP_PORT efetiva>`, inclusive quando iniciado em `apps/web`.
- O `.env` da raiz é a configuração compartilhada. O Vite deve funcionar sem esse arquivo, inclusive no build Docker, e não deve enviar a senha do banco ao navegador.
- Atualizar `.env.example`, README, arquitetura e fluxo de primeiro uso. Documentar `tailscale serve --bg 8082` e a necessidade de usar a porta personalizada quando houver uma.

## Limites

- Manter PostgreSQL `17.6`, as versões e dependências existentes, a rede padrão por projeto e as conexões internas atuais.
- Não alterar os outros projetos, a configuração global do Tailscale ou o `.env` pessoal para obter a nova porta padrão.
- Não criar um PostgreSQL compartilhado, suporte a clones simultâneos, migração de dados ou uma nova camada de configuração da API.
- Não mudar o fallback da API executada diretamente no host: o caminho escolhido para o banco é pelos containers.

## Fronteiras de teste propostas para confirmação

1. **CLI pública do Compose:** `docker compose config --format json`, com ambiente temporário e senha fictícia. Observar portas, destino interno do banco e identidade do volume/rede; não iniciar serviços nos testes automatizados.
2. **API pública de configuração do Vite:** `resolveConfig(..., 'serve')`, carregando a configuração real em uma árvore temporária que reproduz `apps/web`. Observar o destino do proxy e as variáveis disponibilizadas ao cliente; sem mocks das funções do projeto.

Validação operacional posterior: iniciar este Compose, verificar `/api/v1/health`, volume montado e ausência de porta publicada no banco, mantendo os demais projetos ativos.

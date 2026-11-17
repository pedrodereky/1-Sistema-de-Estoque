# Sistema de Gestão de Estoque (ERP Simulado)

Módulo de estoque de um ERP, em Python, com banco **SQLite**: cadastro de itens, entradas e saídas com histórico, relatórios gerenciais e gráficos.

## Funcionalidades

| Menu | O que faz |
|---|---|
| 1. Cadastrar item | Nome, categoria, unidade (un, kg, L…), quantidade inicial, valor unitário e estoque mínimo (padrão 5) |
| 2. Listar itens | Todos os itens, com valor total e alerta de **estoque baixo** (abaixo do estoque mínimo do item) |
| 3. Buscar itens | Busca parcial por nome ou categoria |
| 4. Movimentar estoque | Entrada ou saída, sem permitir saída maior que o saldo; cada movimento fica registrado com data, hora e saldo resultante |
| 5. Relatórios gerenciais | Custo total em estoque, giro (total de saídas), estoque de segurança sugerido, tempo médio de reposição e itens críticos |
| 6. Dashboard | Gráficos da evolução do valor do estoque e da curva ABC por produto (requer `matplotlib`) |
| 7. Excluir item | Remove o item e o histórico de movimentos dele |
| 8. Exportar CSV | Gera uma planilha com os itens, o valor total e a situação de cada um (separador `;` e vírgula decimal, que o Excel em português abre direto) |

Valores aceitam vírgula ou ponto como separador decimal.

## Como executar

Requer Python 3.8+. O SQLite já vem com o Python.

```sh
python estoque.py
```

O banco `estoque.db` é criado na primeira execução. Para os gráficos do dashboard:

```sh
pip install -r requirements.txt
```

Para rodar os testes:

```sh
pip install -r requirements-dev.txt
pytest
```

## Banco de dados

- **`itens`**: id, nome, categoria, unidade, quantidade, valor unitário e estoque mínimo.
- **`movimentos`**: cada cadastro, entrada e saída, com a quantidade, o valor, a data e hora e o saldo do item e do estoque depois do movimento. É o histórico que alimenta o relatório e o gráfico de evolução.

## Melhorias futuras

- Interface gráfica ou API web.

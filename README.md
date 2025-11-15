
# Sistema de Gestão de Estoque (ERP Simulado)

Este projeto implementa uma simulação simples de um módulo de estoque de um ERP, utilizando a linguagem Python. O objetivo é permitir o cadastro, exclusão, listagem e geração de relatórios de produtos, aplicando conceitos de gestão de estoque, como organização de itens, controle de quantidades e visualização em formato de pilha.

## Funcionalidades

* Cadastro de produtos com código, descrição, categoria e quantidade.
* Exclusão de produtos com base no código identificador.
* Listagem completa de todos os itens cadastrados.
* Geração de relatórios que apresentam informações resumidas e estruturadas.
* Visualização da estrutura de estoque em formato de pilha (último que entra, primeiro que aparece na listagem).

## Tecnologias Utilizadas

* Python 3.x
* Estruturas de dados como listas e dicionários
* Funções organizadas para cada operação (cadastrar, excluir, listar, relatório)

## Estrutura Geral do Código

O sistema é organizado em funções responsáveis por:

* Inserir novos produtos
* Remover itens existentes
* Exibir todos os produtos
* Exibir relatório geral do estoque
* Mostrar a pilha de produtos de forma reversa, evidenciando o item mais recente

## Como Executar

1. Instale o Python 3 em seu computador.
2. Baixe ou clone o repositório contendo o arquivo principal do sistema.
3. Execute o programa no terminal com o comando:

```
python nome_do_arquivo.py
```

## Melhorias Futuras

* Armazenamento de dados em arquivos CSV ou JSON.
* Implementação de movimentações de entrada e saída.
* Criação de gráficos de controle de estoque.
* Interface gráfica ou integração com API.

estoque = []

opcao = ""
while opcao != "5":
    print("\n=== Sistema de Estoque ===")
    print("1 - Cadastrar Produto")
    print("2 - Excluir Produto")
    print("3 - Atualizar Produto")
    print("4 - Visualizar Estoque")
    print("5 - Sair")

    opcao = input("Escolha uma opção: ")

    match opcao:
        case "1":
            nome = input("Digite o nome do produto: ")
            validade = input("Digite a data de validade (dd/mm/aaaa): ")

            try:
                valor = float(input("Digite o valor total do produto: R$ "))
                estoque.append([nome, validade, valor])
                print("Produto cadastrado!")
            except ValueError:
                print("Valor inválido. O produto não foi cadastrado.")

        case "2":
            nome = input("Digite o nome do produto que deseja excluir: ")
            encontrado = False
            for produto in estoque:
                if produto[0].lower() == nome.lower():
                    estoque.remove(produto)
                    print("Produto excluído!")
                    encontrado = True
                    break
            if not encontrado:
                print("Produto não encontrado.")

        case "3":
            nome = input("Digite o nome do produto para atualizar: ")
            encontrado = False
            for produto in estoque:
                if produto[0].lower() == nome.lower():
                    try:
                        novo_valor = float(input("Digite o novo valor: R$ "))
                        produto[2] = novo_valor
                        print("Produto atualizado!")
                        encontrado = True
                    except ValueError:
                        print("Valor inválido. Atualização cancelada.")
                    break
            if not encontrado:
                print("Produto não encontrado.")

        case "4":
            if not estoque:
                print("Estoque vazio.")
            else:
                print("\n--- Produtos em Estoque ---")
                for i, produto in enumerate(estoque, start=1):
                    print(f"{i}. Nome: {produto[0]} | Validade: {produto[1]} | Valor: R$ {produto[2]:.2f}")

        case "5":
            print("Saindo do sistema...")

        case _:
            print("Opção inválida. Tente novamente.")   
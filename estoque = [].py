import sqlite3
from datetime import datetime
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Configurações do Banco
DB_FILE = "estoque.db"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def conectar_db():
    return sqlite3.connect(DB_FILE)

def criar_banco():
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidade TEXT NOT NULL,
            quantidade REAL NOT NULL DEFAULT 0.0,
            valor_unitario REAL NOT NULL DEFAULT 0.0
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            quantidade REAL NOT NULL,
            valor_unitario REAL NOT NULL,
            datahora TEXT NOT NULL,
            estoque_qtd_após REAL NOT NULL,
            total_estoque_após REAL NOT NULL,
            FOREIGN KEY (item_id) REFERENCES itens(id)
        );
    """)
    
    conn.commit()
    conn.close()

# =========================================================
# Funções Auxiliares
# =========================================================

def calcular_valor_total(conn):
    cur = conn.cursor()
    cur.execute("SELECT quantidade, valor_unitario FROM itens;")
    return sum((q or 0) * (v or 0) for q, v in cur.fetchall())

def entrada_float(prompt, minimo=None):
    while True:
        valor = input(prompt).replace(",", ".").strip()
        try:
            f = float(valor)
            if minimo is not None and f < minimo:
                print(f"Valor deve ser >= {minimo}")
                continue
            return f
        except ValueError:
            print("Entrada inválida.")

def exibir_item(row):
    _id, nome, cat, un, qtd, vu = row
    total = qtd * vu
    alerta = "⚠ ESTOQUE BAIXO" if qtd < 5 else ""
    print(f"[{_id}] {nome} | Cat: {cat} | Un: {un} | Qtd: {qtd:.2f} | "
          f"Vlr Unit: R$ {vu:.2f} | Total: R$ {total:.2f} {alerta}")

# =========================================================
# 1. Cadastro de Itens
# =========================================================

def cadastrar_item():
    print("\n=== Cadastro de Item ===")
    nome = input("Nome: ")
    cat = input("Categoria: ")
    un = input("Unidade (un, kg, L...): ")
    qtd = entrada_float("Quantidade inicial: ", minimo=0)
    vu = entrada_float("Valor unitário: R$ ", minimo=0)

    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO itens(nome, categoria, unidade, quantidade, valor_unitario)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, cat, un, qtd, vu))

    item_id = cur.lastrowid
    now = datetime.now().strftime(DATE_FORMAT)
    total_estoque = calcular_valor_total(conn)

    cur.execute("""
        INSERT INTO movimentos(item_id, tipo, quantidade, valor_unitario, datahora, estoque_qtd_após, total_estoque_após)
        VALUES (?, 'init', ?, ?, ?, ?, ?)
    """, (item_id, qtd, vu, now, qtd, total_estoque))

    conn.commit()
    conn.close()

    print("✔ Item cadastrado com sucesso!")

# =========================================================
# 2. Listagem
# =========================================================

def listar_itens():
    print("\n=== Itens Cadastrados ===")

    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM itens ORDER BY id;")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("Nenhum item cadastrado.")
    else:
        for r in rows:
            exibir_item(r)

# =========================================================
# 3. Buscar Itens
# =========================================================

def buscar_itens():
    termo = input("\nBuscar termo (nome/categoria): ").strip()
    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM itens 
        WHERE nome LIKE ? OR categoria LIKE ?
    """, (f"%{termo}%", f"%{termo}%"))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("Nenhum item encontrado.")
    else:
        for r in rows:
            exibir_item(r)

# =========================================================
# 4. Excluir Item
# =========================================================

def excluir_item():
    print("\n=== Excluir Item ===")

    conn = conectar_db()
    cur = conn.cursor()

    listar_itens()
    try:
        item_id = int(input("ID do item a excluir: "))
    except ValueError:
        print("ID inválido.")
        return

    cur.execute("SELECT nome FROM itens WHERE id = ?", (item_id,))
    if not cur.fetchone():
        print("Item não encontrado.")
        conn.close()
        return

    cur.execute("DELETE FROM movimentos WHERE item_id = ?", (item_id,))
    cur.execute("DELETE FROM itens WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    print("✔ Item excluído com sucesso!")

# =========================================================
# 5. Movimentação
# =========================================================

def selecionar_item(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM itens;")
    rows = cur.fetchall()

    if not rows:
        print("Nenhum item cadastrado.")
        return None

    for _id, nome in rows:
        print(f"[{_id}] {nome}")

    while True:
        try:
            i = int(input("Escolha o ID: "))
            cur.execute("SELECT id FROM itens WHERE id=?", (i,))
            if cur.fetchone():
                return i
            print("ID não encontrado.")
        except ValueError:
            print("Digite um número.")

def movimentar_estoque():
    print("\n=== Movimentar Estoque ===")
    conn = conectar_db()

    item_id = selecionar_item(conn)
    if item_id is None:
        conn.close()
        return

    tipo = ""
    while tipo not in ("E", "S"):
        tipo = input("Tipo (E=Entrada / S=Saída): ").upper().strip()

    qtd = entrada_float("Quantidade: ", minimo=0)

    cur = conn.cursor()
    cur.execute("SELECT quantidade, valor_unitario FROM itens WHERE id = ?", (item_id,))
    qtd_atual, vu = cur.fetchone()

    if tipo == "S" and qtd > qtd_atual:
        print("Saída maior que estoque atual.")
        conn.close()
        return

    nova_qtd = qtd_atual + qtd if tipo == "E" else qtd_atual - qtd
    mov_tipo = "entrada" if tipo == "E" else "saida"

    cur.execute("UPDATE itens SET quantidade=? WHERE id=?", (nova_qtd, item_id))
    total_estoque = calcular_valor_total(conn)
    now = datetime.now().strftime(DATE_FORMAT)

    cur.execute("""
        INSERT INTO movimentos(item_id, tipo, quantidade, valor_unitario, datahora, estoque_qtd_após, total_estoque_após)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, mov_tipo, qtd, vu, now, nova_qtd, total_estoque))

    conn.commit()
    conn.close()

    print("✔ Movimentação concluída!")

# =========================================================
# 6. Relatórios Gerenciais
# =========================================================

def relatorios_gerenciais():
    print("\n=== RELATÓRIOS GERENCIAIS ===")

    conn = conectar_db()
    cur = conn.cursor()

    # Custo total
    custo_total = calcular_valor_total(conn)

    # Itens com estoque baixo
    cur.execute("SELECT * FROM itens WHERE quantidade < 5;")
    baixos = cur.fetchall()

    # Giro de estoque = total de saídas
    cur.execute("SELECT SUM(quantidade) FROM movimentos WHERE tipo='saida';")
    giro = cur.fetchone()[0] or 0

    # Tempo médio de reposição
    cur.execute("""
        SELECT julianday(MAX(datahora)) - julianday(MIN(datahora))
        FROM movimentos
    """)
    dias = cur.fetchone()[0]
    tempo_medio = dias / giro if giro > 0 else 0

    # Estoque de segurança (modelo simples)
    estoque_seg = giro * 0.1  

    print(f"✔ Custo total em estoque: R$ {custo_total:.2f}")
    print(f"✔ Giro de estoque: {giro:.2f}")
    print(f"✔ Estoque de segurança sugerido: {estoque_seg:.2f}")
    print(f"✔ Tempo médio de reposição: {tempo_medio:.2f} dias\n")

    print("=== Itens com Estoque Baixo (<5) ===")
    if not baixos:
        print("Nenhum produto crítico.")
    else:
        for r in baixos:
            exibir_item(r)

    conn.close()

# =========================================================
# 7. Dashboard
# =========================================================

def dashboard():
    if plt is None:
        print("Matplotlib não instalado.")
        return

    conn = conectar_db()
    cur = conn.cursor()

    # --- Evolução do Estoque ---
    cur.execute("SELECT datahora, total_estoque_após FROM movimentos ORDER BY datahora;")
    dados = cur.fetchall()

    if dados:
        datas = [datetime.strptime(d, DATE_FORMAT) for d, _ in dados]
        valores = [v for _, v in dados]

        plt.figure()
        plt.plot(datas, valores, marker="o")
        plt.title("Evolução do Valor Total do Estoque")
        plt.xlabel("Data/Hora")
        plt.ylabel("Valor (R$)")
        plt.tight_layout()
        plt.show()

    # --- Curva ABC ---
    cur.execute("SELECT nome, quantidade * valor_unitario AS total FROM itens;")
    items = cur.fetchall()

    if items:
        items.sort(key=lambda x: x[1], reverse=True)

        nomes = [x[0] for x in items]
        valores = [x[1] for x in items]

        plt.figure()
        plt.bar(nomes, valores)
        plt.title("Curva ABC - Valor Acumulado por Produto")
        plt.xlabel("Produto")
        plt.ylabel("Valor (R$)")
        plt.xticks(rotation=30)
        plt.tight_layout()
        plt.show()

    conn.close()

# =========================================================
# 8. Menu
# =========================================================

def menu():
    while True:
        print("\n=== SISTEMA DE ESTOQUE ===")
        print("1) Cadastrar item")
        print("2) Listar itens")
        print("3) Buscar itens")
        print("4) Movimentar estoque")
        print("5) Relatórios gerenciais")
        print("6) Dashboard")
        print("7) Excluir item")
        print("0) Sair")
        opc = input("Opção: ").strip()

        if opc == "1":
            cadastrar_item()
        elif opc == "2":
            listar_itens()
        elif opc == "3":
            buscar_itens()
        elif opc == "4":
            movimentar_estoque()
        elif opc == "5":
            relatorios_gerenciais()
        elif opc == "6":
            dashboard()
        elif opc == "7":
            excluir_item()
        elif opc == "0":
            print("Encerrando...")
            break
        else:
            print("Opção inválida.")

# Execução
if __name__ == "__main__":
    criar_banco()
    menu()

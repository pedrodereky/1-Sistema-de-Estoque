import csv
import sqlite3
from datetime import datetime
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Configurações do Banco
DB_FILE = "estoque.db"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
ESTOQUE_MINIMO_PADRAO = 5.0

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
            valor_unitario REAL NOT NULL DEFAULT 0.0,
            estoque_minimo REAL NOT NULL DEFAULT 5.0
        );
    """)

    # Bancos criados antes desta versão não têm a coluna: adiciona sem perder dados.
    colunas = [linha[1] for linha in cursor.execute("PRAGMA table_info(itens);")]
    if "estoque_minimo" not in colunas:
        cursor.execute("ALTER TABLE itens ADD COLUMN estoque_minimo REAL NOT NULL DEFAULT 5.0;")
    
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

def tempo_medio_reposicao(conn):
    """
    Média, em dias, do intervalo entre entradas consecutivas do mesmo item
    (o cadastro conta como a primeira entrada). None se nenhum item foi reposto.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT item_id, datahora FROM movimentos
        WHERE tipo IN ('init', 'entrada')
        ORDER BY item_id, datahora
    """)
    intervalos = []
    anterior = {}
    for item_id, datahora in cur.fetchall():
        momento = datetime.strptime(datahora, DATE_FORMAT)
        if item_id in anterior:
            intervalos.append((momento - anterior[item_id]).total_seconds() / 86400)
        anterior[item_id] = momento
    return sum(intervalos) / len(intervalos) if intervalos else None

def entrada_float(prompt, minimo=None, padrao=None):
    while True:
        valor = input(prompt).replace(",", ".").strip()
        if valor == "" and padrao is not None:
            return padrao
        try:
            f = float(valor)
            if minimo is not None and f < minimo:
                print(f"Valor deve ser >= {minimo}")
                continue
            return f
        except ValueError:
            print("Entrada inválida.")

def exibir_item(row):
    _id, nome, cat, un, qtd, vu, minimo = row
    total = qtd * vu
    alerta = "⚠ ESTOQUE BAIXO" if qtd < minimo else ""
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
    est_min = entrada_float(f"Estoque mínimo (Enter = {ESTOQUE_MINIMO_PADRAO:g}): ",
                            minimo=0, padrao=ESTOQUE_MINIMO_PADRAO)

    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO itens(nome, categoria, unidade, quantidade, valor_unitario, estoque_minimo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nome, cat, un, qtd, vu, est_min))

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

    listar_itens()
    try:
        item_id = int(input("ID do item a excluir: "))
    except ValueError:
        print("ID inválido.")
        return

    conn = conectar_db()
    cur = conn.cursor()
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
    cur.execute("SELECT * FROM itens WHERE quantidade < estoque_minimo;")
    baixos = cur.fetchall()

    # Giro de estoque = total de saídas
    cur.execute("SELECT SUM(quantidade) FROM movimentos WHERE tipo='saida';")
    giro = cur.fetchone()[0] or 0

    tempo_medio = tempo_medio_reposicao(conn)

    # Estoque de segurança (modelo simples)
    estoque_seg = giro * 0.1  

    print(f"✔ Custo total em estoque: R$ {custo_total:.2f}")
    print(f"✔ Giro de estoque: {giro:.2f}")
    print(f"✔ Estoque de segurança sugerido: {estoque_seg:.2f}")
    if tempo_medio is None:
        print("✔ Tempo médio de reposição: sem reposições registradas ainda\n")
    else:
        print(f"✔ Tempo médio de reposição: {tempo_medio:.2f} dias\n")

    print("=== Itens abaixo do estoque mínimo ===")
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
# 8. Exportar CSV
# =========================================================

def exportar_csv(caminho="estoque.csv"):
    """
    Exporta os itens para CSV (separador ';' e vírgula decimal, que o Excel
    em português abre direto), com valor total e situação de cada item.
    Devolve a quantidade de itens exportados.
    """
    conn = conectar_db()
    rows = conn.execute(
        "SELECT id, nome, categoria, unidade, quantidade, valor_unitario, estoque_minimo FROM itens ORDER BY id"
    ).fetchall()
    conn.close()

    def br(valor):
        return f"{valor:.2f}".replace(".", ",")

    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(["ID", "Nome", "Categoria", "Unidade", "Quantidade", "Valor unitário",
                           "Valor total", "Estoque mínimo", "Situação"])
        for _id, nome, cat, un, qtd, vu, minimo in rows:
            situacao = "Estoque baixo" if qtd < minimo else "OK"
            escritor.writerow([_id, nome, cat, un, br(qtd), br(vu), br(qtd * vu), br(minimo), situacao])
    return len(rows)

# =========================================================
# 9. Menu
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
        print("8) Exportar CSV")
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
        elif opc == "8":
            caminho = input("Arquivo (Enter = estoque.csv): ").strip() or "estoque.csv"
            print(f"✔ {exportar_csv(caminho)} item(ns) exportado(s) para {caminho}")
        elif opc == "0":
            print("Encerrando...")
            break
        else:
            print("Opção inválida.")

# Execução
if __name__ == "__main__":
    criar_banco()
    menu()

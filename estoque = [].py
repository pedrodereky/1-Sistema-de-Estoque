import sqlite3
from datetime import datetime
try:
    import matplotlib.pyplot as plt # pyright: ignore[reportMissingModuleSource]
except ImportError:
    plt = None

# Configurações do Banco de Dados
DB_FILE = "estoque.db"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def conectar_db():
    """Retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_FILE)

def criar_banco():
    """
    Cria as tabelas 'itens' e 'movimentos' caso não existam.
    'itens': armazena os produtos cadastrados
    'movimentos': registra entradas e saídas de estoque
    """
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

# Funções de cálculo e utilitários

def calcular_valor_total(conn):
    """
    Calcula o valor total do estoque somando quantidade * valor unitário de cada item.
    """
    cur = conn.cursor()
    cur.execute("SELECT quantidade, valor_unitario FROM itens;")
    total = sum((q or 0.0) * (vu or 0.0) for q, vu in cur.fetchall())
    return total

def entrada_float(prompt, minimo=None):
    """
    Solicita ao usuário a entrada de um número float.
    Reexibe até que o valor seja válido e maior que 'minimo', se definido.
    """
    while True:
        val = input(prompt).replace(",", ".").strip()
        try:
            x = float(val)
            if minimo is not None and x < minimo:
                print(f"Valor deve ser >= {minimo}.")
                continue
            return x
        except ValueError:
            print("Entrada inválida. Digite um número válido.")

def exibir_item(row):
    """
    Recebe uma tupla de item e exibe seus detalhes de forma formatada.
    """
    _id, nome, cat, un, qtd, vu = row
    total_item = (qtd or 0.0) * (vu or 0.0)
    print(f"[{_id}] {nome} | Categoria: {cat} | Unidade: {un} | Quantidade: {qtd:.3f} | "
          f"Valor Unitário: R$ {vu:,.2f} | Total Item: R$ {total_item:,.2f}")

# Funções de Operações

def cadastrar_item():
    """Cadastra um novo item no estoque e registra movimentação inicial."""
    print("\n=== Cadastro de Item ===")
    nome = input("Nome do item: ").strip()
    categoria = input("Categoria: ").strip()
    unidade = input("Unidade (ex: un, kg, L): ").strip()
    quantidade = entrada_float("Quantidade inicial: ", minimo=0.0)
    valor_unitario = entrada_float("Valor unitário (R$): ", minimo=0.0)
    
    conn = conectar_db()
    cur = conn.cursor()
    
    # Insere o item na tabela 'itens'
    cur.execute("""
        INSERT INTO itens (nome, categoria, unidade, quantidade, valor_unitario)
        VALUES (?, ?, ?, ?, ?);
    """, (nome, categoria, unidade, quantidade, valor_unitario))
    
    item_id = cur.lastrowid
    now = datetime.now().strftime(DATE_FORMAT)
    total_estoque = calcular_valor_total(conn)
    
    # Registra a movimentação inicial
    cur.execute("""
        INSERT INTO movimentos (item_id, tipo, quantidade, valor_unitario, datahora, estoque_qtd_após, total_estoque_após)
        VALUES (?, 'init', ?, ?, ?, ?, ?);
    """, (item_id, quantidade, valor_unitario, now, quantidade, total_estoque))
    
    conn.commit()
    conn.close()
    print("Item cadastrado com sucesso!")

def listar_itens():
    """Exibe todos os itens cadastrados no estoque."""
    print("\n=== Itens Cadastrados ===")
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, categoria, unidade, quantidade, valor_unitario FROM itens ORDER BY id;")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("Nenhum item cadastrado.")
        return
    for r in rows:
        exibir_item(r)

def buscar_itens():
    """Busca itens por nome ou categoria contendo o termo fornecido pelo usuário."""
    print("\n=== Buscar Itens ===")
    termo = input("Buscar por (nome ou categoria): ").strip()
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nome, categoria, unidade, quantidade, valor_unitario
        FROM itens
        WHERE nome LIKE ? OR categoria LIKE ?
        ORDER BY nome;
    """, (f"%{termo}%", f"%{termo}%"))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("Nenhum item encontrado.")
        return
    for r in rows:
        exibir_item(r)

def selecionar_item(conn):
    """
    Exibe todos os itens com ID e solicita ao usuário escolher um.
    Retorna o ID do item selecionado ou None se não houver itens.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, nome FROM itens ORDER BY id;")
    rows = cur.fetchall()
    if not rows:
        print("Não há itens cadastrados.")
        return None
    print("\nSelecione o item pelo ID:")
    for _id, nome in rows:
        print(f"[{_id}] {nome}")
    while True:
        try:
            alvo = int(input("ID do item: ").strip())
            cur.execute("SELECT id FROM itens WHERE id = ?;", (alvo,))
            if cur.fetchone():
                return alvo
            print("ID inválido.")
        except ValueError:
            print("Digite um número inteiro para o ID.")

def movimentar_estoque():
    """Realiza entrada ou saída de produtos no estoque."""
    print("\n=== Movimentação de Estoque ===")
    conn = conectar_db()
    try:
        item_id = selecionar_item(conn)
        if item_id is None:
            conn.close()
            return
        
        tipo = ""
        while tipo not in ("E", "S"):
            tipo = input("Tipo (E = Entrada | S = Saída): ").strip().upper()
        
        qtd_mov = entrada_float("Quantidade: ", minimo=0.0)
        cur = conn.cursor()
        cur.execute("SELECT quantidade, valor_unitario FROM itens WHERE id = ?;", (item_id,))
        row = cur.fetchone()
        if not row:
            print("Item não encontrado.")
            conn.close()
            return
        
        qtd_atual, valor_unit = row
        if tipo == "E":
            nova_qtd = qtd_atual + qtd_mov
            mov_tipo = "entrada"
        else:
            if qtd_mov > qtd_atual:
                print(f"Erro: saída maior que estoque atual ({qtd_atual}). Operação cancelada.")
                conn.close()
                return
            nova_qtd = qtd_atual - qtd_mov
            mov_tipo = "saida"
        
        # Atualiza a quantidade no estoque
        cur.execute("""
            UPDATE itens SET quantidade = ?, valor_unitario = ?
            WHERE id = ?;
        """, (nova_qtd, valor_unit, item_id))
        
        total_estoque_após = calcular_valor_total(conn)
        now = datetime.now().strftime(DATE_FORMAT)
        
        # Registra a movimentação
        cur.execute("""
            INSERT INTO movimentos (item_id, tipo, quantidade, valor_unitario, datahora, estoque_qtd_após, total_estoque_após)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (item_id, mov_tipo, qtd_mov, valor_unit, now, nova_qtd, total_estoque_após))
        
        conn.commit()
        print("Movimentação registrada com sucesso!")
    finally:
        conn.close()

# =========================================================
# Dashboard com gráficos
# =========================================================
def dashboard():
    """Exibe gráficos de evolução do estoque (linha) e valor por categoria (barras)."""
    print("\n=== Dashboard ===")
    if plt is None:
        print("O módulo matplotlib não está instalado. Instale com: pip install matplotlib")
        return
    
    conn = conectar_db()
    cur = conn.cursor()
    
    # ===== Gráfico de linha: evolução do valor total do estoque =====
    cur.execute("SELECT datahora, total_estoque_após FROM movimentos ORDER BY datetime(datahora);")
    movs = cur.fetchall()
    if not movs:
        print("Sem movimentações para exibir.")
    else:
        datas_total = [datetime.strptime(d, DATE_FORMAT) for d, _ in movs]
        valores_total = [v for _, v in movs]
        plt.figure()
        plt.plot(datas_total, valores_total, marker='o', linestyle='-', color='blue')
        plt.xlabel("Data/Hora")
        plt.ylabel("Valor total do estoque (R$)")
        plt.title("Evolução do Valor Total do Estoque")
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.show()
    
    # ===== Gráfico de barras: valor total por categoria =====
    cur.execute("SELECT categoria, SUM(quantidade * valor_unitario) FROM itens GROUP BY categoria;")
    cat_vals = cur.fetchall()
    if cat_vals:
        categorias = [c for c, _ in cat_vals]
        valores = [v for _, v in cat_vals]
        plt.figure()
        plt.bar(categorias, valores, color='green')
        plt.xlabel("Categoria")
        plt.ylabel("Valor total (R$)")
        plt.title("Valor Total por Categoria")
        plt.tight_layout()
        plt.show()
    
    conn.close()

# =========================================================
# Menu principal
# =========================================================
def menu():
    """Exibe o menu principal e chama funções correspondentes à escolha do usuário."""
    while True:
        print("\n=== SISTEMA DE ESTOQUE ===")
        print("1) Cadastrar item")
        print("2) Listar itens")
        print("3) Buscar itens")
        print("4) Movimentar estoque")
        print("5) Dashboard")
        print("0) Sair")
        escolha = input("Escolha uma opção: ").strip()
        
        if escolha == "1":
            cadastrar_item()
        elif escolha == "2":
            listar_itens()
        elif escolha == "3":
            buscar_itens()
        elif escolha == "4":
            movimentar_estoque()
        elif escolha == "5":
            dashboard()
        elif escolha == "0":
            print("Saindo do sistema...")
            break
        else:
            print("Opção inválida.")

# Execução principal
if __name__ == "__main__":
    criar_banco()
    menu()

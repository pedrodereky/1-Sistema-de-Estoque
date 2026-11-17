import sqlite3

import pytest

import estoque


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    """Cada teste usa um banco SQLite novo, numa pasta temporária."""
    monkeypatch.setattr(estoque, "DB_FILE", str(tmp_path / "estoque.db"))
    estoque.criar_banco()


def responder(monkeypatch, *respostas):
    """Simula o que o usuário digitaria, em ordem."""
    fila = iter(respostas)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(fila))


def itens():
    with sqlite3.connect(estoque.DB_FILE) as conn:
        return conn.execute("SELECT nome, quantidade, valor_unitario FROM itens").fetchall()


def minimos():
    with sqlite3.connect(estoque.DB_FILE) as conn:
        return conn.execute("SELECT nome, estoque_minimo FROM itens ORDER BY id").fetchall()


def movimentos():
    with sqlite3.connect(estoque.DB_FILE) as conn:
        return conn.execute("SELECT tipo, quantidade, estoque_qtd_após FROM movimentos ORDER BY id").fetchall()


def test_cadastro_aceita_virgula_decimal_e_registra_movimento_inicial(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5,50", "")
    estoque.cadastrar_item()
    assert itens() == [("Arroz", 10.0, 5.5)]
    assert movimentos() == [("init", 10.0, 10.0)]


def test_entrada_float_repete_ate_receber_valor_valido(monkeypatch):
    responder(monkeypatch, "abc", "-1", "2,5")
    assert estoque.entrada_float("Valor: ", minimo=0) == 2.5


def test_valor_total_soma_quantidade_vezes_valor(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "Feijão", "Alimentos", "kg", "4", "8", "")
    estoque.cadastrar_item()
    with sqlite3.connect(estoque.DB_FILE) as conn:
        assert estoque.calcular_valor_total(conn) == 10 * 5 + 4 * 8


def test_entrada_e_saida_atualizam_saldo(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "1", "E", "5")
    estoque.movimentar_estoque()
    responder(monkeypatch, "1", "S", "12")
    estoque.movimentar_estoque()
    assert itens()[0][1] == 3.0
    assert movimentos()[1:] == [("entrada", 5.0, 15.0), ("saida", 12.0, 3.0)]


def test_saida_maior_que_o_saldo_e_recusada(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "1", "S", "3")
    estoque.movimentar_estoque()
    assert itens()[0][1] == 2.0
    assert len(movimentos()) == 1


def test_excluir_remove_item_e_historico(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "1")
    estoque.excluir_item()
    assert itens() == []
    assert movimentos() == []


def test_excluir_com_id_invalido_nao_altera_nada(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "xyz")
    estoque.excluir_item()
    assert len(itens()) == 1


def test_estoque_minimo_padrao_e_personalizado(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5", "")
    estoque.cadastrar_item()
    responder(monkeypatch, "Parafuso", "Ferragens", "un", "100", "0,10", "200")
    estoque.cadastrar_item()
    assert minimos() == [("Arroz", 5.0), ("Parafuso", 200.0)]


def test_alerta_usa_o_minimo_de_cada_item(monkeypatch, capsys):
    responder(monkeypatch, "Parafuso", "Ferragens", "un", "100", "0,10", "200")
    estoque.cadastrar_item()
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "3", "5", "2")
    estoque.cadastrar_item()
    capsys.readouterr()
    estoque.listar_itens()
    linhas = capsys.readouterr().out.splitlines()
    assert "ESTOQUE BAIXO" in next(l for l in linhas if "Parafuso" in l)
    assert "ESTOQUE BAIXO" not in next(l for l in linhas if "Arroz" in l)


def test_banco_antigo_ganha_a_coluna_sem_perder_dados(tmp_path, monkeypatch):
    antigo = tmp_path / "antigo.db"
    with sqlite3.connect(antigo) as conn:
        conn.execute("""CREATE TABLE itens (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL,
            categoria TEXT NOT NULL, unidade TEXT NOT NULL, quantidade REAL NOT NULL DEFAULT 0.0,
            valor_unitario REAL NOT NULL DEFAULT 0.0)""")
        conn.execute("INSERT INTO itens (nome, categoria, unidade, quantidade, valor_unitario) VALUES ('Sal', 'Alimentos', 'kg', 1, 2)")
    monkeypatch.setattr(estoque, "DB_FILE", str(antigo))
    estoque.criar_banco()
    assert minimos() == [("Sal", 5.0)]


def registrar(item_id, tipo, datahora):
    with sqlite3.connect(estoque.DB_FILE) as conn:
        conn.execute(
            "INSERT INTO movimentos (item_id, tipo, quantidade, valor_unitario, datahora, estoque_qtd_após, total_estoque_após)"
            " VALUES (?, ?, 1, 1, ?, 0, 0)", (item_id, tipo, datahora))


def test_tempo_medio_de_reposicao_entre_entradas_do_mesmo_item():
    # Item 1: cadastro dia 1, entradas nos dias 5 e 11 -> intervalos de 4 e 6 dias.
    # Item 2: cadastro dia 2, entrada dia 4 -> intervalo de 2 dias. Saídas não contam.
    registrar(1, "init", "2026-01-01 08:00:00")
    registrar(1, "saida", "2026-01-03 08:00:00")
    registrar(1, "entrada", "2026-01-05 08:00:00")
    registrar(1, "entrada", "2026-01-11 08:00:00")
    registrar(2, "init", "2026-01-02 08:00:00")
    registrar(2, "entrada", "2026-01-04 08:00:00")
    with sqlite3.connect(estoque.DB_FILE) as conn:
        assert estoque.tempo_medio_reposicao(conn) == pytest.approx((4 + 6 + 2) / 3)


def test_tempo_medio_sem_reposicao_e_none():
    registrar(1, "init", "2026-01-01 08:00:00")
    registrar(1, "saida", "2026-01-09 08:00:00")
    with sqlite3.connect(estoque.DB_FILE) as conn:
        assert estoque.tempo_medio_reposicao(conn) is None

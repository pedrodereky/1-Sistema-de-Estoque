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


def movimentos():
    with sqlite3.connect(estoque.DB_FILE) as conn:
        return conn.execute("SELECT tipo, quantidade, estoque_qtd_após FROM movimentos ORDER BY id").fetchall()


def test_cadastro_aceita_virgula_decimal_e_registra_movimento_inicial(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5,50")
    estoque.cadastrar_item()
    assert itens() == [("Arroz", 10.0, 5.5)]
    assert movimentos() == [("init", 10.0, 10.0)]


def test_entrada_float_repete_ate_receber_valor_valido(monkeypatch):
    responder(monkeypatch, "abc", "-1", "2,5")
    assert estoque.entrada_float("Valor: ", minimo=0) == 2.5


def test_valor_total_soma_quantidade_vezes_valor(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5")
    estoque.cadastrar_item()
    responder(monkeypatch, "Feijão", "Alimentos", "kg", "4", "8")
    estoque.cadastrar_item()
    with sqlite3.connect(estoque.DB_FILE) as conn:
        assert estoque.calcular_valor_total(conn) == 10 * 5 + 4 * 8


def test_entrada_e_saida_atualizam_saldo(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "10", "5")
    estoque.cadastrar_item()
    responder(monkeypatch, "1", "E", "5")
    estoque.movimentar_estoque()
    responder(monkeypatch, "1", "S", "12")
    estoque.movimentar_estoque()
    assert itens()[0][1] == 3.0
    assert movimentos()[1:] == [("entrada", 5.0, 15.0), ("saida", 12.0, 3.0)]


def test_saida_maior_que_o_saldo_e_recusada(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5")
    estoque.cadastrar_item()
    responder(monkeypatch, "1", "S", "3")
    estoque.movimentar_estoque()
    assert itens()[0][1] == 2.0
    assert len(movimentos()) == 1


def test_excluir_remove_item_e_historico(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5")
    estoque.cadastrar_item()
    responder(monkeypatch, "1")
    estoque.excluir_item()
    assert itens() == []
    assert movimentos() == []


def test_excluir_com_id_invalido_nao_altera_nada(monkeypatch):
    responder(monkeypatch, "Arroz", "Alimentos", "kg", "2", "5")
    estoque.cadastrar_item()
    responder(monkeypatch, "xyz")
    estoque.excluir_item()
    assert len(itens()) == 1

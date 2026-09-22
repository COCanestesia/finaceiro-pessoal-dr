import pytest
from financeiro_dr.core.financeiro.money import format_money,parse_money

@pytest.mark.parametrize(("text","expected"),[("1.234,56",123456),("1234,56",123456),("1234.56",123456),("0,01",1),("R$ 2.000,00",200000),("10",1000)])
def test_parse_money(text,expected): assert parse_money(text)==expected

def test_parse_money_rounds_half_up_to_cents(): assert parse_money("1,005")==101

def test_format_money_uses_brazilian_separators():
    assert format_money(123456)=="R$ 1.234,56"; assert format_money(1)=="R$ 0,01"

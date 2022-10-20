# -*- coding: utf-8 -*-

from .classes import PgConn

def db_login():
    """Logowanie do bazy danych."""
    db = PgConn()
    if not db:
        print("Nie udało się połączyć z bazą danych.")
        return False
    sql = 'SELECT version()'
    res = db.query_sel(sql, False)
    if not res:
        print("Nie udało się połączyć z bazą danych.")
        return False
    return True

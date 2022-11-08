# -*- coding: utf-8 -*-

import pandas as pd

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

def df_from_db(sql, cols=[]):
    """Zwraca dataframe ze wskazanymi kolumnami i danymi z db pobranymi z kwerendy sql."""
    empty_df = pd.DataFrame(columns=cols)
    db = PgConn()
    if db:
        df = db.query_pd(sql, cols)
        if isinstance(df, pd.DataFrame):
            return df if len(df) > 0 else empty_df
        else:
            return empty_df
    else:
        return empty_df

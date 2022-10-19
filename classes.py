#!/usr/bin/python

import os

from configparser import ConfigParser

DB_SOURCE = "PGI"

class CfgPars(ConfigParser):
    """Parser parametrów konfiguracji połączenia z bazą danych."""
    def __init__(self, filename='database.ini', section=DB_SOURCE):
        super().__init__()
        self.filename = self.resolve(filename)
        self.section = section
        self.read(self.filename)  # Pobranie zawartości pliku
        if not self.has_section(section):
            raise AttributeError(f'Sekcja {section} nie istnieje w pliku {filename}!')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return True

    def resolve(self, name):
        """Zwraca ścieżkę do folderu plugina wraz z nazwą pliku .ini."""
        basepath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(basepath, name)

    def psycopg2(self):
        """Przekazanie parametrów połączenia z db za pośrednictwem Psycopg2."""
        db = {}  # Stworzenie słownika
        # Ładowanie parametrów do słownika
        params = self.items(self.section)
        for param in params:
            db[param[0]] = param[1]
        return db

    def uri(self):
        """Przekazanie parametrów połączenia z db za pośrednictwem Uri."""
        result = ""
        # Ładowanie parametrów do słownika
        params = self.items(self.section)
        for key, val in params:
            if key == "database":
                key = "dbname"
                val = str('"' + val + '"')
            elif key == "user":
                val = str('"' + val + '"')
            result += key + "=" + val + " "
        return result

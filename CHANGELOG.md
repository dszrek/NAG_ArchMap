# Changelog (dziennik zmian):

## [0.3.0] - 2022-10-27

### Zmieniono
- Nazwy wczytywanych do projektu warstw rastrowych map nie są już ich numerami ID, ale pochodzą od tytułu mapy.
- Nazwy tworzonych w legendzie projektu grup warstw, które grupują mapy z danej dokumentacji nie pochodzą już od nr CBDG, ale tworzone są z kombinacji słowa kluczowego (tagu) i roku wykonania dokumentacji.

## [0.2.0] - 2022-10-26

### Dodano
- Przed uruchomieniem wtyczki sprawdzany jest dostęp do sieci wewnętrznej PIG-PIB oraz uprawnienia odczytu folderu "\\pgi.local\pig_dfs2\Projekty\CAG\Dokumenty CAG" i jego podfolderów. Brak powyższych uniemożliwia uruchomienie wtyczki.
- Uruchamianie wtyczki z pustym lub otwartym "własnym" plikiem projektowym. Po uruchomieniu wtyczki tworzy się w legendzie projektu (drzewko w panelu Warstwy) grupa warstw "NAG_ArchMap", do której wczytywane są warstwy rastrowe z plikami .jpg (mapami). Jeśli w otwartym projekcie znajduje się już grupa "NAG_ArchMap", wtyczka się z nią zsynchronizuje.
- Interfejs wtyczki zorganizowany jest w postaci dockwidget'u, złożonego z 4 części: wyszukiwarka dokumentacji, tabela z listą wyszukanych dokumentacji, ramka ze szczegółowymi informacjami tekstowymi o wybranej dokumentacji i tabela z listą map przypisanych do wybranej dokumentacji.
- Wyszukiwanie dokumentacji odbywa się poprzez wpisanie frazy w polu tekstowym i kliknięcie przycisku "Wyszukaj". Baza danych zwraca wynik w oparciu o występowanie szukanej frazy w nazwach złóż z bazy MIDAS, słowach kluczowych (tagów) przypisanych do dokumentacji oraz tytułach dokumentacji. Wynik wyszukiwania pojawia się w tabeli dokumentacji - lista sortowana jest w oparciu o ranking istotności, który tworzony jest dzięki funkcji wykonywanej po stronie serwera.
- Po wybraniu dokumentacji z listy, wyświetlane są o niej informacje szczegółowe, a w najniższej tabeli pojawia się lista przypisanych do wybranej dokumentacji dostępnych map.
- Zaznaczenie pola wyboru (checkbox'u) w wierszu tabeli map powoduje wczytanie do projektu QGIS warstwy rastrowej z plikiem graficznym mapy. Odznaczenie pola wyboru usuwa warstwę rastrową z projektu.
- Usunięcie warstwy (lub grupy warstw) z poziomu legendy (panel Warstwy w QGIS), automatycznie aktualizuje informacje zawarte w tabeli wtyczki.

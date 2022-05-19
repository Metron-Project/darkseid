import pytest

test_articles = [
    pytest.param("The Champions & Inhumans", "Test string with '&'", "Champions Inhumans"),
    pytest.param("Justice League", "Test string with no articles", "Justice League"),
    pytest.param("The X-Men", "Test string with leading 'The'", "X-Men"),
]

test_file_names = [
    pytest.param(
        "Batman '89 (2021) (Webrip) (The Last Kryptonian-DCP).cbr",
        "year in title without issue",
        {
            "issue": "",
            "series": "Batman '89",
            "volume": "",
            "year": "2021",
            "remainder": "(Webrip) (The Last Kryptonian-DCP)",
            "issue_count": "",
        },
    ),
    (
        "Batman_-_Superman_020_(2021)_(digital)_(NeverAngel-Empire).cbr",
        "underscores",
        {
            "issue": "20",
            "series": "Batman - Superman",
            "volume": "",
            "year": "2021",
            "remainder": "(digital) (NeverAngel-Empire)",
            "issue_count": "",
        },
    ),
    (
        "Amazing Spider-Man 078.BEY (2022) (Digital) (Zone-Empire).cbr",
        "number issue with extra",
        {
            "issue": "78.BEY",
            "series": "Amazing Spider-Man",
            "title": "",
            "volume": "",
            "year": "2022",
            "remainder": "(Digital) (Zone-Empire)",
            "issue_count": "",
        },
    ),
    (
        "Farmhand 016 (2022) (Digital) (Zone-Empire).cbz",
        "Standard formatting",
        {
            "issue": "16",
            "series": "Farmhand",
            "title": "",
            "volume": "",
            "year": "2022",
            "remainder": "(Digital) (Zone-Empire)",
            "issue_count": "",
        },
    ),
    (
        "Aquaman 80th Anniversary 100-Page Super Spectacular (2021) 001 "
        "(2021) (Digital) (BlackManta-Empire).cbz",
        "numbers in series",
        {
            "issue": "1",
            "series": "Aquaman 80th Anniversary 100-Page Super Spectacular",
            "volume": "2021",
            "year": "2021",
            "remainder": "(Digital) (BlackManta-Empire)",
            "issue_count": "",
        },
    ),
    (
        "Batman_-_Superman_020_(2021)_(digital)_(NeverAngel-Empire).cbr",
        "underscores",
        {
            "issue": "20",
            "series": "Batman - Superman",
            "volume": "",
            "year": "2021",
            "remainder": "(digital) (NeverAngel-Empire)",
            "issue_count": "",
        },
    ),
    (
        "Blade Runner 2029 006 (2021) (3 covers) (digital) (Son of Ultron-Empire).cbr",
        "year before issue",
        {
            "issue": "6",
            "series": "Blade Runner 2029",
            "volume": "",
            "year": "2021",
            "remainder": "(3 covers) (digital) (Son of Ultron-Empire)",
            "issue_count": "",
        },
    ),
    (
        "The Defenders v1 058 (1978) (digital).cbz",
        "",
        {
            "issue": "58",
            "series": "The Defenders",
            "volume": "1",
            "year": "1978",
            "remainder": "(digital)",
            "issue_count": "",
        },
    ),
    pytest.param(
        " X-Men-V1-067.cbr",
        "hyphen separated with hyphen in series",
        {
            "issue": "67",
            "series": "X-Men",
            "title": "",
            "volume": "1",
            "year": "",
            "remainder": "",
            "issue_count": "",
        },
        marks=pytest.mark.xfail,
    ),
    pytest.param(
        "Marvel Previews 002 (January 2022) (Digital-Empire).cbr",
        "(month year)",
        {
            "issue": "2",
            "series": "Marvel Previews",
            "volume": "",
            "year": "2022",
            "remainder": "(Digital-Empire)",
            "issue_count": "",
        },
        marks=pytest.mark.xfail,
    ),
]

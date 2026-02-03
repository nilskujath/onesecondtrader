import json
import sqlite3
import zipfile

from onesecondtrader.secmaster.utils import _ingest_symbology, create_secmaster_db


def _make_db(tmp_path):
    db_path = tmp_path / "secmaster.db"
    create_secmaster_db(db_path)
    return db_path


def _make_publisher(con):
    cur = con.cursor()
    cur.execute(
        "INSERT INTO publishers (name, dataset, venue) VALUES (?, ?, ?)",
        ("databento", "X.TEST", "X"),
    )
    return int(cur.lastrowid)


def test_instruments_check_requires_symbol_or_source_id(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")

    publisher_id = _make_publisher(con)

    with con:
        try:
            con.execute(
                "INSERT INTO instruments (publisher_ref) VALUES (?)", (publisher_id,)
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected CHECK constraint to fail")


def test_instruments_symbol_type_is_not_null_and_defaults(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    with con:
        try:
            con.execute(
                "INSERT INTO instruments (publisher_ref, symbol) VALUES (?, ?)",
                (publisher_id, "AAPL"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected CHECK constraint to fail")

    with con:
        con.execute(
            "INSERT INTO instruments (publisher_ref, symbol, symbol_type) VALUES (?, ?, ?)",
            (publisher_id, "AAPL", "ticker"),
        )


def test_instruments_unique_symbol_symbol_type(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    with con:
        con.execute(
            "INSERT INTO instruments (publisher_ref, symbol, symbol_type) VALUES (?, ?, ?)",
            (publisher_id, "AAPL", "ticker"),
        )

    with con:
        try:
            con.execute(
                "INSERT INTO instruments (publisher_ref, symbol, symbol_type) VALUES (?, ?, ?)",
                (publisher_id, "AAPL", "ticker"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected UNIQUE constraint to fail")


def test_instruments_numeric_only_allows_null_symbol_type(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    with con:
        con.execute(
            "INSERT INTO instruments (publisher_ref, source_instrument_id) VALUES (?, ?)",
            (publisher_id, 123),
        )


def test_symbology_requires_matching_instrument(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    with con:
        try:
            con.execute(
                "INSERT INTO symbology "
                "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (publisher_id, "AAPL", "raw_symbol", 123, "2020-01-01", "2020-12-31"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected FK constraint to fail")

    with con:
        con.execute(
            "INSERT INTO instruments (publisher_ref, source_instrument_id) VALUES (?, ?)",
            (publisher_id, 123),
        )
        con.execute(
            "INSERT INTO symbology "
            "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (publisher_id, "AAPL", "raw_symbol", 123, "2020-01-01", "2020-12-31"),
        )


def test_ingest_symbology_creates_instruments_for_source_ids(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    symbology_json = {
        "result": {
            "AAPL": [
                {"s": 1001, "d0": "2020-01-01", "d1": "2020-12-31"},
                {"s": 1001, "d0": "2021-01-01", "d1": "2021-12-31"},
            ],
            "MSFT": [
                {"s": 2002, "d0": "2020-01-01", "d1": "2020-12-31"},
            ],
        }
    }

    json_path = tmp_path / "symbology.json"
    json_path.write_text(json.dumps(symbology_json), encoding="utf-8")

    with con:
        seen = _ingest_symbology(json_path, con, publisher_id)

    assert seen == 3

    instrument_count = con.execute(
        "SELECT COUNT(*) FROM instruments WHERE publisher_ref = ?",
        (publisher_id,),
    ).fetchone()[0]
    assert instrument_count == 2

    symbology_count = con.execute(
        "SELECT COUNT(*) FROM symbology WHERE publisher_ref = ?",
        (publisher_id,),
    ).fetchone()[0]
    assert symbology_count == 3


def test_ingest_symbology_accepts_symbol_type_param(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    symbology_json = {
        "result": {
            "AAPL": [
                {"s": 1001, "d0": "2020-01-01", "d1": "2020-12-31"},
            ],
        }
    }

    json_path = tmp_path / "symbology.json"
    json_path.write_text(json.dumps(symbology_json), encoding="utf-8")

    with con:
        seen = _ingest_symbology(json_path, con, publisher_id, symbol_type="ticker")

    assert seen == 1
    row = con.execute(
        "SELECT symbol_type FROM symbology WHERE publisher_ref = ? AND symbol = ?",
        (publisher_id, "AAPL"),
    ).fetchone()
    assert row[0] == "ticker"


def test_extract_dataset_info_finds_nested_metadata(tmp_path):
    from onesecondtrader.secmaster.utils import _extract_dataset_info

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "nested/metadata.json",
            json.dumps({"query": {"dataset": "XNAS.ITCH"}}),
        )

    with zipfile.ZipFile(zip_path, "r") as zf:
        dataset, venue = _extract_dataset_info(zf)

    assert dataset == "XNAS.ITCH"
    assert venue == "XNAS"


def test_extract_dataset_info_missing_metadata_requires_override(tmp_path):
    from onesecondtrader.secmaster.utils import _extract_dataset_info

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nested/other.json", json.dumps({"x": 1}))

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            _extract_dataset_info(zf)
        except ValueError as e:
            assert "missing metadata.json" in str(e)
        else:
            raise AssertionError("Expected ValueError")

    with zipfile.ZipFile(zip_path, "r") as zf:
        dataset, venue = _extract_dataset_info(zf, dataset_override="XNAS.ITCH")
    assert dataset == "XNAS.ITCH"
    assert venue == "XNAS"


def test_zip_find_member_raises_on_duplicates_by_default(tmp_path):
    from onesecondtrader.secmaster.utils import _zip_find_member

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a/metadata.json", json.dumps({"query": {"dataset": "XNAS.ITCH"}}))
        zf.writestr("b/metadata.json", json.dumps({"query": {"dataset": "XNAS.ITCH"}}))

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            _zip_find_member(zf, "metadata.json")
        except ValueError as e:
            assert "Multiple metadata.json members" in str(e)
        else:
            raise AssertionError("Expected ValueError")

    with zipfile.ZipFile(zip_path, "r") as zf:
        member = _zip_find_member(zf, "metadata.json", allow_multiple=True)
    assert member == "a/metadata.json"


def test_ingest_symbology_validation_has_context(tmp_path):
    db_path = _make_db(tmp_path)

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    json_path = tmp_path / "symbology.json"
    json_path.write_text(json.dumps({"result": {"ES": [{"s": 1, "d0": "2020-01-01"}]}}))

    try:
        with con:
            _ingest_symbology(json_path, con, publisher_id)
    except ValueError as e:
        msg = str(e)
        assert (
            "symbol='ES'" in msg
            or 'symbol="ES"' in msg
            or "symbol=\u0027ES\u0027" in msg
        )
        assert "index=0" in msg
        assert "d1" in msg
    else:
        raise AssertionError("Expected ValueError")


def test_ingest_databento_dbn_requires_dataset_metadata(tmp_path, monkeypatch):
    from onesecondtrader.secmaster.utils import ingest_databento_dbn

    class _Meta:
        dataset = ""

    class _Store:
        metadata = _Meta()

    def _from_file(_path):
        return _Store()

    monkeypatch.setattr(
        "onesecondtrader.secmaster.utils.databento.DBNStore.from_file", _from_file
    )

    db_path = _make_db(tmp_path)
    dbn_path = tmp_path / "sample.dbn"
    dbn_path.write_bytes(b"x")

    try:
        ingest_databento_dbn(dbn_path, db_path)
    except ValueError as e:
        assert "missing dataset" in str(e)
    else:
        raise AssertionError("Expected ValueError")

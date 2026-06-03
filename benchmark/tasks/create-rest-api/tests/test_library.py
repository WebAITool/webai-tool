"""Tests for create-rest-api task."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def client():
    import importlib, main
    importlib.reload(main)
    return TestClient(main.app)


def test_create_book(client):
    resp = client.post("/books", json={
        "title": "1984", "author": "Orwell", "genre": "dystopia", "year": 1949, "isbn": "978-0451524346"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "1984"
    assert "id" in data


def test_list_books(client):
    client.post("/books", json={"title": "Book1", "author": "A", "genre": "fic", "year": 2000, "isbn": "111"})
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_filter_books_by_author(client):
    client.post("/books", json={"title": "B1", "author": "Orwell", "genre": "fic", "year": 1949, "isbn": "222"})
    client.post("/books", json={"title": "B2", "author": "Tolstoy", "genre": "fic", "year": 1869, "isbn": "333"})
    resp = client.get("/books?author=Orwell")
    assert len(resp.json()) == 1


def test_get_book(client):
    created = client.post("/books", json={"title": "Test", "author": "X", "genre": "y", "year": 2000, "isbn": "444"}).json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test"


def test_update_book(client):
    created = client.post("/books", json={"title": "Old", "author": "X", "genre": "y", "year": 2000, "isbn": "555"}).json()
    resp = client.put(f"/books/{created['id']}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_delete_book(client):
    created = client.post("/books", json={"title": "Del", "author": "X", "genre": "y", "year": 2000, "isbn": "666"}).json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code in (200, 204)


def test_isbn_unique(client):
    client.post("/books", json={"title": "B1", "author": "A", "genre": "g", "year": 2000, "isbn": "777"})
    resp = client.post("/books", json={"title": "B2", "author": "A", "genre": "g", "year": 2000, "isbn": "777"})
    assert resp.status_code in (400, 409)


def test_create_member(client):
    resp = client.post("/members", json={"name": "Alice", "email": "alice@test.com", "phone": "123"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Alice"


def test_email_unique(client):
    client.post("/members", json={"name": "A", "email": "same@test.com", "phone": "1"})
    resp = client.post("/members", json={"name": "B", "email": "same@test.com", "phone": "2"})
    assert resp.status_code in (400, 409)


def test_borrow_book(client):
    book = client.post("/books", json={"title": "B", "author": "A", "genre": "g", "year": 2000, "isbn": "888"}).json()
    member = client.post("/members", json={"name": "M", "email": "m@t.com", "phone": "3"}).json()
    resp = client.post("/borrow", json={"book_id": book["id"], "member_id": member["id"]})
    assert resp.status_code == 200


def test_cannot_borrow_twice(client):
    book = client.post("/books", json={"title": "B", "author": "A", "genre": "g", "year": 2000, "isbn": "999"}).json()
    member = client.post("/members", json={"name": "M", "email": "m2@t.com", "phone": "4"}).json()
    client.post("/borrow", json={"book_id": book["id"], "member_id": member["id"]})
    resp = client.post("/borrow", json={"book_id": book["id"], "member_id": member["id"]})
    assert resp.status_code == 400


def test_max_5_borrows(client):
    member = client.post("/members", json={"name": "M", "email": "m3@t.com", "phone": "5"}).json()
    for i in range(5):
        book = client.post("/books", json={"title": f"B{i}", "author": "A", "genre": "g", "year": 2000, "isbn": f"max{i}"}).json()
        client.post("/borrow", json={"book_id": book["id"], "member_id": member["id"]})
    # 6th should fail
    book6 = client.post("/books", json={"title": "B6", "author": "A", "genre": "g", "year": 2000, "isbn": "max6"}).json()
    resp = client.post("/borrow", json={"book_id": book6["id"], "member_id": member["id"]})
    assert resp.status_code == 400


def test_return_book(client):
    book = client.post("/books", json={"title": "R", "author": "A", "genre": "g", "year": 2000, "isbn": "ret1"}).json()
    member = client.post("/members", json={"name": "M", "email": "m4@t.com", "phone": "6"}).json()
    client.post("/borrow", json={"book_id": book["id"], "member_id": member["id"]})
    resp = client.post("/return", json={"book_id": book["id"]})
    assert resp.status_code == 200


def test_return_unborrowed(client):
    book = client.post("/books", json={"title": "U", "author": "A", "genre": "g", "year": 2000, "isbn": "unb1"}).json()
    resp = client.post("/return", json={"book_id": book["id"]})
    assert resp.status_code == 400


"""Full library REST API implementation."""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid

app = FastAPI()

# In-memory storage
books_db = {}
members_db = {}
borrows_db = {}  # book_id -> member_id (currently borrowed)

# Helpers for IDs
def generate_id():
    return str(uuid.uuid4())

# ---- Pydantic models ----
class BookCreate(BaseModel):
    title: str
    author: str
    genre: Optional[str] = None
    isbn: str


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    isbn: Optional[str] = None

class Book(BaseModel):
    id: str
    title: str
    author: str
    genre: Optional[str] = None
    isbn: str
    available: bool = True

class MemberCreate(BaseModel):
    name: str
    email: str

class Member(BaseModel):
    id: str
    name: str
    email: str
    borrowed_books: List[str] = []

class BorrowRequest(BaseModel):
    member_id: str
    book_id: str

class ReturnRequest(BaseModel):
    book_id: str

# ---- Books endpoints ----
@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    for existing in books_db.values():
        if existing["isbn"] == book.isbn:
            raise HTTPException(status_code=400, detail="ISBN already exists")
    new_id = generate_id()
    books_db[new_id] = {
        "id": new_id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "isbn": book.isbn,
        "available": True
    }
    return books_db[new_id]

@app.get("/books")
def list_books(author: Optional[str] = Query(None), genre: Optional[str] = Query(None)):
    result = list(books_db.values())
    if author:
        result = [b for b in result if b["author"].lower() == author.lower()]
    if genre:
        result = [b for b in result if b.get("genre") and b["genre"].lower() == genre.lower()]
    return result

@app.get("/books/{book_id}")
def get_book(book_id: str):
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    return books_db[book_id]

@app.put("/books/{book_id}")
def update_book(book_id: str, book: BookUpdate):
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    existing = books_db[book_id]
    # Check ISBN uniqueness excluding self if isbn is provided
    if book.isbn is not None:
        for bid, b in books_db.items():
            if b["isbn"] == book.isbn and bid != book_id:
                raise HTTPException(status_code=400, detail="ISBN already exists")
        existing["isbn"] = book.isbn
    if book.title is not None:
        existing["title"] = book.title
    if book.author is not None:
        existing["author"] = book.author
    if book.genre is not None:
        existing["genre"] = book.genre
    return existing

@app.delete("/books/{book_id}", status_code=200)
def delete_book(book_id: str):
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    del books_db[book_id]
    return {"detail": "Book deleted"}

# ---- Members endpoints ----
@app.post("/members", status_code=201)
def create_member(member: MemberCreate):
    for existing in members_db.values():
        if existing["email"] == member.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    new_id = generate_id()
    members_db[new_id] = {
        "id": new_id,
        "name": member.name,
        "email": member.email,
        "borrowed_books": []
    }
    return members_db[new_id]

@app.get("/members")
def list_members():
    return list(members_db.values())

@app.get("/members/{member_id}")
def get_member(member_id: str):
    if member_id not in members_db:
        raise HTTPException(status_code=404, detail="Member not found")
    return members_db[member_id]

@app.put("/members/{member_id}")
def update_member(member_id: str, member: MemberCreate):
    if member_id not in members_db:
        raise HTTPException(status_code=404, detail="Member not found")
    existing = members_db[member_id]
    # Check email uniqueness excluding self
    for mid, m in members_db.items():
        if m["email"] == member.email and mid != member_id:
            raise HTTPException(status_code=400, detail="Email already exists")
    existing["name"] = member.name
    existing["email"] = member.email
    return existing

@app.delete("/members/{member_id}", status_code=200)
def delete_member(member_id: str):
    if member_id not in members_db:
        raise HTTPException(status_code=404, detail="Member not found")
    del members_db[member_id]
    return {"detail": "Member deleted"}

# ---- Borrow/Return endpoints ----
@app.post("/borrow")
def borrow_book(request: BorrowRequest):
    member_id = request.member_id
    book_id = request.book_id
    if member_id not in members_db:
        raise HTTPException(status_code=400, detail="Member not found")
    if book_id not in books_db:
        raise HTTPException(status_code=400, detail="Book not found")
    if not books_db[book_id]["available"]:
        raise HTTPException(status_code=400, detail="Book already borrowed")
    if len(members_db[member_id]["borrowed_books"]) >= 5:
        raise HTTPException(status_code=400, detail="Member has reached maximum borrow limit (5)")
    books_db[book_id]["available"] = False
    members_db[member_id]["borrowed_books"].append(book_id)
    borrows_db[book_id] = member_id
    return {"detail": "Book borrowed successfully"}

@app.post("/return")
def return_book(request: ReturnRequest):
    book_id = request.book_id
    if book_id not in borrows_db:
        raise HTTPException(status_code=400, detail="Book was not borrowed")
    member_id = borrows_db[book_id]
    books_db[book_id]["available"] = True
    members_db[member_id]["borrowed_books"].remove(book_id)
    del borrows_db[book_id]
    return {"detail": "Book returned successfully"}

@app.get("/borrowed")
def list_borrowed():
    result = []
    for book_id, member_id in borrows_db.items():
        book = books_db[book_id]
        member = members_db.get(member_id)
        result.append({
            "book_id": book_id,
            "book_title": book["title"],
            "member_id": member_id,
            "member_name": member["name"] if member else "Unknown"
        })
    return result

@app.get("/members/{member_id}/borrowed")
def member_borrowed_books(member_id: str):
    if member_id not in members_db:
        raise HTTPException(status_code=404, detail="Member not found")
    member = members_db[member_id]
    result = []
    for book_id in member["borrowed_books"]:
        book = books_db.get(book_id)
        if book:
            result.append(book)
    return result

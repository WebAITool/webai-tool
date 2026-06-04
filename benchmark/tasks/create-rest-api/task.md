# Create a book library REST API

Create a complete REST API for a book library management system using FastAPI.

## Requirements

1. **Book CRUD**:
   - `GET /books` — list all books (with optional `?author=` and `?genre=` filters)
   - `POST /books` — create a book (title, author, genre, year, isbn)
   - `GET /books/{id}` — get single book
   - `PUT /books/{id}` — update a book
   - `DELETE /books/{id}` — delete a book

2. **Member CRUD**:
   - `GET /members` — list all members
   - `POST /members` — register a member (name, email, phone)
   - `GET /members/{id}` — get member info
   - `PUT /members/{id}` — update member
   - `DELETE /members/{id}` — remove member

3. **Borrowing system**:
   - `POST /borrow` — borrow a book (body: `{book_id, member_id}`)
   - `POST /return` — return a book (body: `{book_id}`)
   - `GET /borrowed` — list currently borrowed books
   - `GET /members/{id}/borrowed` — list books borrowed by a member

4. **Business rules**:
   - A book can only be borrowed if it's available
   - A member can borrow at most 5 books at a time
   - Returning a book that wasn't borrowed should return 400
   - ISBN must be unique
   - Email must be unique

5. **Data storage**: In-memory (dict/list), no database needed

6. Create `requirements.txt` with FastAPI + uvicorn

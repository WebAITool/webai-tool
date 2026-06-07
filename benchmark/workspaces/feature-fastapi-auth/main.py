"""
FastAPI Notes App – Integrated with auth module.
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from auth import UserRegister, UserLogin, register_user, login_user, get_current_user

app = FastAPI()

# In-memory notes store
_notes: dict = {}
_next_note_id = 1


class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None


class Note(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    username: str


@app.get("/notes")
def list_notes(username: str = Depends(get_current_user)) -> List[Note]:
    """Return notes belonging to the authenticated user."""
    user_notes = [note for note in _notes.values() if note["username"] == username]
    return [Note(**note) for note in user_notes]


@app.post("/notes", status_code=201)
def create_note(note: NoteCreate, username: str = Depends(get_current_user)) -> Note:
    """Create a new note for the authenticated user."""
    global _next_note_id
    note_id = _next_note_id
    _next_note_id += 1
    note_dict = {
        "id": note_id,
        "title": note.title,
        "content": note.content,
        "username": username,
    }
    _notes[note_id] = note_dict
    return Note(**note_dict)


@app.get("/notes/{note_id}")
def get_note(note_id: int, username: str = Depends(get_current_user)) -> Note:
    """Retrieve a specific note, verifying ownership."""
    note = _notes.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    if note["username"] != username:
        raise HTTPException(status_code=403, detail="Access denied")
    return Note(**note)


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int, username: str = Depends(get_current_user)):
    """Delete a note owned by the authenticated user."""
    note = _notes.get(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    if note["username"] != username:
        raise HTTPException(status_code=403, detail="Access denied")
    del _notes[note_id]


@app.post("/auth/register")
def auth_register(data: UserRegister):
    """Register a new user and return token."""
    return register_user(data)


@app.post("/auth/login")
def auth_login(data: UserLogin):
    """Log in an existing user and return token."""
    return login_user(data)

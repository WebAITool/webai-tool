from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()


class NoteCreate(BaseModel):
    title: str
    content: str


class Note(NoteCreate):
    id: int


_notes: List[dict] = []
_next_id = 1


@app.get("/notes")
def list_notes():
    return _notes


@app.post("/notes", status_code=201)
def create_note(body: NoteCreate):
    global _next_id
    note = {"id": _next_id, "title": body.title, "content": body.content}
    _notes.append(note)
    _next_id += 1
    return note


@app.get("/notes/{note_id}")
def get_note(note_id: int):
    for n in _notes:
        if n["id"] == note_id:
            return n
    raise HTTPException(404, "not found")


@app.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: int):
    global _notes
    _notes = [n for n in _notes if n["id"] != note_id]

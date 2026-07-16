from fastapi import FastAPI, HTTPException, Depends, status
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from datetime import datetime

from database.session import get_session, engine
from models.book import Book, BookCreate, BookUpdate

# Automatically create tables in PostgreSQL on startup
SQLModel.metadata.create_all(engine)

app = FastAPI(
    title="Book Inventory API",
    description="A FastAPI backend to manage bookstore inventory using SQLModel",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Welcome to the Book Inventory API"}


# 1. CREATE BOOK (POST /books)
@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, session: Session = Depends(get_session)):
    """Create a new book in the inventory"""
    # Check if a book with the same ISBN already exists
    existing_book = session.exec(select(Book).where(Book.isbn == book.isbn)).first()
    if existing_book:
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists")

    db_book = Book(**book.dict())
    session.add(db_book)
    session.commit()
    session.refresh(db_book)
    return db_book


# 2. LIST ALL BOOKS WITH FILTERS (GET /books)
@app.get("/books", response_model=List[Book])
def list_books(
    skip: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """List all books with pagination and optional filters"""
    query = select(Book)
    
    if min_price is not None:
        query = query.where(Book.price >= min_price)
    if max_price is not None:
        query = query.where(Book.price <= max_price)
    if in_stock is not None:
        if in_stock:
            query = query.where(Book.stock > 0)
        else:
            query = query.where(Book.stock == 0)
            
    return session.exec(query.offset(skip).limit(limit)).all()
@app.get("/books/search", response_model=List[Book])
def search_books(q: str, session: Session = Depends(get_session)):
    """Search for books matching the search string in title or author"""
    query = select(Book).where(
        (Book.title.contains(q)) | (Book.author.contains(q))
    )
    return session.exec(query).all()


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, session: Session = Depends(get_session)):
    """Retrieve a single book's details by ID"""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.patch("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int,
    book_update: BookUpdate,
    session: Session = Depends(get_session)
):
    """Partially update a book's fields"""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = book_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(book, key, value)
        
    book.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, session: Session = Depends(get_session)):
    """Delete a book from the inventory"""
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    session.delete(book)
    session.commit()
    return None
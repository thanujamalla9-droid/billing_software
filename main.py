from decimal import Decimal
from typing import List

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from mysql.connector import Error
from pydantic import BaseModel, Field

from database import DatabaseError, get_connection, init_database


class ItemBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    item: str = Field(..., min_length=1, max_length=120)
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    pass


class ItemOut(ItemBase):
    id: int


app = FastAPI(title="Billing Items API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse("index.html")


@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse("styles.css")


@app.get("/script.js", include_in_schema=False)
def script():
    return FileResponse("script.js")


@app.on_event("startup")
def on_startup():
    init_database()


@app.exception_handler(DatabaseError)
def database_error_handler(_request, exc: DatabaseError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def row_to_item(row: dict) -> ItemOut:
    return ItemOut(
        id=row["id"],
        code=row["code"],
        item=row["item"],
        price=row["price"],
    )


@app.get("/items", response_model=List[ItemOut])
def list_items():
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, code, item, price FROM items ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        return [row_to_item(row) for row in rows]


@app.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, code, item, price FROM items WHERE id = %s", (item_id,))
        row = cursor.fetchone()
        cursor.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return row_to_item(row)


@app.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "INSERT INTO items (code, item, price) VALUES (%s, %s, %s)",
                (payload.code, payload.item, payload.price),
            )
            connection.commit()
            new_id = cursor.lastrowid
            cursor.execute("SELECT id, code, item, price FROM items WHERE id = %s", (new_id,))
            row = cursor.fetchone()
        except Error as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise HTTPException(status_code=409, detail="Code already exists") from exc
            raise
        finally:
            cursor.close()

    return row_to_item(row)


@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id FROM items WHERE id = %s", (item_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Item not found")

            cursor.execute(
                "UPDATE items SET code = %s, item = %s, price = %s WHERE id = %s",
                (payload.code, payload.item, payload.price, item_id),
            )
            connection.commit()

            cursor.execute("SELECT id, code, item, price FROM items WHERE id = %s", (item_id,))
            row = cursor.fetchone()
        except Error as exc:
            connection.rollback()
            if exc.errno == 1062:
                raise HTTPException(status_code=409, detail="Code already exists") from exc
            raise
        finally:
            cursor.close()

    return row_to_item(row)


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        connection.commit()
        deleted = cursor.rowcount
        cursor.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

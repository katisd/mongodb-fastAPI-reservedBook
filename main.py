from fastapi import FastAPI, HTTPException, Body
from datetime import date, datetime
from pymongo import MongoClient
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

DATABASE_NAME = "hotel"
COLLECTION_NAME = "reservation"
MONGO_DB_URL = "mongodb://localhost"
MONGO_DB_PORT = 27017


class Reservation(BaseModel):
    name: str
    start_date: str
    end_date: str
    room_id: int


client = MongoClient(f"{MONGO_DB_URL}:{MONGO_DB_PORT}")

db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def room_avaliable(room_id: int, start_date: str, end_date: str):
    query = {
        "room_id": room_id,
        "$or": [
            {
                "$and": [
                    {"start_date": {"$lte": start_date}},
                    {"end_date": {"$gte": start_date}},
                ]
            },
            {
                "$and": [
                    {"start_date": {"$lte": end_date}},
                    {"end_date": {"$gte": end_date}},
                ]
            },
            {
                "$and": [
                    {"start_date": {"$gte": start_date}},
                    {"end_date": {"$lte": end_date}},
                ]
            },
        ],
    }

    result = collection.find(query, {"_id": 0})
    list_cursor = list(result)

    return not len(list_cursor) > 0


def validate_date(start_date: str, end_date: str):
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        # print("Incorrect data format, should be YYYY-MM-DD")
        raise HTTPException(status_code=422, detail="Date format must be YYYY-MM-DD")
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before end date"
        )
    else:
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


@app.get("/reservation/by-name/{name}")
def get_reservation_by_name(name: str):
    data = collection.find({"name": name}, {"_id": 0})
    return {"result": list(data)}


@app.get("/reservation/by-room/{room_id}")
def get_reservation_by_room(room_id: int):
    data = collection.find({"room_id": room_id}, {"_id": 0})
    return {"result": list(data)}


@app.post("/reservation")
def reserve(reservation: Reservation):
    reservation.start_date, reservation.end_date = validate_date(
        reservation.start_date, reservation.end_date
    )
    if reservation.room_id < 1 or reservation.room_id > 10:
        raise HTTPException(status_code=400, detail="Room out of range")
    elif room_avaliable(
        reservation.room_id, reservation.start_date, reservation.end_date
    ):
        collection.insert_one(reservation.dict())
        return reservation
    else:
        raise HTTPException(status_code=400, detail="Room not avaliable")


@app.put("/reservation/update")
def update_reservation(
    reservation: Reservation, new_start_date: str = Body(), new_end_date: str = Body()
):
    new_start_date, new_end_date = validate_date(new_start_date, new_end_date)
    if reservation.room_id < 1 or reservation.room_id > 10:
        raise HTTPException(status_code=400, detail="Room out of range")
    elif room_avaliable(reservation.room_id, new_start_date, new_end_date):
        collection.update_one(
            reservation.dict(),
            {"$set": {"start_date": new_start_date, "end_date": new_end_date}},
        )
    else:
        raise HTTPException(status_code=400, detail="Room not avaliable")


@app.delete("/reservation/delete")
def cancel_reservation(reservation: Reservation):
    collection.delete_one(reservation.dict())

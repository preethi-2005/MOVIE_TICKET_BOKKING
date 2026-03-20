from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

# -------- DATA --------
movies = [
    {"id": 1, "title": "Leo", "genre": "Action", "language": "Tamil", "duration_mins": 160, "ticket_price": 200, "seats_available": 50},
    {"id": 2, "title": "RRR", "genre": "Action", "language": "Telugu", "duration_mins": 180, "ticket_price": 250, "seats_available": 60},
    {"id": 3, "title": "Jailer", "genre": "Drama", "language": "Tamil", "duration_mins": 150, "ticket_price": 180, "seats_available": 40},
    {"id": 4, "title": "KGF", "genre": "Action", "language": "Kannada", "duration_mins": 170, "ticket_price": 220, "seats_available": 55},
    {"id": 5, "title": "Avengers", "genre": "Action", "language": "English", "duration_mins": 190, "ticket_price": 300, "seats_available": 70},
    {"id": 6, "title": "Comedy Nights", "genre": "Comedy", "language": "Hindi", "duration_mins": 120, "ticket_price": 150, "seats_available": 45}
]

bookings = []
booking_counter = 1

holds = []
hold_counter = 1

# -------- MODEL --------
class BookingRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    movie_id: int = Field(..., gt=0)
    seats: int = Field(..., gt=0, le=10)
    phone: str = Field(..., min_length=10)
    seat_type: str = "standard"
    promo_code: str = ""   # ✅ ADDED

class NewMovie(BaseModel):
    title: str = Field(..., min_length=2)
    genre: str = Field(..., min_length=2)
    language: str = Field(..., min_length=2)
    duration_mins: int = Field(..., gt=0)
    ticket_price: int = Field(..., gt=0)
    seats_available: int = Field(..., gt=0)

# -------- HELPERS --------
def find_movie(movie_id):
    for movie in movies:
        if movie["id"] == movie_id:
            return movie
    return None


def calculate_ticket_cost(base_price, seats, seat_type, promo_code):
    multiplier = 1

    if seat_type == "premium":
        multiplier = 1.5
    elif seat_type == "recliner":
        multiplier = 2

    original_cost = base_price * seats * multiplier

    discount = 0
    if promo_code == "SAVE10":
        discount = 0.1
    elif promo_code == "SAVE20":
        discount = 0.2

    final_cost = original_cost * (1 - discount)

    return original_cost, final_cost

def filter_movies_logic(genre=None, language=None, max_price=None, min_seats=None):
    result = []

    for movie in movies:
        if genre is not None and movie["genre"].lower() != genre.lower():
            continue

        if language is not None and movie["language"].lower() != language.lower():
            continue

        if max_price is not None and movie["ticket_price"] > max_price:
            continue

        if min_seats is not None and movie["seats_available"] < min_seats:
            continue

        result.append(movie)

    return result

# -------- APIs --------

@app.get("/")
def home():
    return {"message": "Welcome to CineStar Booking"}


@app.get("/movies")
def get_movies():
    total_movies = len(movies)

    total_seats = sum(movie["seats_available"] for movie in movies)

    return {
        "total_movies": total_movies,
        "total_seats_available": total_seats,
        "movies": movies
    }

@app.post("/movies", status_code=201)
def create_movie(movie: NewMovie):
    # check duplicate title
    for m in movies:
        if m["title"].lower() == movie.title.lower():
            raise HTTPException(status_code=400, detail="Movie already exists")

    new_id = len(movies) + 1

    new_movie = {
        "id": new_id,
        "title": movie.title,
        "genre": movie.genre,
        "language": movie.language,
        "duration_mins": movie.duration_mins,
        "ticket_price": movie.ticket_price,
        "seats_available": movie.seats_available
    }

    movies.append(new_movie)

    return new_movie

from typing import Optional

@app.put("/movies/{movie_id}")
def update_movie(
    movie_id: int,
    ticket_price: Optional[int] = None,
    seats_available: Optional[int] = None
):
    movie = find_movie(movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if ticket_price is not None:
        movie["ticket_price"] = ticket_price

    if seats_available is not None:
        movie["seats_available"] = seats_available

    return {
        "message": "Movie updated successfully",
        "movie": movie
    }

@app.get("/movies/summary")
def movies_summary():
    prices = [movie["ticket_price"] for movie in movies]
    total_seats = sum(movie["seats_available"] for movie in movies)

    genre_count = {}
    for movie in movies:
        genre = movie["genre"]
        genre_count[genre] = genre_count.get(genre, 0) + 1

    return {
        "total_movies": len(movies),
        "highest_price": max(prices),
        "lowest_price": min(prices),
        "total_seats": total_seats,
        "genre_count": genre_count
    }

@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: int):
    movie = find_movie(movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # check if bookings exist for this movie
    for booking in bookings:
        if booking["movie_title"] == movie["title"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete movie with existing bookings"
            )

    movies.remove(movie)

    return {"message": "Movie deleted successfully"}
from fastapi import Query

@app.get("/movies/filter")
def filter_movies(
    genre: str = Query(None),
    language: str = Query(None),
    max_price: int = Query(None),
    min_seats: int = Query(None)
):
    filtered = filter_movies_logic(genre, language, max_price, min_seats)

    return {
        "total_found": len(filtered),
        "movies": filtered
    }
@app.get("/movies/search")
def search_movies(keyword: str):
    result = []

    for movie in movies:
        if (
            keyword.lower() in movie["title"].lower()
            or keyword.lower() in movie["genre"].lower()
            or keyword.lower() in movie["language"].lower()
        ):
            result.append(movie)

    if not result:
        return {"message": "No movies found"}

    return {
        "total_found": len(result),
        "movies": result
    }

@app.get("/movies/sort")
def sort_movies(
    sort_by: str = "ticket_price",
    order: str = "asc"
):
    valid_fields = ["ticket_price", "title", "duration_mins", "seats_available"]

    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    reverse = False
    if order == "desc":
        reverse = True

    sorted_movies = sorted(movies, key=lambda x: x[sort_by], reverse=reverse)

    return {
        "sorted_by": sort_by,
        "order": order,
        "movies": sorted_movies
    }

@app.get("/movies/page")
def paginate_movies(page: int = 1, limit: int = 3):
    total = len(movies)

    start = (page - 1) * limit
    end = start + limit

    paginated_movies = movies[start:end]

    total_pages = (total + limit - 1) // limit

    return {
        "total_movies": total,
        "total_pages": total_pages,
        "current_page": page,
        "movies": paginated_movies
    }

@app.get("/movies/browse")
def browse_movies(
    keyword: str = None,
    genre: str = None,
    language: str = None,
    sort_by: str = "ticket_price",
    order: str = "asc",
    page: int = 1,
    limit: int = 3
):
    result = movies

    # 1. keyword search
    if keyword:
        result = [
            m for m in result
            if keyword.lower() in m["title"].lower()
            or keyword.lower() in m["genre"].lower()
            or keyword.lower() in m["language"].lower()
        ]

    # 2. filter
    if genre:
        result = [m for m in result if m["genre"].lower() == genre.lower()]

    if language:
        result = [m for m in result if m["language"].lower() == language.lower()]

    # 3. sort
    valid_fields = ["ticket_price", "title", "duration_mins", "seats_available"]
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail="Invalid sort field")

    reverse = True if order == "desc" else False
    result = sorted(result, key=lambda x: x[sort_by], reverse=reverse)

    # 4. pagination
    total = len(result)
    start = (page - 1) * limit
    end = start + limit

    paginated = result[start:end]
    total_pages = (total + limit - 1) // limit

    return {
        "total_results": total,
        "total_pages": total_pages,
        "current_page": page,
        "movies": paginated
    }

@app.get("/movies/{movie_id}")
def get_movie_by_id(movie_id: int):
    movie = find_movie(movie_id)
    if movie:
        return movie
    raise HTTPException(status_code=404, detail="Movie not found")


@app.get("/bookings")
def get_bookings():
    total_revenue = sum(booking.get("final_cost", 0) for booking in bookings)

    return {
        "total_bookings": len(bookings),
        "total_revenue": total_revenue,
        "bookings": bookings
    }


@app.post("/test-booking")
def test_booking(request: BookingRequest):
    return request


@app.post("/bookings")
def create_booking(request: BookingRequest):
    global booking_counter

    # 1. check movie
    movie = find_movie(request.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # 2. check seats
    if movie["seats_available"] < request.seats:
        raise HTTPException(status_code=400, detail="Not enough seats")

    # 3. calculate cost
    original, final = calculate_ticket_cost(
        movie["ticket_price"],
        request.seats,
        request.seat_type,
        request.promo_code
    )

    # 4. reduce seats
    movie["seats_available"] -= request.seats

    # 5. create booking
    booking = {
        "booking_id": booking_counter,
        "customer_name": request.customer_name,
        "movie_title": movie["title"],
        "seats": request.seats,
        "seat_type": request.seat_type,
        "original_cost": original,
        "final_cost": final
    }

    bookings.append(booking)
    booking_counter += 1

    return booking

@app.get("/bookings/search")
def search_bookings(name: str):
    result = []

    for booking in bookings:
        if name.lower() in booking["customer_name"].lower():
            result.append(booking)

    if not result:
        return {"message": "No bookings found"}

    return {
        "total_found": len(result),
        "bookings": result
    }

@app.post("/seat-hold")
def hold_seats(request: BookingRequest):
    global hold_counter

    movie = find_movie(request.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if movie["seats_available"] < request.seats:
        raise HTTPException(status_code=400, detail="Not enough seats")

    # temporarily reduce seats
    movie["seats_available"] -= request.seats

    hold = {
        "hold_id": hold_counter,
        "customer_name": request.customer_name,
        "movie_id": request.movie_id,
        "movie_title": movie["title"],
        "seats": request.seats
    }

    holds.append(hold)
    hold_counter += 1

    return hold

@app.get("/seat-hold")
def get_holds():
    return {
        "total_holds": len(holds),
        "holds": holds
    }

@app.post("/seat-confirm/{hold_id}")
def confirm_hold(hold_id: int):
    global booking_counter

    # find hold
    hold = None
    for h in holds:
        if h["hold_id"] == hold_id:
            hold = h
            break

    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    # create booking from hold
    booking = {
        "booking_id": booking_counter,
        "customer_name": hold["customer_name"],
        "movie_title": hold["movie_title"],
        "seats": hold["seats"],
        "seat_type": "standard",
        "original_cost": 0,
        "final_cost": 0
    }

    bookings.append(booking)
    booking_counter += 1

    # remove hold
    holds.remove(hold)

    return {
        "message": "Booking confirmed",
        "booking": booking
    }
@app.delete("/seat-release/{hold_id}")
def release_hold(hold_id: int):
    hold = None
    for h in holds:
        if h["hold_id"] == hold_id:
            hold = h
            break

    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    # restore seats
    movie = find_movie(hold["movie_id"])
    if movie:
        movie["seats_available"] += hold["seats"]

    holds.remove(hold)

    return {"message": "Hold released and seats restored"}
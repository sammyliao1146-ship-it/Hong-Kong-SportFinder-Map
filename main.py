from backend.app.config.factory import create_app
from backend.app.routers import assistant, booking, health, programmes, venues

app = create_app(routers=[
    health.router,
    venues.router,
    booking.router,
    programmes.router,
    assistant.router,
])

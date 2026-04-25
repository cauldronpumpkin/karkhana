from mangum import Mangum

from backend.app.main import app

handler = Mangum(app, lifespan="off")

from core.db import Base, engine
from core.models.appointment import Appointment
# Import other core models as needed

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db() 
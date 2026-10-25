from core.database import engine, Base
from models import *

Base.metadata.create_all(bind=engine)
print('done')

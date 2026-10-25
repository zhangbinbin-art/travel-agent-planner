import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import engine, Base
from models import *

Base.metadata.create_all(bind=engine)
print('done')

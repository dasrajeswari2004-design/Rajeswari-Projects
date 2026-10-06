from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
import chromadb

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
chroma_client = chromadb.PersistentClient(path="./chroma_data")

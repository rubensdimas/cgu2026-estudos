import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://cgu:cgu@localhost:5432/cgu_test")
os.environ.setdefault("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver,*.ts.net")

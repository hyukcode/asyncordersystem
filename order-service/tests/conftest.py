import os 

os.environ.setdefault(
    "DATABASE_URL",
    "mysql+asyncmy://test_user:test_password@127.0.0.1:3306/test_db",
)
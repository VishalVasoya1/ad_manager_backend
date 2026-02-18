from passlib.context import CryptContext
import bcrypt

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd.hash("Admin@123"))

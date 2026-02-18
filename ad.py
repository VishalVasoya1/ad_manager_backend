import asyncio
import uuid
from sqlalchemy import select
from app.config.postgres import AsyncSessionLocal
from app.model.user import User  # make sure this is your user model
from passlib.hash import bcrypt  # or whatever hashing you use

async def create_first_admin():
    async with AsyncSessionLocal() as session:
        # Check if any user exists
        result = await session.execute(select(User))
        user = result.scalars().first()
        if user:
            print("⚠️ Admin already exists!")
            return

        # Create first admin
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@admanager.com",
            status="active",
            password=bcrypt.hash("Admin@123"),  # use secure password
            role="admin",
            is_admin=True,
            is_active=True,
        )
        session.add(admin_user)
        await session.commit()
        print("✅ First admin user created!")

if __name__ == "__main__":
    asyncio.run(create_first_admin())

"""
Seed ข้อมูลตั้งต้น (รันซ้ำได้ - ข้ามแถวที่มีอยู่แล้ว)

    python seed.py

- สร้างบัญชี admin จาก SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD (ถ้าตั้งไว้)
- ข้อมูลตัวอย่าง (ห้อง, อุปกรณ์, บัญชี demo) สร้างเมื่อ SEED_DEMO_DATA=true เท่านั้น
  ห้ามเปิดบน prod เพราะบัญชี demo ใช้รหัสผ่านที่รู้กันทั่วไป
บน cloud รันครั้งเดียวผ่าน Cloud Run Job `campus-seed`
"""

import asyncio
import os

from sqlalchemy import select

from app.common.constants import EquipmentStatus, RoomStatus, RoomType, UserRole
from app.core.database import AsyncSessionLocal, close_db_connection
from app.core.security import get_password_hash
from app.models import Equipment, Room, User

ROOMS = [
    ("A101", "ห้องเรียนมาตรฐาน A101", RoomType.CLASSROOM, "อาคาร A", 1, 40),
    ("A201", "ห้องเรียน A201", RoomType.CLASSROOM, "อาคาร A", 2, 50),
    ("B301", "ห้องประชุม B301", RoomType.MEETING_ROOM, "อาคาร B", 3, 20),
    ("C101", "ห้องปฏิบัติการคอมพิวเตอร์", RoomType.LABORATORY, "อาคาร C", 1, 30),
    ("D401", "หอประชุมใหญ่", RoomType.AUDITORIUM, "อาคาร D", 4, 200),
]

# อุปกรณ์ 1 แถว = 1 ชิ้น (ของรุ่นเดียวกัน 2 ชิ้นจึงเป็น 2 แถว)
EQUIPMENTS = [
    ("PROJ001", "โปรเจคเตอร์ Epson EB-X51", "projector", "Epson", "EB-X51"),
    ("PROJ002", "โปรเจคเตอร์ Epson EB-X41", "projector", "Epson", "EB-X41"),
    ("CAM001", "กล้อง DSLR Canon EOS 90D", "camera", "Canon", "EOS 90D"),
    ("LAP001", "Notebook Dell Inspiron 15", "laptop", "Dell", "Inspiron 15 3000"),
    ("MIC001", "ไมโครโฟนไร้สาย Shure #1", "microphone", "Shure", "BLX24/PG58"),
    ("MIC002", "ไมโครโฟนไร้สาย Shure #2", "microphone", "Shure", "BLX24/PG58"),
]

DEMO_USERS = [
    ("staff@smartcampus.dev", "staff12345", "เจ้าหน้าที่ทดสอบ", UserRole.STAFF, None, "STF001"),
    (
        "student1@smartcampus.dev",
        "student12345",
        "นักศึกษา ทดสอบ 1",
        UserRole.STUDENT,
        "6501001",
        None,
    ),
    (
        "student2@smartcampus.dev",
        "student12345",
        "นักศึกษา ทดสอบ 2",
        UserRole.STUDENT,
        "6501002",
        None,
    ),
]


async def ensure_user(db, email, password, full_name, role, student_id=None, staff_id=None):
    if await db.scalar(select(User.id).where(User.email == email)):
        print(f"  = user {email} exists")
        return
    db.add(
        User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role.value,
            student_id=student_id,
            staff_id=staff_id,
            is_active=True,
            is_verified=True,
        )
    )
    print(f"  + user {email} ({role.value})")


async def main() -> None:
    demo = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    admin_email = os.getenv("SEED_ADMIN_EMAIL")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD")

    async with AsyncSessionLocal() as db:
        if admin_email and admin_password:
            if len(admin_password) < 12:
                raise SystemExit("SEED_ADMIN_PASSWORD must be at least 12 characters")
            await ensure_user(
                db,
                admin_email.lower(),
                admin_password,
                "ผู้ดูแลระบบ",
                UserRole.ADMIN,
                staff_id="ADM001",
            )

        if demo:
            for email, password, name, role, student_id, staff_id in DEMO_USERS:
                await ensure_user(db, email, password, name, role, student_id, staff_id)
            for number, name, rtype, building, floor, capacity in ROOMS:
                if not await db.scalar(select(Room.id).where(Room.room_number == number)):
                    db.add(
                        Room(
                            room_number=number,
                            room_name=name,
                            room_type=rtype.value,
                            building=building,
                            floor=floor,
                            capacity=capacity,
                            status=RoomStatus.AVAILABLE.value,
                            is_bookable=True,
                        )
                    )
                    print(f"  + room {number}")
            for code, name, etype, brand, model in EQUIPMENTS:
                if not await db.scalar(
                    select(Equipment.id).where(Equipment.equipment_code == code)
                ):
                    db.add(
                        Equipment(
                            equipment_code=code,
                            equipment_name=name,
                            equipment_type=etype,
                            brand=brand,
                            model=model,
                            quantity=1,
                            status=EquipmentStatus.AVAILABLE.value,
                            is_bookable=True,
                        )
                    )
                    print(f"  + equipment {code}")

        await db.commit()
    await close_db_connection()
    print("Seed complete")


if __name__ == "__main__":
    asyncio.run(main())

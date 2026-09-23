"""
Database Seeding Script
สร้างข้อมูลเริ่มต้นสำหรับ Development และ Testing
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import Booking, Equipment, Room, User
from app.common.constants import (
    BookingStatus,
    EquipmentStatus,
    RoomStatus,
    RoomType,
    UserRole,
)


async def seed_users(db: AsyncSession):
    """สร้าง Users ตัวอย่าง"""
    print("🌱 Seeding users...")

    # ตรวจสอบว่ามี users อยู่แล้วหรือไม่
    result = await db.execute(select(User).limit(1))
    if result.scalar_one_or_none():
        print("   Users already exist, skipping...")
        return

    users = [
        # Admin
        User(
            email="admin@smartcampus.dev",
            hashed_password=get_password_hash("admin123"),
            full_name="ผู้ดูแลระบบ",
            staff_id="ADM001",
            department="IT Department",
            role=UserRole.ADMIN.value,
            is_active=True,
            is_verified=True,
        ),
        # Staff
        User(
            email="staff@smartcampus.dev",
            hashed_password=get_password_hash("staff123"),
            full_name="เจ้าหน้าที่ดูแลระบบ",
            staff_id="STF001",
            department="General Affairs",
            role=UserRole.STAFF.value,
            is_active=True,
            is_verified=True,
        ),
        # Students
        User(
            email="student1@smartcampus.dev",
            hashed_password=get_password_hash("student123"),
            full_name="นักศึกษาทดสอบ 1",
            student_id="STD2024001",
            department="Computer Science",
            phone_number="0812345678",
            role=UserRole.STUDENT.value,
            is_active=True,
            is_verified=True,
        ),
        User(
            email="student2@smartcampus.dev",
            hashed_password=get_password_hash("student123"),
            full_name="นักศึกษาทดสอบ 2",
            student_id="STD2024002",
            department="Engineering",
            phone_number="0823456789",
            role=UserRole.STUDENT.value,
            is_active=True,
            is_verified=True,
        ),
    ]

    db.add_all(users)
    await db.commit()
    print(f"   ✓ Created {len(users)} users")


async def seed_rooms(db: AsyncSession):
    """สร้าง Rooms ตัวอย่าง"""
    print("🌱 Seeding rooms...")

    result = await db.execute(select(Room).limit(1))
    if result.scalar_one_or_none():
        print("   Rooms already exist, skipping...")
        return

    rooms = [
        Room(
            room_number="A101",
            room_name="ห้องเรียนมาตรฐาน A101",
            room_type=RoomType.CLASSROOM.value,
            building="อาคาร A",
            floor=1,
            capacity=40,
            description="ห้องเรียนขนาดกลาง มีเครื่องฉายโปรเจคเตอร์",
            facilities='["Projector", "Whiteboard", "Air Conditioner", "WiFi"]',
            status=RoomStatus.AVAILABLE.value,
            is_bookable=True,
        ),
        Room(
            room_number="A201",
            room_name="ห้องเรียน A201",
            room_type=RoomType.CLASSROOM.value,
            building="อาคาร A",
            floor=2,
            capacity=50,
            description="ห้องเรียนขนาดใหญ่",
            facilities='["Projector", "Whiteboard", "Air Conditioner", "WiFi", "Sound System"]',
            status=RoomStatus.AVAILABLE.value,
            is_bookable=True,
        ),
        Room(
            room_number="B301",
            room_name="ห้องประชุม B301",
            room_type=RoomType.MEETING_ROOM.value,
            building="อาคาร B",
            floor=3,
            capacity=20,
            description="ห้องประชุมสำหรับกิจกรรมขนาดเล็ก",
            facilities='["Projector", "TV", "Whiteboard", "Air Conditioner", "WiFi", "Video Conference"]',
            status=RoomStatus.AVAILABLE.value,
            is_bookable=True,
        ),
        Room(
            room_number="C101",
            room_name="ห้องปฏิบัติการคอมพิวเตอร์",
            room_type=RoomType.LABORATORY.value,
            building="อาคาร C",
            floor=1,
            capacity=30,
            description="ห้องปฏิบัติการคอมพิวเตอร์ มีเครื่อง 30 เครื่อง",
            facilities='["30 PCs", "Projector", "Air Conditioner", "WiFi"]',
            status=RoomStatus.AVAILABLE.value,
            is_bookable=True,
        ),
        Room(
            room_number="D401",
            room_name="หอประชุมใหญ่",
            room_type=RoomType.AUDITORIUM.value,
            building="อาคาร D",
            floor=4,
            capacity=200,
            description="หอประชุมขนาดใหญ่สำหรับงานพิเธี",
            facilities='["Stage", "Sound System", "Lighting", "Projector", "Air Conditioner"]',
            status=RoomStatus.AVAILABLE.value,
            is_bookable=True,
        ),
    ]

    db.add_all(rooms)
    await db.commit()
    print(f"   ✓ Created {len(rooms)} rooms")


async def seed_equipments(db: AsyncSession):
    """สร้าง Equipments ตัวอย่าง"""
    print("🌱 Seeding equipments...")

    result = await db.execute(select(Equipment).limit(1))
    if result.scalar_one_or_none():
        print("   Equipments already exist, skipping...")
        return

    equipments = [
        Equipment(
            equipment_code="PROJ001",
            equipment_name="โปรเจคเตอร์ Epson EB-X51",
            equipment_type="projector",
            brand="Epson",
            model="EB-X51",
            serial_number="EPSX51001",
            description="โปรเจคเตอร์ความสว่าง 3,800 ANSI Lumens",
            specifications='{"resolution": "XGA 1024x768", "brightness": "3800 lumens"}',
            location="ห้องเก็บอุปกรณ์ อาคาร A ชั้น 1",
            responsible_staff="เจ้าหน้าที่ดูแลอุปกรณ์",
            status=EquipmentStatus.AVAILABLE.value,
            is_bookable=True,
            quantity=1,
        ),
        Equipment(
            equipment_code="PROJ002",
            equipment_name="โปรเจคเตอร์ Epson EB-X41",
            equipment_type="projector",
            brand="Epson",
            model="EB-X41",
            serial_number="EPSX41001",
            description="โปรเจคเตอร์ความสว่าง 3,600 ANSI Lumens",
            specifications='{"resolution": "XGA 1024x768", "brightness": "3600 lumens"}',
            location="ห้องเก็บอุปกรณ์ อาคาร A ชั้น 1",
            responsible_staff="เจ้าหน้าที่ดูแลอุปกรณ์",
            status=EquipmentStatus.AVAILABLE.value,
            is_bookable=True,
            quantity=1,
        ),
        Equipment(
            equipment_code="CAM001",
            equipment_name="กล้อง DSLR Canon EOS 90D",
            equipment_type="camera",
            brand="Canon",
            model="EOS 90D",
            serial_number="CN90D001",
            description="กล้อง DSLR 32.5 MP พร้อมเลนส์ Kit",
            specifications='{"sensor": "APS-C 32.5MP", "video": "4K 30fps"}',
            location="ห้องเก็บอุปกรณ์ อาคาร B ชั้น 2",
            responsible_staff="เจ้าหน้าที่สื่อ",
            status=EquipmentStatus.AVAILABLE.value,
            is_bookable=True,
            quantity=1,
        ),
        Equipment(
            equipment_code="LAP001",
            equipment_name="Notebook Dell Inspiron 15",
            equipment_type="laptop",
            brand="Dell",
            model="Inspiron 15 3000",
            serial_number="DLINS15001",
            description="Notebook สำหรับงานทั่วไป",
            specifications='{"cpu": "Intel Core i5", "ram": "8GB", "storage": "256GB SSD"}',
            location="ห้องเก็บอุปกรณ์ อาคาร C ชั้น 1",
            responsible_staff="เจ้าหน้าที่ IT",
            status=EquipmentStatus.AVAILABLE.value,
            is_bookable=True,
            quantity=1,
        ),
        Equipment(
            equipment_code="MIC001",
            equipment_name="ไมโครโฟนไร้สาย Shure",
            equipment_type="microphone",
            brand="Shure",
            model="BLX24/PG58",
            serial_number="SHBLX001",
            description="ระบบไมโครโฟนไร้สาย",
            specifications='{"frequency": "UHF", "channels": "2"}',
            location="ห้องเก็บอุปกรณ์ อาคาร D ชั้น 4",
            responsible_staff="เจ้าหน้าที่เสียง",
            status=EquipmentStatus.AVAILABLE.value,
            is_bookable=True,
            quantity=2,
        ),
    ]

    db.add_all(equipments)
    await db.commit()
    print(f"   ✓ Created {len(equipments)} equipments")


async def seed_bookings(db: AsyncSession):
    """สร้าง Bookings ตัวอย่าง"""
    print("🌱 Seeding bookings...")

    # ดึง users, rooms, equipments
    users_result = await db.execute(select(User).where(User.role == UserRole.STUDENT.value))
    users = users_result.scalars().all()

    rooms_result = await db.execute(select(Room).limit(2))
    rooms = rooms_result.scalars().all()

    equipments_result = await db.execute(select(Equipment).limit(1))
    equipments = equipments_result.scalars().all()

    if not users or not rooms:
        print("   Skipping bookings (no users or rooms found)")
        return

    now = datetime.utcnow()
    bookings = [
        # การจองห้องในอนาคต
        Booking(
            user_id=users[0].id,
            room_id=rooms[0].id,
            title="ประชุมกลุ่มโปรเจค",
            description="ประชุมกลุ่มเพื่อทำโปรเจควิชา Software Engineering",
            purpose="Group Study",
            start_time=now + timedelta(days=1, hours=9),
            end_time=now + timedelta(days=1, hours=11),
            status=BookingStatus.CONFIRMED.value,
            contact_person=users[0].full_name,
            contact_phone=users[0].phone_number,
            attendees_count=5,
        ),
    ]

    # ถ้ามี equipment ให้จองด้วย
    if equipments:
        bookings.append(
            Booking(
                user_id=users[0].id,
                equipment_id=equipments[0].id,
                title="ยืมโปรเจคเตอร์",
                description="ยืมโปรเจคเตอร์สำหรับนำเสนอโปรเจค",
                purpose="Presentation",
                start_time=now + timedelta(days=2, hours=13),
                end_time=now + timedelta(days=2, hours=15),
                status=BookingStatus.PENDING.value,
                contact_person=users[0].full_name,
                contact_phone=users[0].phone_number,
            )
        )

    db.add_all(bookings)
    await db.commit()
    print(f"   ✓ Created {len(bookings)} bookings")


async def main():
    """Run all seeders"""
    print("\n" + "=" * 60)
    print("🚀 Starting Database Seeding...")
    print("=" * 60 + "\n")

    async with AsyncSessionLocal() as db:
        try:
            await seed_users(db)
            await seed_rooms(db)
            await seed_equipments(db)
            await seed_bookings(db)

            print("\n" + "=" * 60)
            print("✅ Database seeding completed successfully!")
            print("=" * 60)
            print("\n📝 Default Credentials:")
            print("   Admin:   admin@smartcampus.dev / admin123")
            print("   Staff:   staff@smartcampus.dev / staff123")
            print("   Student: student1@smartcampus.dev / student123")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())

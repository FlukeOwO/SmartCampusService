"""ใส่ชื่อผู้ใช้ลงในผลลัพธ์ เพื่อให้หน้าเว็บแสดงชื่อคนแทน "User #id"

ค้นชื่อทั้งหมดใน query เดียว แล้วตั้งเป็น attribute ธรรมดา (ไม่ใช่คอลัมน์)
ให้ schema ที่ใช้ from_attributes อ่านไปใส่ใน response
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def attach_user_names(db: AsyncSession, items: Iterable[object], **fields: str) -> None:
    """fields: ชื่อ attribute ที่จะตั้ง -> ชื่อ attribute ที่เก็บ user id
    เช่น attach_user_names(db, rows, requester_name="user_id")
    """
    items = list(items)
    ids = {getattr(item, id_attr) for item in items for id_attr in fields.values()} - {None}
    names: dict[int, str] = {}
    if ids:
        result = await db.execute(select(User.id, User.full_name).where(User.id.in_(ids)))
        names = {user_id: full_name for user_id, full_name in result.all()}
    for item in items:
        for target, id_attr in fields.items():
            setattr(item, target, names.get(getattr(item, id_attr)))

"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables"""
    
    # =========================================================================
    # Users Table
    # =========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, comment='อีเมล (ใช้สำหรับ login)'),
        sa.Column('hashed_password', sa.String(length=255), nullable=False, comment='รหัสผ่านที่ Hash แล้ว'),
        sa.Column('full_name', sa.String(length=255), nullable=False, comment='ชื่อ-นามสกุล'),
        sa.Column('student_id', sa.String(length=50), nullable=True, comment='รหัสนักศึกษา (สำหรับ Student)'),
        sa.Column('staff_id', sa.String(length=50), nullable=True, comment='รหัสพนักงาน (สำหรับ Staff/Admin)'),
        sa.Column('phone_number', sa.String(length=20), nullable=True, comment='เบอร์โทรศัพท์'),
        sa.Column('department', sa.String(length=100), nullable=True, comment='ภาควิชา/แผนก'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='URL รูปโปรไฟล์'),
        sa.Column('role', sa.String(length=20), nullable=False, comment='บทบาท: student, staff, admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='สถานะการใช้งาน'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, comment='ยืนยันอีเมลแล้วหรือไม่'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='เวลาที่สร้างระเบียน'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='เวลาที่อัปเดตระเบียนล่าสุด'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_student_id'), 'users', ['student_id'], unique=True)
    op.create_index(op.f('ix_users_staff_id'), 'users', ['staff_id'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index('ix_users_role_active', 'users', ['role', 'is_active'], unique=False)
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'], unique=False)

    # =========================================================================
    # Rooms Table
    # =========================================================================
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('room_number', sa.String(length=50), nullable=False, comment='เลขห้อง'),
        sa.Column('room_name', sa.String(length=255), nullable=False, comment='ชื่อห้อง'),
        sa.Column('room_type', sa.String(length=50), nullable=False, comment='ประเภทห้อง'),
        sa.Column('building', sa.String(length=100), nullable=False, comment='ชื่ออาคาร'),
        sa.Column('floor', sa.Integer(), nullable=False, comment='ชั้น'),
        sa.Column('capacity', sa.Integer(), nullable=False, comment='จำนวนที่นั่ง'),
        sa.Column('description', sa.Text(), nullable=True, comment='รายละเอียดห้อง'),
        sa.Column('facilities', sa.Text(), nullable=True, comment='เครื่องมือและอุปกรณ์ในห้อง (JSON array)'),
        sa.Column('image_url', sa.String(length=500), nullable=True, comment='URL รูปภาพห้อง'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='สถานะห้อง'),
        sa.Column('is_bookable', sa.Boolean(), nullable=False, comment='สามารถจองได้หรือไม่'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rooms_id'), 'rooms', ['id'], unique=False)
    op.create_index(op.f('ix_rooms_room_number'), 'rooms', ['room_number'], unique=True)
    op.create_index(op.f('ix_rooms_room_type'), 'rooms', ['room_type'], unique=False)
    op.create_index(op.f('ix_rooms_building'), 'rooms', ['building'], unique=False)
    op.create_index(op.f('ix_rooms_status'), 'rooms', ['status'], unique=False)
    op.create_index('ix_rooms_status_bookable', 'rooms', ['status', 'is_bookable'], unique=False)
    op.create_index('ix_rooms_building_floor', 'rooms', ['building', 'floor'], unique=False)
    op.create_index('ix_rooms_type_status', 'rooms', ['room_type', 'status'], unique=False)

    # =========================================================================
    # Equipments Table
    # =========================================================================
    op.create_table(
        'equipments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('equipment_code', sa.String(length=50), nullable=False, comment='รหัสอุปกรณ์'),
        sa.Column('equipment_name', sa.String(length=255), nullable=False, comment='ชื่ออุปกรณ์'),
        sa.Column('equipment_type', sa.String(length=100), nullable=False, comment='ประเภทอุปกรณ์'),
        sa.Column('brand', sa.String(length=100), nullable=True, comment='ยี่ห้อ'),
        sa.Column('model', sa.String(length=100), nullable=True, comment='รุ่น'),
        sa.Column('serial_number', sa.String(length=100), nullable=True, comment='Serial Number'),
        sa.Column('description', sa.Text(), nullable=True, comment='รายละเอียดอุปกรณ์'),
        sa.Column('specifications', sa.Text(), nullable=True, comment='สเปค (JSON object)'),
        sa.Column('image_url', sa.String(length=500), nullable=True, comment='URL รูปภาพอุปกรณ์'),
        sa.Column('location', sa.String(length=255), nullable=True, comment='สถานที่เก็บอุปกรณ์'),
        sa.Column('responsible_staff', sa.String(length=255), nullable=True, comment='เจ้าหน้าที่ผู้ดูแล'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='สถานะอุปกรณ์'),
        sa.Column('is_bookable', sa.Boolean(), nullable=False, comment='สามารถจองได้หรือไม่'),
        sa.Column('quantity', sa.Integer(), nullable=False, comment='จำนวนอุปกรณ์'),
        sa.Column('last_maintenance_date', sa.String(length=50), nullable=True),
        sa.Column('next_maintenance_date', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equipments_id'), 'equipments', ['id'], unique=False)
    op.create_index(op.f('ix_equipments_equipment_code'), 'equipments', ['equipment_code'], unique=True)
    op.create_index(op.f('ix_equipments_equipment_name'), 'equipments', ['equipment_name'], unique=False)
    op.create_index(op.f('ix_equipments_equipment_type'), 'equipments', ['equipment_type'], unique=False)
    op.create_index(op.f('ix_equipments_status'), 'equipments', ['status'], unique=False)
    op.create_index('ix_equipments_status_bookable', 'equipments', ['status', 'is_bookable'], unique=False)
    op.create_index('ix_equipments_type_status', 'equipments', ['equipment_type', 'status'], unique=False)

    # =========================================================================
    # Bookings Table
    # =========================================================================
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='ผู้จอง'),
        sa.Column('room_id', sa.Integer(), nullable=True, comment='ห้องที่จอง'),
        sa.Column('equipment_id', sa.Integer(), nullable=True, comment='อุปกรณ์ที่จอง'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='หัวข้อการจอง'),
        sa.Column('description', sa.Text(), nullable=True, comment='รายละเอียดการจอง/วัตถุประสงค์'),
        sa.Column('purpose', sa.String(length=255), nullable=True, comment='วัตถุประสงค์'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, comment='เวลาเริ่มต้น'),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False, comment='เวลาสิ้นสุด'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='สถานะการจอง'),
        sa.Column('approved_by', sa.Integer(), nullable=True, comment='ผู้อนุมัติการจอง'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('attendees_count', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('end_time > start_time', name='check_booking_time_range'),
        sa.CheckConstraint('room_id IS NOT NULL OR equipment_id IS NOT NULL', name='check_booking_target'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
    op.create_index(op.f('ix_bookings_user_id'), 'bookings', ['user_id'], unique=False)
    op.create_index(op.f('ix_bookings_room_id'), 'bookings', ['room_id'], unique=False)
    op.create_index(op.f('ix_bookings_equipment_id'), 'bookings', ['equipment_id'], unique=False)
    op.create_index(op.f('ix_bookings_start_time'), 'bookings', ['start_time'], unique=False)
    op.create_index(op.f('ix_bookings_end_time'), 'bookings', ['end_time'], unique=False)
    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)
    op.create_index('ix_bookings_room_time', 'bookings', ['room_id', 'start_time', 'end_time', 'status'], unique=False)
    op.create_index('ix_bookings_equipment_time', 'bookings', ['equipment_id', 'start_time', 'end_time', 'status'], unique=False)
    op.create_index('ix_bookings_user_status', 'bookings', ['user_id', 'status'], unique=False)
    op.create_index('ix_bookings_status_time', 'bookings', ['status', 'start_time'], unique=False)

    # =========================================================================
    # Requests Table
    # =========================================================================
    op.create_table(
        'requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='ผู้ส่งคำร้อง'),
        sa.Column('assigned_staff_id', sa.Integer(), nullable=True, comment='เจ้าหน้าที่ที่รับผิดชอบ'),
        sa.Column('request_number', sa.String(length=50), nullable=False, comment='เลขที่คำร้อง'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='หัวข้อคำร้อง'),
        sa.Column('description', sa.Text(), nullable=False, comment='รายละเอียดคำร้อง'),
        sa.Column('request_type', sa.String(length=50), nullable=False, comment='ประเภทคำร้อง'),
        sa.Column('priority', sa.String(length=20), nullable=False, comment='ระดับความสำคัญ'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, comment='สถานะ'),
        sa.Column('status_notes', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_staff_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requests_id'), 'requests', ['id'], unique=False)
    op.create_index(op.f('ix_requests_request_number'), 'requests', ['request_number'], unique=True)
    op.create_index(op.f('ix_requests_user_id'), 'requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_requests_assigned_staff_id'), 'requests', ['assigned_staff_id'], unique=False)
    op.create_index(op.f('ix_requests_request_type'), 'requests', ['request_type'], unique=False)
    op.create_index(op.f('ix_requests_priority'), 'requests', ['priority'], unique=False)
    op.create_index(op.f('ix_requests_status'), 'requests', ['status'], unique=False)
    op.create_index('ix_requests_status_priority', 'requests', ['status', 'priority'], unique=False)
    op.create_index('ix_requests_type_status', 'requests', ['request_type', 'status'], unique=False)
    op.create_index('ix_requests_user_status', 'requests', ['user_id', 'status'], unique=False)
    op.create_index('ix_requests_assigned_status', 'requests', ['assigned_staff_id', 'status'], unique=False)

    # =========================================================================
    # Request Attachments Table
    # =========================================================================
    op.create_table(
        'request_attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False, comment='คำร้องที่เกี่ยวข้อง'),
        sa.Column('filename', sa.String(length=255), nullable=False, comment='ชื่อไฟล์'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='Path ของไฟล์'),
        sa.Column('file_url', sa.String(length=500), nullable=False, comment='URL สำหรับเข้าถึงไฟล์'),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='ขนาดไฟล์ (bytes)'),
        sa.Column('file_type', sa.String(length=100), nullable=True, comment='MIME type'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_request_attachments_id'), 'request_attachments', ['id'], unique=False)
    op.create_index(op.f('ix_request_attachments_request_id'), 'request_attachments', ['request_id'], unique=False)

    # =========================================================================
    # Notifications Table
    # =========================================================================
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='ผู้รับการแจ้งเตือน'),
        sa.Column('notification_type', sa.String(length=50), nullable=False, comment='ประเภทการแจ้งเตือน'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='หัวข้อการแจ้งเตือน'),
        sa.Column('message', sa.Text(), nullable=False, comment='เนื้อหาการแจ้งเตือน'),
        sa.Column('related_resource_type', sa.String(length=50), nullable=True),
        sa.Column('related_resource_id', sa.Integer(), nullable=True),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, comment='อ่านแล้วหรือไม่'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index('ix_notifications_user_read', 'notifications', ['user_id', 'is_read'], unique=False)
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_type_read', 'notifications', ['notification_type', 'is_read'], unique=False)


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('notifications')
    op.drop_table('request_attachments')
    op.drop_table('requests')
    op.drop_table('bookings')
    op.drop_table('equipments')
    op.drop_table('rooms')
    op.drop_table('users')

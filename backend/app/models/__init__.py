"""Import all models so SQLAlchemy can discover them."""

from app.models.user import User                          # noqa: F401
from app.models.group import Group                        # noqa: F401
from app.models.group_student import GroupStudent          # noqa: F401
from app.models.face_data import FaceData                  # noqa: F401
from app.models.attendance_session import AttendanceSession  # noqa: F401
from app.models.attendance import Attendance               # noqa: F401

import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django command to wait for the database to be available."""

    def handle(self, *args, **options):
        self.stdout.write("DB 연결을 기다리는 중...")
        maximum = 10
        for i in range(maximum):
            try:
                connections["default"].ensure_connection()
                self.stdout.write(self.style.SUCCESS("DB 연결에 성공했습니다!"))
                return
            except OperationalError:
                self.stdout.write(
                    f"DB 연결에 실패했습니다. ({i + 1}/{maximum}) 1초 후 재시도합니다..."
                )
                time.sleep(1)

        self.stdout.write(
            self.style.ERROR(f"{maximum}번의 시도 후에도 DB에 연결할 수 없습니다.")
        )

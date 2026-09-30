"""
base_oracle_database_interface.py
학교 Oracle DB(OracleDatabaseService) 기반 Repository를 위한 추상 베이스
- BaseDatabaseInterface를 상속한다. OracleDatabaseService가 DatabaseService와 같은 메서드를
  제공하므로 _fetch_one / _fetch_many / _fetch_val / _execute_many / _transaction 헬퍼를 그대로 쓴다
- Oracle 바인드 문법(:1, :name)을 쓰고, 테이블/뷰는 _qualify()로 소유 스키마를 붙여 참조한다
  (접속 계정과 뷰 소유 스키마가 다르기 때문 — 예: 접속 WS_VKEY, 소유 WS_VIEW)

사용법:
    class StudentRepository(BaseOracleDatabaseInterface):
        async def select_one(self, **kwargs) -> Optional[dict]:
            return await self._fetch_one(
                f"SELECT * FROM {self._qualify('STUDENT_VIEW')} WHERE STUDENT_NO = :1",
                kwargs["student_no"],
            )

        async def select_many(self, **kwargs) -> list[dict]:
            return await self._fetch_many(
                f"SELECT * FROM {self._qualify('STUDENT_VIEW')} WHERE DEPT_CD = :dept",
                {"dept": kwargs["dept_cd"]},
            )
"""

from ..database.oracle_database_service import OracleDatabaseService
from .base_database_interface import BaseDatabaseInterface


class BaseOracleDatabaseInterface(BaseDatabaseInterface):

    def __init__(self, db: OracleDatabaseService) -> None:
        super().__init__(db)
        self._owner = db.owner

    def _qualify(self, name: str) -> str:
        """소유 스키마가 설정되어 있으면 'OWNER.NAME', 없으면 NAME 그대로.
        식별자는 바인드할 수 없어 SQL에 직접 들어가므로 name에는 코드 상수만 넘길 것(사용자 입력 금지)."""
        return f"{self._owner}.{name}" if self._owner else name

    async def _execute(self, query: str, *args) -> int:
        """INSERT / UPDATE / DELETE (반환값: 영향받은 row 수)"""
        return await self._db.execute(query, *args)

    # select_one / select_many / insert / update / delete 는
    # BaseRepositoryInterface에서 상속되는 추상 프로시저이며, 서브클래스가 구현해야 한다.

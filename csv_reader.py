"""CSV parsing and validation."""

import csv
import sys
from pathlib import Path

from models import EmailRecord
from validators import validate_csv_columns, validate_csv_row


class CsvReadResult:
    """Immutable result of CSV parsing."""

    __slots__ = ("_records", "_errors")

    def __init__(self, records: tuple[EmailRecord, ...], errors: tuple[str, ...]):
        self._records = records
        self._errors = errors

    @property
    def records(self) -> tuple[EmailRecord, ...]:
        return self._records

    @property
    def errors(self) -> tuple[str, ...]:
        return self._errors

    @property
    def has_errors(self) -> bool:
        return len(self._errors) > 0

    @property
    def summary(self) -> str:
        return f"유효: {len(self._records)}건, 오류: {len(self._errors)}건"


def read_email_csv(file_path: str, encoding: str = "utf-8") -> CsvReadResult:
    """Parse and validate an email CSV file.

    Returns CsvReadResult containing valid records and error messages.
    """
    path = Path(file_path)

    if not path.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, encoding=encoding, newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                return CsvReadResult((), ("CSV 파일이 비어있습니다",))

            missing = validate_csv_columns(list(reader.fieldnames))
            if missing:
                return CsvReadResult(
                    (),
                    (f"필수 컬럼 누락: {', '.join(missing)}",),
                )

            records: list[EmailRecord] = []
            errors: list[str] = []

            for row_num, row in enumerate(reader, start=2):
                row_errors = validate_csv_row(row, row_num)
                if row_errors:
                    errors.extend(row_errors)
                    continue

                try:
                    record = EmailRecord(
                        name=row["name"].strip(),
                        email=row["email"].strip(),
                        subject=row["subject"].strip(),
                        body=row["body"].strip(),
                    )
                    records.append(record)
                except Exception as e:
                    errors.append(f"행 {row_num}: 데이터 검증 실패 - {e}")

            return CsvReadResult(tuple(records), tuple(errors))

    except UnicodeDecodeError:
        return CsvReadResult(
            (),
            (f"인코딩 오류: '{encoding}'으로 파일을 읽을 수 없습니다. --encoding 옵션을 확인하세요.",),
        )
    except Exception as e:
        return CsvReadResult((), (f"CSV 읽기 실패: {e}",))

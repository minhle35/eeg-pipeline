from datetime import datetime, timezone
from sqlalchemy import BigInteger, Double, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.db import Base

# BigInteger for PostgreSQL, Integer for SQLite (SQLite only auto-increments INTEGER)
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class EegSample(Base):
    __tablename__ = "eeg_samples"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    recording_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_sec: Mapped[float] = mapped_column(Double, nullable=False)
    value_uv: Mapped[float] = mapped_column(Double, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_eeg_patient_time", "patient_id", "recording_id", "timestamp_sec"),
        Index("idx_eeg_channel_time", "patient_id", "recording_id", "channel", "timestamp_sec"),
    )


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(Text, nullable=False)
    recording_id: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_start_sec: Mapped[float | None] = mapped_column(Double)
    chunk_end_sec: Mapped[float | None] = mapped_column(Double)
    num_samples: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

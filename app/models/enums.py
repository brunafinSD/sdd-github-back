from enum import StrEnum


class GameStatus(StrEnum):
    PENDING = "pending"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    PIX = "pix"
    ON_COURT = "on_court"


class TransactionType(StrEnum):
    GAME = "game"
    MANUAL_IN = "manual_in"
    MANUAL_OUT = "manual_out"
    TRANSFER = "transfer"


class CashTarget(StrEnum):
    COURT = "court"
    ADM = "adm"

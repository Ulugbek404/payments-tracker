import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

# Only years 1900-2099: keeps month arithmetic safely inside datetime.date limits.
MONTH_PATTERN = r"^(19|20)\d{2}-(0[1-9]|1[0-2])$"


class StudentIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, examples=["Алишер Каримов"])
    phone: str = Field(pattern=r"^\+?[\d\s()\-]{7,20}$", examples=["+998 90 123 45 67"])
    group: str = Field(min_length=1, max_length=50, examples=["English A1"])
    monthly_fee: int = Field(gt=0, description="Monthly fee, whole currency units", examples=[500000])


class StudentOut(StudentIn):
    id: int
    created_at: str


class PaymentIn(BaseModel):
    student_id: int
    amount: int = Field(gt=0, description="Whole currency units", examples=[300000])
    date: dt.date | None = Field(default=None, description="Payment date, defaults to today")


class PaymentOut(BaseModel):
    id: int
    student_id: int
    amount: int
    date: dt.date
    created_at: str


class DebtorOut(BaseModel):
    student_id: int
    name: str
    phone: str
    group: str
    monthly_fee: int
    paid: int
    debt: int


class DebtorsOut(BaseModel):
    month: str
    count: int
    total_debt: int
    debtors: list[DebtorOut]

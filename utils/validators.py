from datetime import datetime


def validate_amount(value):
    try:
        v = float(value)
        return v
    except Exception:
        raise ValueError('القيمة يجب أن تكون رقماً صالحاً')


def validate_date(value):
    try:
        dt = datetime.strptime(value, '%d-%m-%Y')
        return dt.strftime('%d-%m-%Y')
    except Exception:
        raise ValueError('التاريخ يجب أن يكون بالشكل DD-MM-YYYY')

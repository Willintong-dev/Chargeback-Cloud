CURRENCY_TO_USD = {"MXN": 17.0, "COP": 4000.0, "CLP": 950.0}
HIGH_VALUE_THRESHOLD_USD = 500.0
MERCHANT_RATIO_ALERT_THRESHOLD = 1.5


def currency_to_usd_sql(amount_col: str = "t.amount", currency_col: str = "t.currency") -> str:
    cases = "\n".join(
        f"            WHEN '{currency}' THEN {rate}"
        for currency, rate in CURRENCY_TO_USD.items()
    )
    return f"""(
            {amount_col} / CASE {currency_col}
{cases}
            ELSE 1.0
            END
        )"""

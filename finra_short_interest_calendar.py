"""Point-in-time FINRA short-interest publication dates (research only)."""
from __future__ import annotations
from datetime import date, timedelta
from pandas.tseries.holiday import USFederalHolidayCalendar

# Markets are open on these federal holidays; Good Friday is a market holiday.
MARKET_OPEN_FEDERAL = {(2022, 10, 10), (2022, 11, 11), (2023, 10, 9), (2023, 11, 10), (2024, 10, 14), (2024, 11, 11), (2025, 10, 13), (2025, 11, 11), (2026, 10, 12), (2026, 11, 11)}
GOOD_FRIDAYS = {date(2022,4,15),date(2023,4,7),date(2024,3,29),date(2025,4,18),date(2026,4,3)}
def market_holidays(start: date,end: date)->set[date]:
 h={x.date() for x in USFederalHolidayCalendar().holidays(start=start,end=end)}
 h.difference_update(date(*x) for x in MARKET_OPEN_FEDERAL); return h|{x for x in GOOD_FRIDAYS if start<=x<=end}
def publication_date(settlement: date)->date:
 holidays=market_holidays(settlement,settlement+timedelta(days=20)); seen=0; day=settlement
 while seen<7:
  day+=timedelta(days=1)
  if day.weekday()<5 and day not in holidays: seen+=1
 return day

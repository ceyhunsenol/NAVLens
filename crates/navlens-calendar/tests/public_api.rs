use navlens_calendar::{
    CalendarError, MarketCalendar, MarketDate, PricingError, ReturnPeriod, SessionKind,
    SessionOverride,
};

fn date(year: i32, month: u8, day: u8) -> MarketDate {
    MarketDate::new(year, month, day).expect("test date should be valid")
}

#[test]
fn weekdays_are_open_and_weekends_are_closed_by_default() {
    let calendar = MarketCalendar::default();

    assert_eq!(calendar.session_on(date(2026, 7, 17)), SessionKind::FullDay);
    assert_eq!(calendar.session_on(date(2026, 7, 18)), SessionKind::Closed);
    assert_eq!(calendar.session_on(date(2026, 7, 19)), SessionKind::Closed);
}

#[test]
fn explicit_sessions_override_weekday_rules() {
    let overrides = [
        SessionOverride::new(date(2026, 5, 26), SessionKind::HalfDay),
        SessionOverride::new(date(2026, 5, 27), SessionKind::Closed),
        SessionOverride::new(date(2026, 5, 30), SessionKind::FullDay),
    ];
    let calendar = MarketCalendar::new(&overrides).expect("unique overrides");

    assert_eq!(calendar.session_on(date(2026, 5, 26)), SessionKind::HalfDay);
    assert_eq!(calendar.session_on(date(2026, 5, 27)), SessionKind::Closed);
    assert_eq!(calendar.session_on(date(2026, 5, 30)), SessionKind::FullDay);
}

#[test]
fn half_day_is_an_open_session() {
    assert!(SessionKind::HalfDay.is_open());
    assert!(!SessionKind::Closed.is_open());
}

#[test]
fn finds_next_open_date_after_holiday_and_weekend() {
    let overrides = [SessionOverride::new(date(2026, 7, 20), SessionKind::Closed)];
    let calendar = MarketCalendar::new(&overrides).expect("unique overrides");

    assert_eq!(
        calendar.next_open_date(date(2026, 7, 17)),
        Ok(date(2026, 7, 21))
    );
}

#[test]
fn rejects_duplicate_session_dates() {
    let duplicate_date = date(2026, 5, 26);
    let overrides = [
        SessionOverride::new(duplicate_date, SessionKind::HalfDay),
        SessionOverride::new(duplicate_date, SessionKind::Closed),
    ];

    assert_eq!(
        MarketCalendar::new(&overrides),
        Err(CalendarError::DuplicateSessionDate(duplicate_date))
    );
}

#[test]
fn rejects_invalid_gregorian_dates() {
    assert_eq!(
        MarketDate::new(2026, 2, 29),
        Err(CalendarError::InvalidDate {
            year: 2026,
            month: 2,
            day: 29,
        })
    );
}

#[test]
fn calculates_calendar_days_since_same_day() {
    let d = date(2026, 7, 22);
    assert_eq!(d.calendar_days_since(d), 0);
}

#[test]
fn calculates_calendar_days_since_across_month_boundary() {
    let jan31 = date(2026, 1, 31);
    let feb01 = date(2026, 2, 1);
    assert_eq!(feb01.calendar_days_since(jan31), 1);
    assert_eq!(jan31.calendar_days_since(feb01), -1);
}

#[test]
fn calculates_calendar_days_since_across_leap_year_february() {
    let feb28_leap = date(2024, 2, 28);
    let mar01_leap = date(2024, 3, 1);
    assert_eq!(mar01_leap.calendar_days_since(feb28_leap), 2);

    let feb28_non_leap = date(2025, 2, 28);
    let mar01_non_leap = date(2025, 3, 1);
    assert_eq!(mar01_non_leap.calendar_days_since(feb28_non_leap), 1);
}

#[test]
fn calculates_calendar_days_since_negative_difference() {
    let earlier = date(2026, 1, 1);
    let later = date(2026, 1, 10);
    assert_eq!(earlier.calendar_days_since(later), -9);
    assert_eq!(later.calendar_days_since(earlier), 9);
}

#[test]
fn public_api_exports_period_decimal_return() {
    use navlens_calendar::PeriodDecimalReturn;
    use navlens_core::DecimalReturn;

    let start = date(2026, 1, 1);
    let end = date(2026, 1, 2);
    let ret = DecimalReturn::new(0.05).expect("valid return");

    let p = PeriodDecimalReturn::new(start, end, ret).expect("valid period return");
    assert_eq!(p.period_start_date(), start);
    assert_eq!(p.period_end_date(), end);
    assert_eq!(p.decimal_return(), ret);

    let period = p.period();
    assert_eq!(period.period_start_date(), start);
    assert_eq!(period.period_end_date(), end);

    let from_p = PeriodDecimalReturn::from_period(period, ret);
    assert_eq!(from_p.period_start_date(), start);
    assert_eq!(from_p.decimal_return(), ret);
}

#[test]
fn return_period_validates_dates() {
    let d1 = date(2026, 1, 1);
    let d2 = date(2026, 1, 2);

    let valid = ReturnPeriod::new(d1, d2).expect("chronological dates");
    assert_eq!(valid.period_start_date(), d1);
    assert_eq!(valid.period_end_date(), d2);

    assert_eq!(
        ReturnPeriod::new(d1, d1),
        Err(PricingError::InvalidReturnPeriod {
            period_start_date: d1,
            period_end_date: d1,
        })
    );

    assert_eq!(
        ReturnPeriod::new(d2, d1),
        Err(PricingError::InvalidReturnPeriod {
            period_start_date: d2,
            period_end_date: d1,
        })
    );
}

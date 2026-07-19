use navlens_calendar::{CalendarError, MarketCalendar, MarketDate, SessionKind, SessionOverride};

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

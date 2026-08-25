from onyx.server.sales_copilot.api import RoiRequest, calculate_ai_roi


def test_roi_is_transparent_and_positive() -> None:
    result = calculate_ai_roi(RoiRequest(employee_count=3000, average_salary=180000, hours_saved_per_employee=1, automation_rate=0.2, software_cost=500000))
    assert result.annual_labor_saving == 8_100_000
    assert result.net_saving == 7_600_000
    assert result.roi == 15.2
    assert "monthly_hours_saved" in result.formula

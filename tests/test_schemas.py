"""
tests/test_schemas.py
---------------------
Unit test suite for Pydantic v2 schemas and header rotator.
"""

import pytest
from pydantic import ValidationError
from app.schemas import JobItem, IngestionMetrics, CircuitBreakerStateEnum
from app.engine import AntiDetectionHeaderRotator


def test_job_item_validation_remoteok_raw_format():
    raw_payload = {
        "id": "999888",
        "position": "Senior Backend Engineer",
        "company": "Stripe",
        "location": "Worldwide",
        "url": "/remote-jobs/stripe-senior-backend-engineer",
        "salary_min": "150000",
        "salary_max": "220000",
        "tags": ["python", "fastapi", "postgres"],
        "date": 1710000000,
    }

    job = JobItem.model_validate(raw_payload)
    assert job.id == "999888"
    assert job.title == "Senior Backend Engineer"
    assert job.company == "Stripe"
    assert job.location == "Worldwide"
    assert job.url == "https://remoteok.com/remote-jobs/stripe-senior-backend-engineer"
    assert job.salary_min == 150000
    assert job.salary_max == 220000
    assert job.tags == ["python", "fastapi", "postgres"]
    assert job.source == "RemoteOK"


def test_job_item_validation_himalayas_raw_format():
    raw_payload = {
        "guid": "himalayas-777",
        "title": "Staff Python Developer",
        "companyName": "Acme Corp",
        "locationRestrictions": ["US", "Canada"],
        "applicationUrl": "https://himalayas.app/jobs/123",
        "minSalary": 160000,
        "maxSalary": 210000,
        "categories": ["Software Engineering"],
        "source": "Himalayas",
    }

    job = JobItem.model_validate(raw_payload)
    assert job.id == "himalayas-777"
    assert job.title == "Staff Python Developer"
    assert job.company == "Acme Corp"
    assert job.location == "US, Canada"
    assert job.url == "https://himalayas.app/jobs/123"
    assert job.salary_min == 160000
    assert job.salary_max == 210000
    assert job.tags == ["software engineering"]
    assert job.source == "Himalayas"


def test_job_item_skips_legal_disclaimer():
    raw_disclaimer = {"legal": "Please read our Terms of Service before using this API"}
    with pytest.raises(ValueError):
        JobItem.model_validate(raw_disclaimer)


def test_anti_detection_header_rotator():
    profile = AntiDetectionHeaderRotator.get_random_profile()
    assert "User-Agent" in profile
    assert "Accept" in profile
    assert "Accept-Language" in profile
    assert "Sec-Fetch-Dest" in profile

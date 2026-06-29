from agents.requirements_analyst import BuildRequest, build_prompt


def test_build_prompt_uses_user_owned_site_title_not_scraped_title():
    body = BuildRequest(
        requirements="Create a website for a doctor clinic",
        build_mode="agentic_only",
        output_target="legacy",
        email="hello@abaaba.example.com",
        phone="+91 98765 43210",
        location="Chennai, India",
        niche="doctor clinic",
        categories=["General Consultation", "Preventive Care"],
        scraped_title="BrightPath Consulting",
        nav_links=["Home", "Services", "About", "Contact", "Book Appointment"],
    )
    site = {
        "title": "Aba Aba Clinic",
        "name": "aba-aba",
        "description": "A trusted family clinic providing consultations and preventive care.",
        "theme": "modern",
        "logo_url": "",
        "classification": "generic",
        "classification_label": "generic",
        "classification_group": "general",
        "cart_features": "[]",
    }

    prompt, _ = build_prompt(body, site, extra_context="Reference site title: BrightPath Consulting")

    assert "WEBSITE NAME: Aba Aba Clinic" in prompt
    assert "WEBSITE NAME: BrightPath Consulting" not in prompt
    assert "WEBSITE BUILD SPECIFICATION is the highest-priority source of truth." in prompt
    assert "Reference URLs, scraped content, and web research may inform structure" in prompt
    assert "Business Email: hello@abaaba.example.com" in prompt
    assert "Business Phone: +91 98765 43210" in prompt
    assert "Business Location: Chennai, India" in prompt
    assert "Exact Service / Category Names: General Consultation | Preventive Care" in prompt


def test_build_prompt_disables_booking_form_without_prefix():
    body = BuildRequest(
        requirements="Create a business profile site",
        build_mode="agentic_only",
        output_target="legacy",
        nav_links=["Home", "Services", "About", "Contact"],
        booking_prefix=None,
    )
    site = {
        "title": "Acme Studio",
        "name": "acme-studio",
        "description": "Creative services and support.",
        "theme": "modern",
        "logo_url": "",
        "classification": "generic",
        "classification_label": "generic",
        "classification_group": "general",
        "cart_features": "[]",
    }

    prompt, _ = build_prompt(body, site, extra_context="")

    assert "BOOKING/ORDER FORM MODE: DISABLED" in prompt
    assert "Order/Booking Reference Prefix:" not in prompt
    assert "DOMAIN-SPECIFIC BOOKING/INQUIRY SERVICES" not in prompt


def test_build_prompt_enables_booking_form_with_prefix():
    body = BuildRequest(
        requirements="Create a business profile site",
        build_mode="agentic_only",
        output_target="legacy",
        booking_prefix="BK",
        classification="startup_saas",
        classification_label="Startup SaaS",
        classification_group="Technology",
    )
    site = {
        "title": "Acme Studio",
        "name": "acme-studio",
        "description": "Creative services and support.",
        "theme": "modern",
        "logo_url": "",
        "classification": "startup_saas",
        "classification_label": "Startup SaaS",
        "classification_group": "Technology",
        "cart_features": "[]",
    }

    prompt, _ = build_prompt(body, site, extra_context="")

    assert "BOOKING/ORDER FORM MODE: ENABLED" in prompt
    assert "Order/Booking Reference Prefix: BK" in prompt
    assert "DOMAIN-SPECIFIC BOOKING/INQUIRY SERVICES" in prompt
"""
Smoke tests that exercise modules A / B / C against synthetic fixtures.
No network, no Playwright — purely validates the parsing + scoring logic.

Run from the backend/ directory:
    python -m pytest -xvs tests/test_modules.py
or directly:
    python tests/test_modules.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crawler import CrawlResult, FetchedPage
from app.modules.trust import run_trust_scan
from app.modules.consistency import run_consistency_check
from app.modules.forms import run_form_audit
from app.scoring import compute_score, teaser_score


HOME_HTML = """
<html><head><title>Acme Bakery</title></head><body>
  <h1>Welcome to Acme Bakery (M) Sdn Bhd</h1>
  <p>Free delivery, no minimum order!</p>
  <p>We ship across Klang Valley.</p>
  <a href="/about">About</a>
  <a href="/contact">Contact</a>
  <a href="/faq">FAQ</a>
  <a href="/shipping">Shipping</a>
  <a href="/privacy">Privacy Policy</a>
  <a href="https://wa.me/60123456789">WhatsApp us</a>
  <p>JAKIM Halal certified.</p>
  <p>What our customers say: 5-star rated since 2018.</p>
</body></html>
"""

ABOUT_HTML = """
<html><body>
  <h1>About Acme</h1>
  <p>Registered: Acme Bakery (M) Sdn Bhd, Co. No. 202001028025.</p>
  <p>15 Jalan Mayang, Petaling Jaya, 47301, Malaysia.</p>
</body></html>
"""

CONTACT_HTML = """
<html><body>
  <h1>Contact</h1>
  <p>Email us at hello@acme.test or call <a href="tel:+60123456789">+60 12 345 6789</a>.</p>
  <p>Address: 15 Jalan Mayang, Petaling Jaya, 47301.</p>
  <form id="contact-form">
    <label for="n">Your name</label><input id="n" name="name" required>
    <label for="e">Your email</label><input id="e" name="email" type="email" required>
    <label for="m">Your message</label><textarea id="m" name="message" required></textarea>
    <label for="company">Company name</label><input id="company" name="company" required>
    <label for="budget">Budget</label><input id="budget" name="budget" required>
    <label for="industry">Industry</label><input id="industry" name="industry" required>
    <label for="src">How did you hear about us?</label><input id="src" name="how_did_you_hear" required>
    <button type="submit">Send</button>
  </form>
</body></html>
"""

FAQ_HTML = """
<html><body>
  <h1>FAQ</h1>
  <p>Same-day orders must be placed before 7 PM.</p>
  <p>Free delivery above RM 200.</p>
  <p>We deliver to KL, Selangor and JB.</p>
</body></html>
"""

SHIPPING_HTML = """
<html><body>
  <h1>Shipping Policy</h1>
  <p>Cut-off for same-day delivery is 5:00 PM.</p>
  <p>Shipping to Klang Valley only.</p>
</body></html>
"""

POLICY_HTML = "<html><body><h1>Privacy Policy</h1><p>We respect your data.</p></body></html>"


def build_fixture_crawl() -> CrawlResult:
    pages = [
        FetchedPage("https://acme.test/", "home", "Acme", HOME_HTML, "Acme Bakery Sdn Bhd " + HOME_HTML, "https://acme.test/"),
        FetchedPage("https://acme.test/about", "about", "About", ABOUT_HTML,
                    "Acme Bakery (M) Sdn Bhd Co. No. 202001028025 15 Jalan Mayang Petaling Jaya 47301", "https://acme.test/about"),
        FetchedPage("https://acme.test/contact", "contact", "Contact", CONTACT_HTML,
                    "Email us at hello@acme.test or call +60 12 345 6789. Address: 15 Jalan Mayang Petaling Jaya 47301.", "https://acme.test/contact"),
        FetchedPage("https://acme.test/faq", "faq", "FAQ", FAQ_HTML,
                    "Same-day orders must be placed before 7 PM. Free delivery above RM 200. We deliver to KL Selangor and JB.", "https://acme.test/faq"),
        FetchedPage("https://acme.test/shipping", "shipping", "Shipping", SHIPPING_HTML,
                    "Cut-off for same-day delivery is 5:00 PM. Free delivery no minimum. Shipping to Klang Valley only.", "https://acme.test/shipping"),
        FetchedPage("https://acme.test/privacy", "policy", "Privacy", POLICY_HTML, "Privacy Policy We respect your data.", "https://acme.test/privacy"),
    ]
    return CrawlResult(
        start_url="https://acme.test/",
        base_url="https://acme.test",
        pages=pages,
        ssl_ok=True,
    )


def main():
    crawl = build_fixture_crawl()

    print("=== Trust scan ===")
    trust = run_trust_scan(crawl)
    for t in trust:
        print(f"  [{t.status:>7}] {t.name} :: {t.note}")
    assert any(t.key == "ssl" and t.status == "pass" for t in trust), "SSL should pass"
    assert any(t.key == "entity" and t.status == "pass" for t in trust), "Entity should pass"
    assert any(t.key == "contact" and t.status == "pass" for t in trust), "Contact should pass"
    assert any(t.key == "cert" and t.status == "pass" for t in trust), "Certification should pass"

    print("\n=== Consistency check ===")
    conflicts = run_consistency_check(crawl)
    for c in conflicts:
        print(f"  CONFLICT: {c.topic}")
        for s in c.sides:
            print(f"    - {s.page_intent} :: {s.value}")
    topics = {c.topic for c in conflicts}
    assert "Same-day delivery cut-off time" in topics, "Should detect 5pm vs 7pm conflict"
    assert "Free-delivery condition" in topics, "Should detect free-delivery conflict"

    print("\n=== Form audit ===")
    forms = run_form_audit(crawl, monthly_visitors=10000, avg_order_value=300)
    print(f"  Forms found: {len(forms.forms)}")
    for f in forms.forms:
        print(f"  - {f.page_intent} :: total={f.total_fields} required={f.required_fields} essential={f.essential_required} extra={f.extra_required}")
    assert len(forms.forms) >= 1, "Should find the contact form"
    assert forms.extra_required_total >= 3, f"Should flag extra required fields, got {forms.extra_required_total}"
    print(f"  Estimated monthly loss: ${forms.estimated_monthly_loss_usd}")
    assert forms.estimated_monthly_loss_usd > 0, "Should compute a loss"

    print("\n=== Score ===")
    score, breakdown = compute_score(trust, conflicts, forms)
    print(f"  Real score   : {score}/100  breakdown={breakdown}")
    print(f"  Teaser score : {teaser_score(score)}/100")
    assert 0 <= score <= 100
    assert teaser_score(score) <= score

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()

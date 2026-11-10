# ClearSettle PYUSD

A merchant-side trust and dispute-assistance prototype for cross-border commerce,
built for a PayPal + AI hackathon. Built by one developer. **This is a prototype
that runs only against sandbox and simulated services. No real money moves.**

## The problem

Small cross-border merchants lose payment disputes because buyers do not understand
protection rules up front, evidence is scattered, and dispute replies are slow and
hard to write. ClearSettle tries to address this with: explained consent before
payment, structured evidence capture with integrity fingerprints, and an AI-drafted
dispute reply that the merchant must review and approve.

## What is real and what is simulated

| Feature | Status |
|---|---|
| Merchant register and login (hashed passwords, sessions) | Real |
| Order creation and ownership checks | Real |
| Buyer consent: one-time, expiring, hashed link | Real |
| Card payment via Braintree Sandbox (a PayPal service), transaction ID stored | Real sandbox API calls, test cards only |
| Evidence upload: JPEG/PNG signature check, random filenames, SHA256 | Real |
| Evidence integrity re-check against stored SHA256 | Real |
| AI policy explanation (English and Bengali) from verified policy text | Real LLM calls (Google Gemini) |
| AI dispute reply draft from recorded order facts | Real LLM calls (Google Gemini) |
| Merchant review, edit and approval of the draft | Real |
| Dispute itself and the "submit" step | **Simulated.** Nothing is sent to PayPal or Braintree. |
| PYUSD settlement | **Simulated.** A SIM-reference is recorded. No PYUSD, wallet or blockchain transfer. |
| PayPal REST API, webhooks, real Disputes API | **Not implemented** |
| OCR and image classification | **Not implemented** |

Payments use Braintree, a PayPal service. The PayPal REST Orders API was not used because developer account sign-up was unavailable in the developer's region.

## Architecture

    Browser (Jinja2 pages)
        |
    Flask app (routes) ---- services ---- MongoDB
        |                       |
        |                       +-- Braintree Sandbox (payment)
        |                       +-- Google Gemini API (explanations, dispute draft)
        +-- uploads/ (evidence images, random names, SHA256 stored in MongoDB)

Folders: app/routes (pages), app/services (logic), app/utils (helpers),
app/templates (HTML), app/data/policies.json (verified policy text).

## Responsible AI

- The AI only explains **verified** policy text (marked verified, with a source URL).
  Unverified policies, such as Seller Protection and Fees, are blocked.
- The dispute draft receives only facts read from the database. Missing facts are
  passed as null and must be written as "not recorded".
- Prompts use delimiter tags and instructions to treat supplied text as data. This
  reduces but does not eliminate prompt-injection risk.
- AI output is always a draft. Nothing is approved without the merchant clicking Approve.
- Bengali text is AI-generated and has been reviewed by the developer only.
- SHA256 shows a file is unchanged since upload. It does not prove a photo is
  genuine or when it was taken.
- No claim is made that this improves dispute win rates.

## Security measures

Hashed passwords, session login, merchant ownership checks on every order route,
CSRF tokens on forms, single-use hashed consent tokens, image signature validation,
5 MB upload limit, random stored filenames, secrets in .env (git-ignored), login
throttle after 5 failures, amounts read from the database and never from the browser.

## AI tool disclosure

- Google Gemini API (model set in GEMINI_MODEL) for runtime explanations and drafts.
- Claude (Anthropic) was used as a coding and teaching assistant during development.
  The developer ran, tested and reviewed the code.

## Setup

Requirements: Python 3.10+, MongoDB running locally, a Braintree Sandbox account,
a Gemini API key.

    git clone https://github.com/Iffeleen/ClearSettle-PYUSD.git
    cd ClearSettle-PYUSD
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    # edit .env with your own keys
    python run.py

When `python run.py` starts, your browser opens the login page. If it does not, open `http://127.0.0.1:5001/login` yourself. This address only works on your own computer while the app is running. It is not a public website.
Register a merchant, and create an order.
Sandbox test card: 4111 1111 1111 1111 with any future expiry date.
Some sandbox amounts (roughly 2000 to 2999) are declined on purpose by Braintree.

## Demo flow

1. Create an order, read the explained policy, accept as merchant.
2. Open the buyer link, accept as buyer.
3. Pay with the sandbox card.
4. Save courier and tracking number, upload three evidence images, verify integrity.
5. Create a simulated dispute, generate the AI draft, edit and approve it.
6. Run the simulated PYUSD settlement.

## Known limitations

- Prototype only. Sandbox payments and simulated disputes and settlement.
- Only Buyer Protection policy text is verified. Seller Protection and Fees are not.
- Login throttle is in memory and single process.
- Evidence checks are completeness checks, not image quality or authenticity checks.
- No webhooks, no real PayPal Disputes API, no OCR.
- Consent records an acknowledgment of a ClearSettle explanation. It is not
  acceptance of PayPal's legal terms.
- Not legal or financial advice, and no regulatory compliance is claimed.

## Future work

Real PayPal REST and Disputes API integration with webhook signature verification,
verified PYUSD settlement if supported, OCR of shipping labels, more languages,
PayPal as a payment method in Braintree Drop-in, Fastlane for repeat checkout.

## License

MIT, see LICENSE.

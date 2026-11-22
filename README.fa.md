# SDK رسمی پایتون ویپانو

[English README](README.md) · [کالکشن Postman](docs/voipano-webservice.postman_collection.json)

کتابخانه پایتون برای اتصال ساده به **Voipano Public Webservice API v1** که هر **۲۳ درخواست** کالکشن مورخ **۲۰۲۶/۱۱/۲۱** را پوشش می‌دهد. بدون وابستگی به Django، Flask یا FastAPI و قابل استفاده در همه برنامه‌های معمول پایتون.

## پیش‌نیاز و نصب

- حداقل **Python 3.11**؛ قدیمی‌ترین نسخه پایتون تحت پشتیبانی امنیتی در نوامبر ۲۰۲۶.
- توکن معتبر وب‌سرویس ویپانو.

پس از اولین انتشار در PyPI:

```bash
python -m pip install voipano
```

متغیرهای محیطی برنامه خود را تنظیم کنید؛ توکن را هرگز در Git ثبت نکنید:

```dotenv
VOIPANO_API_TOKEN=your-private-token
VOIPANO_SERVICE_ID=
```

استفاده:

```python
from voipano import VoipanoClient

with VoipanoClient() as client:
    services = client.services.all()
    contacts = client.contacts.all({"page": 1, "per_page": 20})
    client.contacts.create({"primary_number": "09120000000", "first_name": "Ali"})

    # این عملیات تماس واقعی برقرار می‌کند؛ فقط پس از دریافت مجوز اجرا کنید:
    # client.calls.otp("09120000000", purpose="login")
    # client.calls.click_to_call("09120000000", "09121111111", timeout=30)
    # client.calls.secure_call("09120000000", "09121111111", retry_count=0)
```

## امکانات

- مشاهده سرویس‌های متصل به توکن؛ مدیریت مخاطبین و گروه‌ها؛ ورود گروهی تا ۳۰۰۰ مخاطب.
- گزارش تماس، صندوق صوتی، صوت انتظار و دریافت یا دانلود فایل‌های ضبط‌شده.
- OTP صوتی، تماس سریع و تماس امن؛ مدیریت وبهوک عمومی و اختصاصی ۴ نوع رویداد.
- پشتیبانی از چند توکن/سرویس به‌صورت مستقل با `with_token()` و `for_service()`.
- خطاهای نوع‌بندی‌شده، تایم‌اوت قابل تنظیم، شناسه درخواست و جلوگیری از Retry خودکار.

```python
customer = client.with_token("customer-token").for_service("service-id")
reports = customer.call_reports.all({"page": 1})
customer.close()
```

### دریافت فایل ضبط‌شده

برای فایل‌های بزرگ از دانلود استریم استفاده کنید. پوشه مقصد باید از قبل وجود داشته باشد و فایل مقصد موجود نباشد:

```python
from pathlib import Path

file_path = client.recordings.download_call(
    "cdr-id", "call-details-record-id", Path("private/audio/call.wav")
)
voice_path = client.recordings.download_voicemail(
    "vm-id", "default", "1001", Path("private/audio/message.wav")
)
```

در مستندات Postman، دو شناسه `cdr_id` و `call_details_record_id` نمونه با یکدیگر متفاوت‌اند، در حالی که متن توضیحی آن‌ها را یکسان می‌داند. تا مشخص‌شدن قرارداد واقعی، هر دو ورودی الزامی هستند.

### نکته امنیتی وبهوک

کالکشن فعلی **شیوه امضای وبهوک ورودی را مستند نکرده است**. به همین دلیل `WebhookReceiver` به‌صورت پیش‌فرض تمام درخواست‌ها را رد می‌کند و هیچ مسیر ورودی خودکاری فعال نیست. پس از تأیید روش امضا و پیشگیری از replay از سمت سرور، Verifier اختصاصی خودتان را متصل کنید. وبهوک عمومی و اختصاصی خروجی از طریق `client.webhooks` قابل تنظیم است.

### پایداری و خطاها

خطاهای 401، 403، 404، 422، 429 و 5xx به Exceptionهای مجزا تبدیل می‌شوند. انتقال ناموفق به `TransportError` و پاسخ نامعتبر به `UnexpectedResponseError` تبدیل می‌شود. درخواست‌ها بازگردانی خودکار یا پیگیری Redirect ندارند. بعد از تایم‌اوت تماس یا OTP، بدون تأیید وضعیت درخواست قبلی آن را تکرار نکنید.

## تست و انتشار

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m build
python -m twine check dist/*
```

فایل‌های GitHub Actions آماده‌اند: تست در `tests.yml` و انتشار امن در `publish.yml` با **Trusted Publishing** بدون API Token در مخزن. برای اولین انتشار باید در حساب PyPI یک **Pending Trusted Publisher** برای پروژه `voipano` بسازید و مالک GitHub، نام ریپازیتوری، نام workflow برابر `publish.yml` و environment برابر `pypi` را ثبت کنید. سپس پس از موفقیت تست‌های GitHub، تگ `v1.0.1` را Push کنید. در GitHub هم environment با نام `pypi` ایجاد شود. اگر نام Repository با `voipano/python-voipano` متفاوت بود، لینک‌های `pyproject.toml` را اصلاح کنید.

مستندات Postman پاسخ‌های نمونه و جزئیات امنیتی وبهوک را ندارد؛ بنابراین تست‌های Mock جایگزین بررسی واقعی API نمی‌شوند.

مجوز: MIT.

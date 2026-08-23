# وضعیت تولید کتاب

## اصل

این فایل وضعیت قابل‌ادامه پروژه را نگه می‌دارد. آخرین وضعیت معتبر باید به‌گونه‌ای ثبت شود که کار در نشست بعدی بدون بازسازی context ادامه پیدا کند.

## وضعیت‌های اصلی

`PLANNED` → `RESEARCHING` → `EVIDENCE_READY` → `OUTLINE_READY` → `DRAFTING` → `SCIENTIFIC_REVIEW` → `EDUCATIONAL_REVIEW` → `FACT_CHECK` → `REVISION` → `FINAL_QA` → `PUBLISHED`

وضعیت‌های اضطراری:

`PAUSED`، `BLOCKED`، `FAILED`

## قواعد انتقال

- بدون Evidence کافی، ورود به `DRAFTING` برای ادعاهای اصلی مجاز نیست.
- بدون Scientific Review، ورود به `FINAL_QA` مجاز نیست.
- بدون Educational Review و Fact Check، انتشار مجاز نیست.
- `PUBLISHED` فقط وقتی معتبر است که Markdown، منابع و خروجی‌های مشتق‌شده با یک نسخه مشخص قابل ردیابی باشند.

## State فعلی Pilot

- Project: Intelligent-Digital-Transformation-Course
- Pilot: Chapter 01 — Foundations
- Current status: `SCIENTIFIC_REVIEW`
- Baseline: محتوای موجود در main حفظ شده و فقط به‌عنوان baseline تاریخی استفاده می‌شود.
- Evidence pack: `BOOK/01-foundations/EVIDENCE-PACK-v1.md`
- Outline: `BOOK/01-foundations/OUTLINE-v2.md`
- Core references: `BOOK-SYSTEM/CORE-REFERENCES.md`
- Draft status: بدنه اصلی بخش‌های 1.1 تا 1.9 بازنویسی شده و مطالعه موردی، تمرین‌ها و منابع فصل به‌روزرسانی شده‌اند.
- Citation status: شماره‌گذاری ارجاعات کتابی یکدست‌سازی شده است.
- Scientific review focus: صحت ادعاهای مربوط به Digital Transformation، Agentic AI، AI-Native، نقش عامل انسانی، مرزبندی تعریف‌های عملیاتی و سازگاری با نقشه ده‌فصلی.
- Pending: اصلاحات ناشی از Scientific Review، سپس Educational Review و Fact Check.
- Publishing gate: CLOSED
- Last state update: 2026-08-23

## Session resume protocol

در شروع هر نشست:

1. همین فایل خوانده شود.
2. وضعیت فصل و آخرین task مشخص شود.
3. Evidence و Reviewهای مرتبط بازیابی شوند.
4. فقط context لازم وارد نشست شود.
5. پس از پایان نشست، state، منابع جدید، ادعاهای باز و next task به‌روزرسانی شود.

## توقف ایمن

اگر ابزار یا محدودیت استفاده مانع ادامه شد، کار باید در یکی از وضعیت‌های `PAUSED` یا `BLOCKED` ثبت شود. متن ناقص نباید با برچسب نهایی منتشر شود.

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
- Current status: `FINAL_QA`
- Baseline: محتوای موجود در main حفظ شده و فقط به‌عنوان baseline تاریخی استفاده می‌شود.
- Evidence pack: `BOOK/01-foundations/EVIDENCE-PACK-v1.md`
- Outline: `BOOK/01-foundations/OUTLINE-v2.md`
- Core references: `BOOK-SYSTEM/CORE-REFERENCES.md`
- Scientific review: `BOOK/01-foundations/SCIENTIFIC-REVIEW-v1.md`
- Educational review: `BOOK/01-foundations/EDUCATIONAL-REVIEW-v1.md`
- Fact check: `BOOK/01-foundations/FACT-CHECK-v1.md`
- Completed rewrite: sections 01-introduction, 02-learning-objectives, 03-evolution, 04-core-concepts, 05-socio-technical, 06-ai-native, 07-success-and-failure, 08-case-study, 09-summary-and-exercises
- Publishing gate: CLOSED until Final QA validates the assembled chapter and DOCX/PDF outputs
- Last state update: 2026-08-23
- Next task: Assemble canonical Chapter 01, run final structural/reference/output QA, then prepare Word/PDF artifacts

## Session resume protocol

در شروع هر نشست:

1. همین فایل خوانده شود.
2. وضعیت فصل و آخرین task مشخص شود.
3. Evidence و Reviewهای مرتبط بازیابی شوند.
4. فقط context لازم وارد نشست شود.
5. پس از پایان نشست، state، منابع جدید، ادعاهای باز و next task به‌روزرسانی شود.

## توقف ایمن

اگر ابزار یا محدودیت استفاده مانع ادامه شد، کار باید در یکی از وضعیت‌های `PAUSED` یا `BLOCKED` ثبت شود. متن ناقص نباید با برچسب نهایی منتشر شود.

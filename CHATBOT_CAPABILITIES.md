# Document Assistant Capabilities

This document describes the current capabilities and limitations of the Digitized Filing System Document Assistant.

**Document codes:** New uploads receive auto-generated codes in the format `{CategoryCode}-{Year}-{Sequence}` (e.g. `RPT-2026-000001`). Category abbreviations are auto-generated or editable in Manage Categories. When the abbreviation changes or a document is reassigned to another category, auto-generated codes update their prefix only (sequence preserved). Legacy manual codes remain searchable and unchanged.

## Current Capabilities

### 1. Greetings And Help

The assistant responds naturally to short conversational openers before document search runs.

Example prompts:

```text
Hi
Hello
Hey
Good morning
hi, hello
help
what can you do
```

Example answer:

```text
Hi! I'm the Document Assistant for the Digitized Filing System. I can help you find and explore documents within your access scope.

Try asking:
- "How many files do I have?"
- "List all documents"
- "Show documents in Test folder"
- "What is inside code RPT-2026-000001?"
```

### 2. Count Accessible Documents

The assistant can count documents available within the logged-in user's access scope.

Example prompts:

```text
How many files do I have?
How many current files do I have?
How many documents do I have?
```

Example answer:

```text
You currently have 2 accessible documents.
```

### 3. Count Documents In A Folder

The assistant can count documents inside a specific accessible folder.

Example prompts:

```text
How many files are in Test folder?
How many documents do I have in SDD folder?
How many records are inside Reports folder?
```

Example answer:

```text
Test contains 1 accessible document.
```

### 4. Find Folders

The assistant can search for accessible folders by name.

Example prompts:

```text
Find folder Test
Can you find the folder of Test?
Where is Test folder?
```

Example answer:

```text
I found these accessible folder matches:
- Test (Path: Test, Org Unit: CISC)
```

### 5. List Accessible Documents

The assistant lists up to **5 accessible documents** at a time for the current user. If more exist, the total count is included in the answer.

Example prompts:

```text
List all documents
Show all files
All records
```

Example answer (few documents):

```text
Here are the first 2 accessible documents I found:
- april_accomplishment.pdf (Code: RPT-2026-000002, Category: Reports, Folder: SDD)
- organized_demo_presentation_data.pdf (Code: RPT-2026-000001, Category: test, Folder: Test)
```

Example answer (many documents):

```text
Here are the first 5 accessible documents I found:
- file1.pdf (Code: RPT-2026-000001, Category: Reports, Folder: SDD)
- file2.pdf (Code: RPT-2026-000002, Category: Reports, Folder: SDD)
...
Showing 5 of 847.
Use the Documents page to browse the full list.
```

### 6. List Documents In A Folder

The assistant lists up to **5 documents** inside a specific accessible folder and includes the folder total when more exist.

Example prompts:

```text
Show documents in Test folder
List files inside SDD folder
Find all records in Reports folder
```

Example answer (single document):

```text
Here are documents I found in Test:
- organized_demo_presentation_data.pdf (Code: RPT-2026-000001, Category: test, Folder: Test)
```

Example answer (many documents):

```text
Reports has 847 accessible documents.
Showing 5 of 847:
- Audit Reports.pdf (Code: AUD-2026-000001, Category: Audit Reports, Folder: Reports)
...
Use the Documents page to browse the full list.
```

### 7. Find Documents By Code

The assistant can find documents by document code, even when the code appears inside a natural sentence.

Example prompts:

```text
Find code RPT-2026-000001
What is inside code RPT-2026-000001?
What is the document RPT-2026-000002 about?
```

### 8. PDF Content Questions

If the PDF has extractable text, the assistant can answer questions about the PDF content through OpenRouter.

Example prompts:

```text
What is inside code RPT-2026-000001?
Summarize document RPT-2026-000002.
What is organized_demo_presentation_data.pdf about?
```

Important note:

Image-only scanned PDFs are fully supported. If a PDF contains no selectable text (or selectable text is below a configurable threshold), the system automatically falls back to the Tesseract OCR pipeline to extract text from the document pages.

### 9. Keyword, Title, Category, Folder, And PDF Text Search

The assistant can search accessible documents using:

- document code
- title
- file name
- folder name
- folder path
- category
- short description
- keywords
- extracted PDF text

### 10. Date, Month, And Filing Year Filters

The assistant can answer date-filtered count and list questions.

For uploaded/added date questions, it uses `created_at`.

Example prompts:

```text
How many files are in Test folder this month?
How many files were uploaded in May 2026?
Show documents added today.
Show files from January.
```

Limited follow-up support:

```text
User: Show documents in the month of April.
User: In May?
```

The frontend resolves the second question using the previous month-based query.

Document context follow-up (after a code or document search returns a match):

```text
User: 120-12
User: What is about?
User: Summarize it
```

The frontend rewrites vague follow-ups using the last matched document (code or title) before the API call runs.

Not yet supported:

```text
User: Show documents in Test folder.
User: Summarize the second one.
```

For filing-year questions, it uses `filing_year`.

Example prompts:

```text
How many documents have filing year 2026?
Show files with filing year 2026.
```

Field rule:

- Use `created_at` for uploaded/added date questions.
- Use `filing_year` only for filing-year questions.

Reason:

Audit/document offices often need to know when a document was added to the system. For chatbot questions like "uploaded this month", "added today", or "files in May 2026", the correct field should be `created_at` because it reflects when the record entered DFS. The `filing_year` field should only be used when the user specifically asks about the document's filing year, such as "filing year 2026".

Recommended examples:

```text
How many files were uploaded this month?
How many files were added in Test folder this month?
Show documents uploaded in May 2026.
How many documents have filing year 2026?
```

Recommended response style:

- For count questions, return a count only.
- For list questions, show at most **5** matching documents and say if there are more.
- Avoid dumping a very large list directly into the chat.
- When more than 5 documents match, suggest the Documents page for full browsing.

List preview limit:

- Default maximum preview: **5** documents (`CHATBOT_LIST_LIMIT`).
- Count queries still return the full scoped total.
- Chat API rate limit: **30 requests/minute** per authenticated user.

### 11. Category And Requestor Filters

The assistant can count or list documents by category and requestor/requisitioner.

Example prompts:

```text
How many files are in Reports category?
Show documents in test category.
How many files were requested by SDD GODS?
Search documents by requisitioner Ralph.
Show files requested by Ralph.
```

Supported requestor/requisitioner aliases include common misspellings such as:

```text
requestionaire
requisitionaire
requestioner
requester
```

Recommended fields:

- Use `category` for category counts and category filtering.
- Use `requestor` for requisitioner/requestor questions.

## Current Limitations

### 1. Limited Conversation Memory

The assistant remembers **one document context** for vague follow-ups (e.g. `what is about?` after `120-12`) and **month filters** for date follow-ups. It does not yet handle ordinals or multi-document lists.

Example that works:

```text
User: 120-12
User: What is about?
```

Example limitation:

```text
User: Show documents in Test folder.
User: Summarize the second one.
```

### 3. Limited Analytics

Basic counts and filters are supported, but advanced reporting is not yet implemented.

Not yet supported:

```text
How many reports per category?
Which folder has the most documents?
How many files did each department upload?
Show upload trend by month.
```

### 4. Limited Fuzzy Matching

The assistant handles some natural wording, but not all typo-heavy or vague questions.

Example:

```text
wat docs i hav lst mnth in tst fld?
```

This may fail until stronger intent parsing or fuzzy matching is added.

### 5. Contextual References (`this folder`, `this category`)

When you open the **Document Assistant** from the Documents page, it receives your **current view context**:

- Selected **folder** (not All Files, not an org-unit node)
- Active **category filter** (when not set to All)

The drawer shows **Using current view: Folder: … · Category: …** when context is active.

Supported examples (with Reports folder selected and/or Audit Reports category filtered):

```text
All files in this folder
How many files in this category
Show all documents here
List everything in the current folder
How many files in this folder
```

These are rewritten internally to explicit names (e.g. `All files in Reports folder`) before search.

**Requirements:**

- Open the assistant from the Documents page while viewing the folder or category you mean.
- Virtual **All Files** or an **org-unit** tree node alone does not provide folder context — use an explicit folder name instead.

Explicit names still work everywhere:

```text
Show all files in Reports folder
How many files are in Reports category?
```

### 6. List All Folders

There is **no true "catalog all folders"** intent yet. Folder lookup searches by **name** (max 5 matches).

| Query | What actually happens |
|-------|------------------------|
| `Find folder Reports` | Works — finds folders named Reports |
| `Where is Test folder?` | Works |
| `List all folders` | Partial — may search for a name fragment, not list every folder |
| `All folders` | Partial — same limitation |
| `Show every folder in my org` | Not supported |

## Manual Test Queries

Use these in the **Document Assistant** (logged in). Replace sample names with folders, categories, and codes that exist in your environment.

Legend:

- **Yes** — direct intent or search should answer reliably
- **Partial** — may work, wrong interpretation, or search/LLM fallback
- **No** — not supported (contextual `this folder` / `this category` work when the Documents page view is passed in)

### Greetings And Help

| Query | Expected |
|-------|----------|
| `Hi` | Yes — greeting + example prompts |
| `Hello` | Yes |
| `Hey` | Yes |
| `Good morning` | Yes |
| `help` | Yes — capabilities list |
| `what can you do` | Yes |
| `Hi` (send again within same session) | Yes — shorter repeat greeting |

### Count — All Accessible Files (scoped by role)

| Query | Expected |
|-------|----------|
| `How many files do I have?` | Yes — full scoped count |
| `How many documents do I have?` | Yes |
| `How many current files do I have?` | Yes |
| `Count all my records` | Partial — needs count + document terms |

### Count — By Folder (use your folder name)

| Query | Expected |
|-------|----------|
| `How many files are in Reports folder?` | Yes |
| `How many documents do I have in Test folder?` | Yes |
| `How many records are inside SDD folder?` | Yes |
| `How many files in this folder` | Yes — when a folder is selected on Documents page |

### Contextual References (Documents page view)

Open the assistant while a **folder** is selected and/or a **category filter** is active.

| Query | Expected |
|-------|----------|
| `All files in this folder` | Yes — with folder selected |
| `How many files in this folder` | Yes — with folder selected |
| `Show all documents here` | Yes — with folder selected |
| `List everything in the current folder` | Yes — with folder selected |
| `How many files in this category` | Yes — with category filter active |
| `Show documents in this category` | Yes — with category filter active |
| `All files in this folder` (on All Files view) | **No** — select a folder first |

### Count — By Category (use your category name)

| Query | Expected |
|-------|----------|
| `How many files are in Audit Reports category?` | Yes |
| `How many documents in Reports category?` | Yes |
| `How many files in this category` | Yes — when a category filter is active on Documents page |

### Count — By Date / Filing Year

| Query | Expected |
|-------|----------|
| `How many files were uploaded this month?` | Yes |
| `How many files are in Reports folder this month?` | Yes |
| `How many files were uploaded in May 2026?` | Yes |
| `How many documents have filing year 2026?` | Yes |
| `Show documents added today` | Partial — list, not count |

### Count — By Requestor

| Query | Expected |
|-------|----------|
| `How many files were requested by Ralph?` | Yes — if requestor exists |
| `How many documents requested by SDD GODS?` | Yes — if requestor exists |

### List All Files (max 5 preview + total)

| Query | Expected |
|-------|----------|
| `List all documents` | Yes — up to 5 + total if more |
| `Show all files` | Yes |
| `All records` | Yes |
| `all files` | Yes |
| `Find all documents` | Yes |

### List Files In A Folder (max 5 preview + folder total)

| Query | Expected |
|-------|----------|
| `Show documents in Reports folder` | Yes |
| `List files inside Test folder` | Yes |
| `Find all records in SDD folder` | Yes |
| `All files in Reports folder` | Yes |
| `All files in this folder` | Yes — when a folder is selected on Documents page |

### List — Category / Requestor / Date Filters

| Query | Expected |
|-------|----------|
| `Show documents in Audit Reports category` | Yes — up to 5 |
| `Show files in Reports category` | Yes |
| `Show documents in test category` | Yes |
| `Show files requested by Ralph` | Yes |
| `Show documents uploaded in May 2026` | Yes |
| `Show files with filing year 2026` | Yes |
| `Show documents in this category` | Yes — when a category filter is active on Documents page |

### Find Folders (by name, max 5)

| Query | Expected |
|-------|----------|
| `Find folder Test` | Yes |
| `Where is Reports folder?` | Yes |
| `Can you find the folder of SDD?` | Partial |
| `List all folders` | **Partial** — not a full folder catalog |
| `All folders` | **Partial** |
| `Show every folder` | **Partial** |

### Find By Document Code

| Query | Expected |
|-------|----------|
| `Find code AUD-2026-000001` | Yes |
| `What is inside code RPT-2026-000001?` | Yes — may use LLM if PDF text exists |
| `What is the document RPT-2026-000002 about?` | Yes — LLM + grounded context |

### Keyword / Title Search (search + LLM, max 5 matches)

| Query | Expected |
|-------|----------|
| `Find files related to audit` | Partial — search fallback |
| `Where is the file with code 01-242?` | Yes — code search |
| `Which folder contains the RRL PDF?` | Partial — search/LLM |
| `Find digitization documents` | Partial |

### Combined Filters (folder + date, etc.)

| Query | Expected |
|-------|----------|
| `How many files were added in Reports folder this month?` | Yes |
| `Show documents in Test folder uploaded in May 2026` | Partial — list up to 5 |
| `How many files in Reports category this month?` | Partial — category + date |

### Anti-Spam / UX (frontend)

| Action | Expected |
|--------|----------|
| Send same query twice within 30 seconds | Yes — duplicate nudge |
| Press Enter rapidly many times | Yes — cooldown + disabled send |
| Send more than 30 messages/minute | Yes — rate limit message |

### Document Context Follow-Up

| Query sequence | Expected |
|----------------|----------|
| `120-12` then `What is about?` | Yes — rewritten to code question |
| `Find code AUD-2026-000001` then `Summarize it` | Yes |
| `Find code AUD-2026-000001` then `Tell me about it` | Yes |
| List 5 docs then `Summarize the second one` | **No** — ordinal not supported yet |

### Public DFS Assistant (not logged in)

| Query | Expected |
|-------|----------|
| `Hi` | Yes — public greeting |
| `How do I upload a PDF?` | Yes — FAQ |
| `What are the user roles?` | Yes |
| `Show all files` | Yes — blocked, login required |
| `List all documents` | Yes — blocked, login required |

### Not Supported Yet

```text
How many reports per category?
Which folder has the most documents?
Show all files under CISC org unit
Summarize the second one
List every folder in the system
Show upload trend by month
```

## Access Rules

The assistant only answers using documents and folders the logged-in user can access.

- Admin can search all active documents.
- Department Head can search their OrgUnit and child OrgUnits.
- Staff can search their own OrgUnit scope.

The assistant should not reveal inaccessible documents, credentials, tokens, API keys, environment values, or private account data.

## Recommended Next Phases

### Phase 3: Department And Advanced Analytics

Add support for:

```text
How many documents are in each category?
Show all files under CISC.
Which folder has the most documents?
Show upload trend by month.
```

### Phase 4: Conversation Memory

Add better chat context so follow-up questions work naturally.

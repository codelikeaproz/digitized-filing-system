# Document Assistant Capabilities

This document describes the current capabilities and limitations of the Digitized Filing System Document Assistant.

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
- "What is inside code 01-12551?"
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

The assistant can list the first accessible documents for the current user.

Example prompts:

```text
List all documents
Show all files
All records
```

Example answer:

```text
Here are the first 2 accessible documents I found:
- april_accomplishment.pdf (Code: 04-98391, Category: Reports, Folder: SDD)
- organized_demo_presentation_data.pdf (Code: 01-12551, Category: test, Folder: Test)
```

### 6. List Documents In A Folder

The assistant can list documents inside a specific accessible folder.

Example prompts:

```text
Show documents in Test folder
List files inside SDD folder
Find all records in Reports folder
```

Example answer:

```text
Here are documents I found in Test:
- organized_demo_presentation_data.pdf (Code: 01-12551, Category: test, Folder: Test)
```

### 7. Find Documents By Code

The assistant can find documents by document code, even when the code appears inside a natural sentence.

Example prompts:

```text
Find code 01-12551
What is inside code 01-12551?
What is the document 04-98391 about?
```

### 8. PDF Content Questions

If the PDF has extractable text, the assistant can answer questions about the PDF content through OpenRouter.

Example prompts:

```text
What is inside code 01-12551?
Summarize document 04-98391.
What is organized_demo_presentation_data.pdf about?
```

Important note:

Image-only scanned PDFs may not work unless OCR is added. The current extractor reads selectable PDF text using `pypdf`.

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
- For list questions, show the first few matching documents and say if there are more.
- Avoid dumping a very large list directly into the chat.

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

### 1. No OCR Yet

The assistant can read PDF text only if the text is selectable/extractable.

Not yet supported:

```text
Read text from scanned image-only PDFs.
Extract handwritten text.
Read blurry scanned documents.
```

Future improvement:

- Add OCR using Tesseract, OCRmyPDF, or a cloud OCR service.

### 2. Limited Conversation Memory

The assistant does not deeply remember earlier turns.

Example limitation:

```text
User: Show documents in Test folder.
User: Summarize the second one.
```

This may not work reliably yet because each backend answer mainly uses the current query.

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

### Phase 4: OCR For Scanned PDFs

Add OCR so scanned image-only PDFs can be searched and summarized.

### Phase 5: Conversation Memory

Add better chat context so follow-up questions work naturally.

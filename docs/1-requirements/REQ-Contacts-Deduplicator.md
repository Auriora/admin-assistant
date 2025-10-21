---
title: "AI-Assisted Contact Deduplication & Quality Pipeline"
id: "REQ-contacts-deduplicator"
type: [ requirements, workflow ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "DD-MM-YYYY"
tags: [contacts, deduplication, ai, workflow]
links:
  tooling: []
---

# AI-Assisted Contact Deduplication & Quality Pipeline

- **Owner**: Auriora Team
- **Status**: Draft
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [Developers, Data Analysts]

## 1. Purpose

Develop a script and workflow to automatically detect and help resolve duplicate contacts, enforce minimum contact data standards, and produce consistent display names. This process will leverage both algorithmic/fuzzy matching and AI-powered analysis for ambiguous cases.

## 2. Context

### Justification for AI-Assistance

Traditional logic can catch *exact* duplicates and many fuzzy ones, but AI offers significant advantages:
- It can resolve ambiguous cases involving nicknames, initials, typos, or missing surnames by using the full context of the contact information.
- It can suggest canonical formats, fix field inconsistencies, and flag probable corporate, group, or transactional/spam entries.
- It can provide a trusted “merge & correct” suggestion list for rapid human review, accelerating the cleanup process.

## 3. Details

### 3.1. Data Acquisition & Preparation

- **Fetch Contacts**: Retrieve all contacts via the Microsoft Graph API, using paging and batching to handle large datasets efficiently.
- **Normalize Fields**: Standardize data by trimming whitespace, lowercasing emails, unifying phone numbers to a consistent format (e.g., E.164), and stripping extraneous characters from names.

### 3.2. Field Validation

- **Required Fields**: Each contact must have at least one of the following: Display Name, Email, or Phone.
- **Format Checks**: Validate that emails match a standard regex (RFC-5322), phone numbers are in a consistent international format, and display names are in title case without junk symbols.
- **Flagging**: Contacts missing required fields will be flagged for review.

### 3.3. Algorithmic Duplicate Detection

- **Exact Match Hashing**: Group contacts by normalized display name, primary email, phone numbers, and composite keys (e.g., name + email).
- **Fuzzy Matching**: Use algorithms like Levenshtein or Jaro-Winkler distance to identify contacts with similar names, emails, or phone numbers.
- **Clustering**: Create clusters of potential duplicates, noting the reason for the grouping (e.g., “Same email & similar name”).

### 3.4. AI-Powered Deduplication & Resolution

- **Prepare Data for AI**: For each cluster, create a minimized JSON or table with only the relevant fields.
- **AI Prompting**: Use a prompt template to ask the AI to identify which contacts are the same person, suggest a canonical version, and flag suspicious entries.
- **Workflow**: Send each cluster to the AI, parse the suggestions, and automatically apply high-confidence merges while flagging ambiguous cases for human review.

### 3.5. Display Name Consistency & Enforcement

- **Standardize Names**: Apply title case and a standard order (e.g., “Given Surname”). Enforce patterns for organizational entries if needed (e.g., “Contact Name [Company]”).
- **Flagging**: Non-standard names will be flagged for review.

### 3.6. Reporting & Logging

- **Reports**: Generate reports listing exact duplicates, likely duplicates (with confidence scores), contacts with missing information, and a summary of all actions taken.
- **Logging**: Log all changes and AI recommendations for transparency, error recovery, and potential retraining.

## 4. Decisions / Actions

### Implementation Outline (Pseudocode)

```python
contacts = fetch_all_contacts_via_api()
contacts = normalize_contacts(contacts)
validated, missing = validate_format_and_completeness(contacts)
exact_dupes, fuzzy_dupes, clusters = detect_duplicates_contacts(contacts)

for cluster in clusters:
    ai_input = format_cluster_for_ai(cluster)
    ai_result = send_to_ai(ai_input, prompt_template)
    process_ai_result(ai_result)

enforce_display_name_style(contacts)
final_report = create_dedupe_and_quality_report(contacts, clusters, missing, ai_results)
output_report(final_report)
```

### Next Steps

1.  Implement the base script for data acquisition, normalization, and hashing.
2.  Integrate fuzzy search for approximate duplicate detection.
3.  Build the logic for chunking and formatting ambiguous clusters for the AI.
4.  Create the prompt and API pipeline for an LLM (e.g., OpenAI).
5.  Implement logging and reporting, then iterate based on real-world data.

# References

- **Future Extensions**:
    - **Feedback Loop**: Collect user corrections to fine-tune future AI inferences.
    - **Batch-Processing UI**: Create a user interface for rapid review and acceptance of merge suggestions.
    - **Integration**: Connect with an organizational directory or HRIS for stricter quality control.

"""
Golden dataset for RAG evaluation: questions where you already know the
correct source document (and ideally the correct answer), so retrieval and
generation quality can be measured against ground truth instead of guessing.

HOW TO FILL THIS IN:
1. Replace `expected_source_file` with the ACTUAL filename as it's stored
   in document_chunks.source_file (check with:
   SELECT DISTINCT source_file FROM document_chunks;)
2. Write `reference_answer` as the actual correct answer in your own words -
   this is only needed for the RAGAS FactualCorrectness metric (Step 3);
   retrieval evaluation (Step 2) only needs expected_source_file.
3. Aim for 15-30 questions covering ALL 5 of your documents, not just one -
   an eval set skewed toward one document will hide problems with the others.
4. Include a few "hard" questions on purpose: ambiguous phrasing, questions
   that could plausibly match two documents, questions using different
   words than the document itself uses. Easy questions make your numbers
   look better than real-world performance will be.

Below are TEMPLATE examples based on topics mentioned in your project so
far - replace the placeholder filenames and verify the reference answers
actually match your real documents before trusting any results.
"""

GOLDEN_DATASET = [
    {
        # VERIFIED against the actual 4_Company_Rules_and_Regulations.pdf
        # (Section 8): the document does NOT state a specific hours limit -
        # it only requires compliance with external hours-of-service law.
        # This question is intentionally kept to show what a document
        # DOESN'T say - useful for checking the agent says "not specified"
        # rather than inventing a number.
        "question": "What is the maximum number of consecutive working hours for a driver?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "The document does not specify a numeric hours limit. It only requires that drivers not operate a vehicle while fatigued or in violation of applicable hours-of-service regulations.",
    },
    {
        "question": "What happens if an invoice is not paid by its due date?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "An invoice not paid in full by its due date is marked Overdue and may incur a late fee of 1.5% of the outstanding balance due per month, or the maximum permitted by law, whichever is lower.",
    },
    {
        "question": "Under what status can cargo not be released to a customer?",
        "expected_source_file": "1_Company_Policies.pdf",
        "reference_answer": "Cargo release records move through Pending -> Approved -> Released. Goods must not be handed over while a release is in Pending status.",
    },
    {
        "question": "What does the code of conduct say about bribery?",
        "expected_source_file": "3_Code_of_Conduct.pdf",
        "reference_answer": "Employees must not offer, give, solicit, or accept bribes, kickbacks, or improper payments to secure business, expedite a shipment, or influence a decision.",
    },
    {
        "question": "What is required before a vehicle marked Maintenance can be dispatched again?",
        "expected_source_file": "1_Company_Policies.pdf",
        "reference_answer": "A vehicle marked Maintenance may not be dispatched until its status is updated to Available following inspection sign-off.",
    },
    {
        # Verified: Section 3, standard-priority cancellation rule.
        "question": "How much notice do I need to cancel a standard shipment without a fee?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "Standard-priority shipments may be cancelled free of charge up to 24 hours before scheduled pickup. Cancelling inside 24 hours may incur a charge of up to 25% of the base shipping charge.",
    },
    {
        # Deliberately similar to the one above but for Express/Overnight -
        # a "hard" pair to check retrieval doesn't confuse the two windows
        # (24hrs/25% vs 6hrs/50%) or return the wrong one.
        "question": "What's the cancellation policy for an Overnight priority shipment?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "Express and Overnight shipments may be cancelled free of charge up to 6 hours before scheduled pickup; cancelling inside that window may incur up to 50% of the base shipping charge.",
    },
    {
        # Verified: Section 7, warehouse storage/demurrage rule.
        "question": "How many days can goods be stored in the warehouse for free?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "Goods may be stored free of charge for the first 5 calendar days following the entry date on the warehouse receipt. Storage beyond 5 days incurs a daily demurrage fee.",
    },
    {
        # Verified: Section 6, cargo claims deadline.
        "question": "How long do I have to file a claim for damaged cargo after delivery?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "Cargo damage or loss claims must be reported within 7 calendar days of the delivery date to be eligible for review.",
    },
    {
        # Verified: Section 9, safety incident reporting window.
        "question": "How quickly must a warehouse safety incident be reported to management?",
        "expected_source_file": "4_Company_Rules_and_Regulations.pdf",
        "reference_answer": "Warehouse and vehicle safety incidents must be logged and reported to management within 24 hours of occurrence.",
    },
    # Add 10-20 more covering 2_Standard_Operating_Procedures.pdf and any
    # remaining sections of the other 4 documents you haven't tested yet.
]
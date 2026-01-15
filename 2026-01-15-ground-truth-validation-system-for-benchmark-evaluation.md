# Ground Truth Validation Plan for Benchmark Evaluation

## Overview

Create an automated system to validate the quality of both review droid comments and golden comments by inspecting the actual PR code. This will establish a "ground truth" evaluation that goes beyond simple string matching.

## Problem Statement

Current evaluation has three critical issues:
1. **Incomplete Golden Set**: Golden comments don't capture all real bugs in PRs
2. **Vague Golden Comments**: Many lack file/line specifics, making matching ambiguous
3. **No Ground Truth**: We don't verify if comments (droid or golden) are actually valid

## Proposed Solution

Build an agent-based validation system that:
1. Checks out each PR's actual code
2. Validates droid comments against real code changes
3. Audits golden comments for completeness and clarity
4. Generates a comprehensive ground truth report

---

## Implementation Plan

### Phase 1: Setup and Infrastructure

#### 1.1 Create Validation Script Structure
```
scripts/
├── validate_ground_truth.py           # Main orchestration script
├── validators/
│   ├── __init__.py
│   ├── code_inspector.py              # Checkout PR and inspect code
│   ├── comment_validator.py           # Validate individual comments
│   ├── golden_auditor.py              # Audit golden comments
│   └── report_generator.py            # Generate comparison reports
```

#### 1.2 Repository Setup
- Use existing droid-sentry repo at `/Users/user/review-droid-benchmark/work/droid-sentry`
- Create a working copy/branch for checking out different PRs
- Store validation results in `results/ground_truth_validation/`

---

### Phase 2: Code Inspection Module

#### 2.1 PR Checkout and Diff Extraction
For each PR #6-15:
```python
def checkout_pr(pr_number: int):
    """
    Checkout PR code and extract changes
    
    Returns:
    - pr_diff: Full diff of changes
    - changed_files: List of modified files with line numbers
    - pr_metadata: Title, description, commit info
    """
```

Implementation:
- Use `gh pr checkout {pr_number}` or `git fetch origin pull/{pr_number}/head`
- Extract diff: `git diff {base_branch}...{pr_branch}`
- Parse changed files and line ranges
- Keep full context (not truncated)

#### 2.2 Code Context Builder
```python
def build_code_context(file_path: str, line_number: int, context_lines: int = 10):
    """
    Extract code context around a specific line
    
    Returns:
    - code_snippet: Code with surrounding context
    - imports: Relevant imports from file
    - class_context: If inside a class, the class definition
    - function_context: If inside a function, the function signature
    """
```

---

### Phase 3: Comment Validation Module

#### 3.1 Droid Comment Validator
For each droid comment in `pr_x_comments.json`:

```python
def validate_droid_comment(comment: dict, pr_context: dict) -> dict:
    """
    Validate if droid's comment identifies a real bug
    
    Inputs:
    - comment: Droid comment with body, file, line, diff_hunk
    - pr_context: Full PR code and changes
    
    Process:
    1. Extract the specific code location from comment
    2. Get full code context (not just diff_hunk)
    3. Use LLM to analyze:
       - Is this a real bug? (Yes/No/Uncertain)
       - Severity if real (Critical/High/Medium/Low)
       - Root cause analysis
       - Would this cause runtime errors, logic bugs, or other issues?
       - False positive reasoning if not a bug
    
    Returns:
    {
      "comment_id": int,
      "file": str,
      "line": int,
      "droid_comment": str,
      "validation": {
        "is_valid_bug": bool,
        "confidence": "high" | "medium" | "low",
        "severity": str,
        "bug_type": str,  # e.g., "AttributeError", "logic bug", "type error"
        "impact": str,
        "reasoning": str,
        "code_evidence": str
      }
    }
    """
```

**LLM Prompt Strategy:**
```
You are a senior Python developer reviewing code changes in a production system.

PR Context:
{full_pr_diff}

Specific Code Location:
File: {file_path}
Line: {line_number}

Code Context:
{code_with_context}

Review Comment:
{droid_comment_body}

Task: Determine if this comment identifies a REAL bug that would cause issues in production.

Consider:
1. Would this code raise an exception at runtime?
2. Would this cause incorrect behavior/logic bugs?
3. Are there performance/security implications?
4. Is the comment technically accurate about the issue?
5. Could this be a false positive (overly defensive, hypothetical scenario)?

Respond in JSON format:
{
  "is_valid_bug": true/false,
  "confidence": "high/medium/low",
  "severity": "critical/high/medium/low/none",
  "bug_type": "runtime error/logic bug/performance/security/false positive",
  "impact": "detailed description of what would happen",
  "reasoning": "why this is or isn't a real bug",
  "code_evidence": "specific code that proves/disproves the bug"
}
```

#### 3.2 Batch Validation
```python
def validate_all_droid_comments(pr_number: int) -> list[dict]:
    """
    Validate all droid comments for a PR
    
    Process:
    1. Load pr_{pr_number}_comments.json
    2. Checkout PR code
    3. Validate each comment
    4. Aggregate results
    
    Returns: List of validation results
    """
```

---

### Phase 4: Golden Comment Auditor

#### 4.1 Golden Comment Analysis
For each golden comment for a PR:

```python
def audit_golden_comment(golden_comment: dict, pr_context: dict, droid_comments: list) -> dict:
    """
    Audit a golden comment for quality and correctness
    
    Checks:
    1. Is this actually a bug in the code?
    2. Is the comment specific enough? (has file/line location)
    3. Is it clear what bug is being described?
    4. Did droid catch this bug?
    5. Are there similar bugs droid found that aren't in golden?
    
    Returns:
    {
      "golden_comment": str,
      "severity": str,
      "audit": {
        "is_real_bug": bool,
        "is_specific": bool,  # Has file/line numbers
        "is_clear": bool,     # Unambiguous description
        "clarity_score": int, # 1-5 scale
        "specificity_score": int, # 1-5 scale
        "matched_by_droid": bool,
        "droid_comment_id": int | null,
        "missing_details": list[str],  # What details are missing
        "vagueness_issues": list[str], # What makes it vague
        "validation": {
          "verified_in_code": bool,
          "evidence": str,
          "reasoning": str
        }
      }
    }
    """
```

**LLM Prompt for Golden Audit:**
```
You are auditing a benchmark comment for quality.

PR Context:
{full_pr_diff}

Golden Comment:
"{golden_comment_text}"
Severity: {severity}

Droid Comments Found:
{list_of_droid_comments}

Tasks:
1. Find this bug in the actual code changes (provide file:line if found)
2. Rate comment specificity (1-5): Does it have file, line, specific variable names?
3. Rate comment clarity (1-5): Is it clear what bug is being described?
4. Verify if this is a real bug: Inspect code and confirm
5. Check if droid caught it: Compare with droid comments
6. Identify vagueness: What details are missing or unclear?

Respond in JSON format:
{
  "is_real_bug": true/false,
  "bug_location": {"file": "...", "line": 123} or null,
  "is_specific": true/false,
  "is_clear": true/false,
  "clarity_score": 1-5,
  "specificity_score": 1-5,
  "matched_by_droid": true/false,
  "matching_droid_comment_id": int or null,
  "missing_details": ["file path", "line number", "variable name"],
  "vagueness_issues": ["unclear which function", "multiple possible locations"],
  "code_evidence": "actual code showing the bug",
  "reasoning": "detailed explanation"
}
```

#### 4.2 Completeness Check
```python
def check_golden_completeness(pr_number: int, 
                               golden_comments: list,
                               validated_droid_comments: list) -> dict:
    """
    Check if golden set is complete
    
    Finds:
    1. Valid droid bugs NOT in golden (missed by golden)
    2. Invalid golden comments (false positives in golden)
    3. Bugs that BOTH missed (requires deep code inspection)
    
    Returns:
    {
      "golden_missed": list[dict],  # Valid droid bugs not in golden
      "golden_false_positives": list[dict],  # Invalid golden comments
      "total_golden": int,
      "total_valid": int,
      "completeness_score": float  # % of real bugs captured
    }
    """
```

---

### Phase 5: Report Generation

#### 5.1 Per-PR Report
```python
def generate_pr_report(pr_number: int, 
                       droid_validations: list,
                       golden_audit: list,
                       completeness: dict) -> dict:
    """
    Generate comprehensive report for one PR
    
    Sections:
    1. PR Overview (title, changes summary)
    2. Droid Comment Analysis
       - Valid bugs: count, severity breakdown
       - False positives: count, reasoning
       - Validation confidence distribution
    3. Golden Comment Audit
       - Quality scores (clarity, specificity)
       - Verified vs unverified bugs
       - Vagueness issues
    4. Completeness Analysis
       - Bugs in droid but not golden
       - Bugs in golden but not validated
       - Estimated total bugs in PR
    5. Recommendations
       - Which golden comments to improve/remove
       - Which droid comments were correct
       - Missing bugs that should be added to golden
    """
```

#### 5.2 Aggregate Report
```python
def generate_aggregate_report(all_pr_reports: list) -> dict:
    """
    Generate summary across all PRs
    
    Metrics:
    1. Droid Performance (validated)
       - True precision: % of droid comments that are real bugs
       - True recall: % of real bugs droid caught
       - False positive rate
    
    2. Golden Set Quality
       - Completeness: % of real bugs in golden
       - Clarity average: avg clarity score
       - Specificity average: avg specificity score
       - False positive rate in golden
    
    3. Gap Analysis
       - Bugs both missed: count and types
       - Common bug patterns golden misses
       - Common false positive patterns in droid
    
    4. Recommendations
       - Improve golden set: which comments to add/edit/remove
       - Improve droid: what patterns it's missing
       - Evaluation methodology improvements
    """
```

#### 5.3 Output Files
Generate in `results/ground_truth_validation/`:
```
ground_truth_validation/
├── pr_6_validation.json           # Per-PR detailed results
├── pr_7_validation.json
├── ...
├── pr_15_validation.json
├── aggregate_report.json          # Summary across all PRs
├── VALIDATION_SUMMARY.md          # Human-readable summary
├── GOLDEN_IMPROVEMENTS.md         # Specific recommendations for golden set
└── droid_analysis/
    ├── true_positives.json        # Validated droid bugs
    ├── false_positives.json       # Droid mistakes
    └── missed_bugs.json           # Real bugs droid missed
```

---

### Phase 6: Execution and Usage

#### 6.1 Main Execution Script
```python
# scripts/validate_ground_truth.py

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='run_2026-01-15', 
                       help='Run folder to validate')
    parser.add_argument('--prs', default='6-15',
                       help='PR range to validate')
    parser.add_argument('--repo-path', 
                       default='/Users/user/review-droid-benchmark/work/droid-sentry')
    args = parser.parse_args()
    
    # Parse PR range
    start_pr, end_pr = map(int, args.prs.split('-'))
    pr_numbers = range(start_pr, end_pr + 1)
    
    results = []
    for pr_num in pr_numbers:
        print(f"Validating PR #{pr_num}...")
        
        # 1. Checkout PR and get context
        pr_context = checkout_pr(pr_num, args.repo_path)
        
        # 2. Load droid comments
        droid_comments = load_droid_comments(args.run, pr_num)
        
        # 3. Validate droid comments
        droid_validations = validate_all_droid_comments(
            droid_comments, pr_context
        )
        
        # 4. Load and audit golden comments
        golden_comments = load_golden_comments(pr_context['title'])
        golden_audit = audit_golden_comments(
            golden_comments, pr_context, droid_validations
        )
        
        # 5. Check completeness
        completeness = check_golden_completeness(
            pr_num, golden_comments, droid_validations
        )
        
        # 6. Generate PR report
        pr_report = generate_pr_report(
            pr_num, droid_validations, golden_audit, completeness
        )
        results.append(pr_report)
        
        # Save individual PR report
        save_pr_report(pr_report, args.run)
    
    # 7. Generate aggregate report
    aggregate = generate_aggregate_report(results)
    save_aggregate_report(aggregate, args.run)
    
    print(f"\n✅ Validation complete!")
    print(f"Results saved to results/ground_truth_validation/")

if __name__ == '__main__':
    main()
```

#### 6.2 Usage
```bash
# Validate run_2026-01-15
cd ~/review-droid-benchmark
ANTHROPIC_API_KEY="sk-ant-..." venv/bin/python3 scripts/validate_ground_truth.py \
  --run run_2026-01-15 \
  --prs 6-15

# Validate specific PRs
ANTHROPIC_API_KEY="sk-ant-..." venv/bin/python3 scripts/validate_ground_truth.py \
  --run run_2026-01-15 \
  --prs 6-8
```

---

## Expected Outputs

### 1. Validated Metrics (vs current metrics)

**Current (string-matching based):**
- Precision: 38.9%
- Recall: 21.9%
- Based on LLM semantic matching against golden

**After Validation (ground-truth based):**
- True Precision: % of droid comments that are REAL bugs
- True Recall: % of REAL bugs droid caught
- Based on actual code inspection

### 2. Golden Set Quality Report

Example output:
```markdown
# Golden Set Quality Analysis

## Overall Scores
- Completeness: 65% (20/31 real bugs captured)
- Clarity Average: 3.2/5
- Specificity Average: 2.8/5
- False Positive Rate: 12% (4/32 not real bugs)

## Issues Found
### Vague Comments (need improvement)
1. PR #6: "Django querysets do not support negative slicing"
   - Missing: File path, line number, specific function
   - Found in: 2 different locations
   - Recommendation: Split into 2 specific comments

### False Positives (not actually bugs)
1. PR #10: "Breaking changes in error response format"
   - Validation: Not a bug, intended API change
   - Recommendation: Remove from golden set

### Missing Bugs (should add to golden)
1. PR #7: Missing check for None return value (line 245)
   - Severity: High
   - Found by: Droid (valid)
   - Recommendation: Add to golden set
```

### 3. Droid Performance Analysis

Example output:
```markdown
# Droid True Performance (Validated)

## Validated Results
- True Positives: 12 (droid bugs confirmed as real)
- False Positives: 6 (droid bugs not actually bugs)
- True Recall: 38.7% (12/31 real bugs caught)
- True Precision: 66.7% (12/18 droid comments are real)

## Comparison to String-Matching Evaluation
- String-match Precision: 38.9% → True Precision: 66.7% (+27.8%)
- String-match Recall: 21.9% → True Recall: 38.7% (+16.8%)

Conclusion: Droid is actually performing MUCH better than metrics suggest!
The low string-match scores are due to incomplete/vague golden set.
```

---

## Implementation Timeline

### Week 1: Core Infrastructure
- Day 1-2: Setup validation script structure
- Day 3-4: Implement code inspection module (PR checkout, diff parsing)
- Day 5: Implement code context builder

### Week 2: Validation Logic
- Day 1-2: Build droid comment validator with LLM prompts
- Day 3-4: Build golden comment auditor
- Day 5: Implement completeness checker

### Week 3: Reports and Testing
- Day 1-2: Build report generators
- Day 3: Test on PRs #6-8
- Day 4: Refine prompts and validation logic
- Day 5: Full validation run on all PRs

---

## Success Criteria

✅ **Primary Goals:**
1. Validate every droid comment (real bug vs false positive)
2. Audit every golden comment (correct, specific, clear)
3. Identify bugs missed by both droid and golden
4. Generate actionable recommendations for improving:
   - Golden set quality
   - Droid performance evaluation
   - Evaluation methodology

✅ **Deliverables:**
1. Ground truth validation reports for all PRs
2. Corrected precision/recall metrics based on actual bugs
3. List of golden comments to add/edit/remove
4. Analysis of droid's actual strengths and weaknesses

---

## Notes and Considerations

### API Costs
- Using Claude Sonnet 4 for validation
- ~20 comments/PR × 10 PRs = 200 validations
- ~32 golden comments = 32 audits
- Estimate: ~232 API calls, ~500-1000 tokens each
- Cost estimate: $5-10 total

### Git Operations
- Will checkout different PRs in droid-sentry
- Recommend creating a separate worktree to avoid conflicts
- Could use: `git worktree add ../droid-sentry-validation master`

### Validation Confidence
- LLM validation won't be 100% perfect
- Include confidence scores
- For low-confidence cases, may need manual review
- Could implement human-in-the-loop for edge cases

---

Ready to implement when approved!
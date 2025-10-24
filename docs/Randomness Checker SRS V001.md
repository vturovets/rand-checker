# **Software Requirements Specification (SRS)**

## **Project: Randomness Checker CLI Application**

---

## **1. Business Value**

### **Purpose**

This application provides a quick, scientifically grounded way to evaluate whether a given sequence of data (numbers, characters, or strings) is random. It supports decision-making in scenarios where detecting randomness has operational, statistical, or cryptographic importance.

### **Business Benefits**

- **Automated Randomness Validation** — removes manual evaluation and statistical testing complexity.

- **Portable CLI Tool** — lightweight, runs on any Windows machine without installation overhead.

- **Configurable Testing** — enables experts to select which randomness tests to run.

- **Consistent & Reproducible Results** — outputs include confidence levels and detailed markdown logs for traceability.

- **Supports Mixed Data Types** — works for numeric, textual, and alphanumeric sequences.

---

## **2. Roles and Responsibilities**

| Role                                       | Responsibilities                                                                                                           |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **User (Analyst / Engineer / Researcher)** | Provides input file, configures test options, runs the tool, and reviews outputs.                                          |
| **System (CLI Application)**               | Reads configuration and input file, runs statistical tests, computes confidence, and generates summary + detailed results. |
| **Developer / Maintainer**                 | Implements, maintains, and updates the test suite and configuration system.                                                |

---

## **3. High-Level Process Flow**

```text
Start
│
├──► 1. Launch CLI application
│
├──► 2. Load configuration file (test selection, weighting, output preferences)
│
├──► 3. Load input data file (list of numbers, chars, or strings)
│
├──► 4. Identify data type(s) and pre-process accordingly
│
├──► 5. Run configured randomness tests:
│         - Frequency (Monobit) Test
│         - Runs Test
│         - Serial Test
│         - Entropy Test
│         - Chi-Square Test
│         - Kolmogorov–Smirnov Test
│         - Autocorrelation Test
│         - Shannon Entropy Test
│
├──► 6. Compute weighted overall confidence level
│
├──► 7. Generate:
│         - Summary report (RANDOM/NON-RANDOM + confidence)
│         - Detailed markdown report (all test results, weights, and rationale)
│
└──► 8. Log results and exit
End
```

---

## **4. User Stories and Acceptance Criteria**

### **User Story 1: Input and Configuration**

**As a** user  
**I want** to provide an input text file and configuration file  
**So that** I can define what tests are executed and how they are weighted.

**Acceptance Criteria:**

- CLI accepts `--input` and `--config` parameters.

- Configuration file supports enabling/disabling individual tests.

- Configuration file supports assigning weights for test reliability.

- Validation errors are displayed clearly if configuration is malformed.

---

### **User Story 2: Randomness Testing**

**As a** user  
**I want** the tool to assess whether my sequence is random  
**So that** I can understand its randomness characteristics.

**Acceptance Criteria:**

- Application performs at least 5 configurable statistical tests.

- Each test returns a p-value or equivalent confidence metric.

- Tool combines results into a final binary output (“RANDOM” or “NON-RANDOM”) with a confidence percentage.

- If mixed data types are detected, justification for selected tests is included in the detailed report.

---

### **User Story 3: Reporting**

**As a** user  
**I want** to see both a human-readable summary and a detailed markdown report  
**So that** I can interpret the results at different levels.

**Acceptance Criteria:**

- Summary output (console):  
  `Result: RANDOM | Confidence: 92%`

- Detailed markdown report includes:
  
  - Input filename
  
  - Number of entries
  
  - Tests executed and individual results
  
  - Weighted confidence
  
  - Overall interpretation
  
  - Timestamp and run duration

---

### **User Story 4: Logging**

**As a** user  
**I want** the tool to automatically log each run  
**So that** I can track all historical assessments.

**Acceptance Criteria:**

- Log file automatically created in a “/logs” folder.

- Log includes timestamp, file name, result, and confidence level.

- Log retention policy configurable (default: keep last 100 entries).

---

## **5. High-Level Solution Requirements**

### **Functional Requirements**

| ID    | Requirement                                                                      | Type       |
| ----- | -------------------------------------------------------------------------------- | ---------- |
| FR-01 | Application shall read input from a plain text file with one entry per line.     | Functional |
| FR-02 | Application shall support numbers, characters, or strings (mixed allowed).       | Functional |
| FR-03 | Application shall allow test selection via configuration file.                   | Functional |
| FR-04 | Application shall perform statistical randomness tests.                          | Functional |
| FR-05 | Application shall compute and display overall confidence.                        | Functional |
| FR-06 | Application shall produce both summary (console) and detailed (markdown) output. | Functional |
| FR-07 | Application shall automatically log all runs and outputs.                        | Functional |

### **Non-Functional Requirements**

| ID     | Requirement                                                           | Type          |
| ------ | --------------------------------------------------------------------- | ------------- |
| NFR-01 | Application shall run in Windows Command Prompt without dependencies. | Portability   |
| NFR-02 | Application shall be developed in Python                              | --            |
| NFR-03 | Average runtime under 10 seconds for ≤10,000 entries.                 | Performance   |
| NFR-04 | Configuration and output formats shall use UTF-8.                     | Compatibility |
| NFR-05 | Detailed report shall be in valid Markdown format.                    | Usability     |

---

## **6. Configuration File (Example)**

```ini
[tests]
monobit = true
runs = true
entropy = true
chi_square = false
serial = true

[weights]
monobit = 0.2
runs = 0.2
entropy = 0.2
serial = 0.2
ks = 0.2

[output]
format = markdown
log_results = true
```

---

## **7. Example Outputs**

### **Console Summary**

```
> randomcheck --input example.txt --config config.ini
Analyzing...
Result: NON-RANDOM
Confidence: 78%
```

### **Markdown Detailed Report**

```markdown
# Randomness Report
**File:** example.txt  
**Entries:** 9  
**Date:** 2025-10-24  

| Test | Result | Confidence |
|------|---------|-------------|
| Frequency (Monobit) | FAIL | 60% |
| Runs Test | PASS | 85% |
| Entropy | FAIL | 70% |
| Serial Test | FAIL | 65% |

**Overall Result:** NON-RANDOM  
**Weighted Confidence:** 78%  
```

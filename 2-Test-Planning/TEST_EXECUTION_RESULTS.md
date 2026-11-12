
# Test Execution Results – Hostel Management System

**Project:** Hostel Management System  
**Tester:** Manasi Jadhav  
**Test scope:** FR-01, SEC-01, SEC-02, SEC-03 and SEC-04

## 1. Test Execution Summary

| Test Area | Test Description | Actual Result | Status |
|---|---|---|---|
| FR-01 | Authentication and login workflow | 3 automated tests passed | PASS |
| SEC-01 | Protected endpoint access | Unauthenticated access was rejected | PASS |
| SEC-01 | Unauthorized access audit | Unauthorized access was logged and tested | PASS |
| SEC-02 | Role-based access control | 2 automated tests passed | PASS |
| SEC-03 | Password hashing | Password hashing test passed | PASS |
| SEC-04 | HTTPS enforcement | HTTP request redirect test passed | PASS |

## 2. Test Evidence

The following screenshots are stored in `5-Project-and-Jira-Screenshots/screenshots/`.

| Evidence | Screenshot |
|---|---|
| Authentication tests | `FR01_Authentication_Tests.png` |
| Protected endpoint test | `SEC01_Protected_Endpoint_Test.png` |
| Unauthorized access test | `SEC01_Unauthorized_Access_Test.png` |
| Role-based access tests | `SEC02_Role_Based_Access_Tests.png` |
| Password hashing test | `SEC03_Password_Hashing_Test.png` |
| HTTPS implementation PR | `SEC04_PR27_Merged.png` |

## 3. Additional Test Execution

The complete automated test suite was executed.

**Result:** 60 tests passed, 0 failures.

Evidence: `Full_Test_Suite_60_Passed.png`

## 4. HTTPS Testing Limitation

The HTTPS enforcement test verifies that HTTP requests are redirected when HTTPS enforcement is enabled. It does not independently verify a live production TLS certificate or deployed HTTPS configuration.

## 5. Conclusion

The listed authentication, authorization, password-storage and HTTPS-related automated tests passed in the recorded test runs. The evidence screenshots are maintained in the project repository.

This execution record documents the tests actually performed and does not claim that untested security requirements have passed.

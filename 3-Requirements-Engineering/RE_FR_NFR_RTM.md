# Requirements Engineering

This folder consolidates the requirements baseline and its traceability for the Hostel Management System.

## Functional Requirements

| ID | Requirement area |
|---|---|
| FR-01 | Authenticate user before protected functions |
| FR-02 | Create/update student records |
| FR-03 | Search student by identifier |
| FR-04 | Create/update room records and capacity |
| FR-05 | Allocate eligible student to room with available capacity |
| FR-06 | Reject full-room or duplicate-student allocation |
| FR-07 | Modify/deallocate active allocation |
| FR-08 | Display room occupancy and available capacity |
| FR-09 | Student can view own allocation only |

## Non-Functional Requirements

| ID | Attribute | Requirement |
|---|---|---|
| NFR-01 | Performance | Up to 50 concurrent authenticated users; at least 95% of normal read requests within 2 seconds, excluding external network latency |
| NFR-02 | Availability | At least 99% monthly availability during scheduled service hours, excluding announced planned maintenance |
| NFR-03 | Data integrity | Allocation and associated capacity update are atomic |
| NFR-04 | Usability | Trained administrator completes valid allocation in no more than five primary data-entry steps after login |
| NFR-05 | Maintainability | Separate presentation, application-service, and data-access responsibilities |

## Security Requirements

| ID | Requirement |
|---|---|
| SEC-01 | Authentication before protected API/application functions |
| SEC-02 | Role-based authorization |
| SEC-03 | Strong salted password hashing; no plaintext passwords |
| SEC-04 | HTTPS/TLS in deployed environments |
| SEC-05 | Input validation and parameterized/ORM database operations |
| SEC-06 | Security-relevant event logging |

## Requirements Traceability Matrix

| Requirement | Test / Verification |
|---|---|
| FR-01 | TP-01, TP-14 |
| FR-02 | TP-02 |
| FR-03 | TP-03 |
| FR-04 | TP-04 |
| FR-05 | TP-05 |
| FR-06 | TP-06, TP-07 |
| FR-07 | TP-08 |
| FR-08 | TP-09 |
| FR-09 | TP-10 |
| NFR-01 | TP-11 |
| NFR-03 | TP-12 |
| NFR-04 | TP-13 |
| NFR-05 | Architecture inspection |
| SEC-01 | TP-10, TP-14 |
| SEC-02 | TP-10, TP-14 |
| SEC-03 | TP-14 |
| SEC-04 | TP-14 |
| SEC-05 | TP-14 |
| SEC-06 | TP-14 |

> NFR-02 is specified in the SRS for operational verification and is not mapped to a numbered TP case in the supplied RTM.

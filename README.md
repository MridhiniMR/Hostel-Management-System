# 🏠 Hostel Management System

A web-based **Hostel Management System** mini-project developed for the Software Engineering course.

## 🌟 Highlights

- Student record management
- Hostel room management
- Room allocation and deallocation
- Room occupancy information
- Authentication and role-based authorization
- Requirements, testing, traceability, architecture, deployment, and demonstration documentation
- Security requirements covering authentication, authorization, password protection, HTTPS/TLS, input validation, and security logging

## 📖 Project Overview

The Hostel Management System manages student details, hostel room details, room allocation/deallocation, and occupancy information. The defined users are the **Hostel Administrator/Warden** and **Student**. Students can view their own allocation information after authentication.

The current requirements baseline specifies a technology-neutral web application with a client interface, application/API layer, application-service layer, data-access layer, and relational database.

## 👥 Team

> Replace this section with the actual team members and university IDs.

| Member | USN | Role / Contribution |
|---|---|---|
| Member 1 | TODO | TODO |
| Member 2 | TODO | TODO |
| Member 3 | TODO | TODO |
| Member 4 | TODO | TODO |

## 🧩 Main Functional Requirements

| ID | Requirement area |
|---|---|
| FR-01 | Authentication |
| FR-02 | Student record management |
| FR-03 | Student search |
| FR-04 | Room management |
| FR-05 | Valid room allocation |
| FR-06 | Invalid/conflicting allocation prevention |
| FR-07 | Modify/deallocate allocation |
| FR-08 | Occupancy information |
| FR-09 | Student self-view |

## 🔐 Security Requirements

- **SEC-01:** Authentication before protected functions/API endpoints
- **SEC-02:** Role-based authorization
- **SEC-03:** Salted, computationally strong password hashing; no plaintext passwords
- **SEC-04:** HTTPS/TLS in deployed environments
- **SEC-05:** Input validation and parameterized/ORM database protection
- **SEC-06:** Security-relevant event logging

## 🏗️ Architecture

The documented architecture uses a **layered three-tier structure**:

1. Presentation/API layer
2. Application/Service layer
3. Data-access layer backed by a relational database

The architecture also documents component responsibilities, data model, security boundaries, API design, error handling, sequence diagrams, and deployment view.

## 🧪 Testing

The test baseline contains functional, non-functional, integration, system, security, performance, and usability testing. The detailed test cases are currently documented as **Not Executed** until actual execution evidence is added.

The traceability matrix maps the SRS requirements to test cases such as TP-01 through TP-14.

## 📁 Repository Structure

```text
Hostel-Management-System/
│
├── README.md
├── 1-SRS-and-Work-Breakdown/
├── 2-Test-Planning/
├── 3-Requirements-Engineering/
├── 4-Architecture-and-Design/
├── 5-Project-and-Jira-Screenshots/
├── 6-GitHub-Copilot/
├── 7-Software-Testing-Tools/
├── 8-Deployment-and-Environment/
└── 9-Demo/
```

## 🚀 Installation / Usage

The requirements and architecture documents intentionally keep the implementation framework technology-neutral. Therefore, add the **actual framework, database, operating-system requirements, environment variables, installation commands, and run commands** used by the team in `8-Deployment-and-Environment/` before final submission.

## 📚 Documentation

| Deliverable | Location |
|---|---|
| SRS | `1-SRS-and-Work-Breakdown/SRS.docx` |
| Work Breakdown Structure | `1-SRS-and-Work-Breakdown/WORK_BREAKDOWN.md` |
| Test Plan | `2-Test-Planning/Test_Plan.docx` |
| Requirements Engineering / RTM | `3-Requirements-Engineering/` |
| Architecture & Design | `4-Architecture-and-Design/Architecture_and_Design.docx` |
| Project/Jira evidence | `5-Project-and-Jira-Screenshots/` |
| GitHub Copilot evidence | `6-GitHub-Copilot/` |
| Testing tools / bug-fix evidence | `7-Software-Testing-Tools/` |
| Deployment / environment | `8-Deployment-and-Environment/` |
| Demo | `9-Demo/` |

## 📌 Scope Exclusions

The current SRS explicitly excludes fee collection/payment, mess management, visitor management, attendance, and complaint management.

## 📜 Documentation Basis

The project documents are structured with reference to ISO/IEC/IEEE 29148:2018 for requirements, ISO/IEC/IEEE 29119-3:2021 for test documentation, and ISO/IEC/IEEE 42010:2022 for architecture description.

## 🤝 Feedback / Contribution

For the course submission, use the GitHub repository Issues/Projects as applicable for team coordination and record the team's actual development and testing evidence.


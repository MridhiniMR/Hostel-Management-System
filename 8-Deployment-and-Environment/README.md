# Deployment / Infrastructure / Environment Setup

The architecture document specifies a minimum deployment consisting of:

- User browser
- HTTPS application server hosting the presentation/API and application-service layers
- Relational database server
- Protected application logging storage

The database is not directly exposed to client browsers.

## Team-Specific Setup

The architecture and SRS are intentionally technology-neutral, so the actual implementation details must be filled in from the team's real project.

### Environment

- Operating system: TODO
- Language/runtime: TODO
- Framework: TODO
- Database: TODO
- Browser: TODO
- Server/hosting: TODO

### Installation

```text
TODO: actual clone/install commands
```

### Configuration

```text
TODO: actual environment-variable/configuration instructions
```

### Database Setup

```text
TODO: actual schema/migration/seed commands
```

### Run the Application

```text
TODO: actual start command
```

### Verification

- [ ] Application opens successfully
- [ ] Database connection works
- [ ] Login works
- [ ] Protected endpoint access is enforced
- [ ] Room allocation works
- [ ] Occupancy is displayed
- [ ] Security logging works
- [ ] HTTPS/TLS verified in deployed environment

### Important

Do not add commands, versions, URLs, credentials, or infrastructure claims unless they correspond to the team's actual implementation.

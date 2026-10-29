\# NFR-01: Performance Test Results



\## Objective



Evaluate whether the Hostel Management System can handle 50 concurrently authenticated users while at least 95% of normal read requests complete within 2 seconds.



\## Test Configuration



\- \*\*Test date:\*\* 29 October 2026

\- \*\*Target concurrent users:\*\* 50

\- \*\*Authenticated users:\*\* 50

\- \*\*Read requests per user:\*\* 10

\- \*\*Total read requests:\*\* 500

\- \*\*Test tool:\*\* Python, asyncio, and HTTPX

\- \*\*Environment:\*\* Local development server

\- \*\*Measured endpoints:\*\* `/api/v1/rooms`, `/api/v1/students`, and `/api/v1/allocations`



\## Results



| Metric | Observed result |

|---|---:|

| Successful read requests | 500 |

| Failed requests | 0 |

| Test duration | 5.473 seconds |

| Throughput | 91.35 requests/second |

| Average latency | 476.59 ms |

| P95 latency | 1,544.93 ms |

| Requests under 2 seconds | 97.6% |



\## Evaluation



The test completed 500 successful read requests using 50 authenticated users. In this run, 97.6% of read requests completed in under 2 seconds, exceeding the required 95% threshold.



The benchmark script reported `target\_met: true`.



\## Limitations



These results are from a local development environment and are not a production-capacity guarantee. Performance depends on the host machine, server configuration, database, and dataset.



The test database and the amount of application data should be verified before treating this as representative of real-world usage. The benchmark should be repeated with realistic student, room, and allocation records. The results also reflect the current local server configuration, not necessarily a production deployment.



\## Conclusion



The NFR-01 response-time target was met in this local test run. Further testing with representative data and a production-like environment is recommended before claiming the requirement is fully validated.




# Day 2 Notes

## Summary

Today focused on selecting and justifying the first real-world domain for DataForge AI.

The selected domain is Job Market Intelligence.

This domain was chosen because it is practical, understandable, and valuable for multiple user groups, including job seekers, recruiters, freelancers, students, and career coaches. It also provides strong opportunities to demonstrate data engineering, data warehousing, analytics, machine learning, AI, FastAPI, Power BI, Ollama, and MCP.

## Decisions Made

- DataForge AI will begin with the Job Market Intelligence domain.
- The project will analyze job postings, skills, companies, locations, salaries, experience levels, and hiring trends.
- Synthetic or sample CSV data will be used first.
- APIs and public datasets can be added after the initial schema and pipeline are stable.
- Web scraping will not be implemented yet.
- Any future scraping must respect website terms of service, `robots.txt`, rate limits, and ethical data-use practices.

## Next Step

The next step is to design the OLTP and warehouse schemas for job market data.

The schema design should define core entities such as jobs, companies, locations, skills, job-skill relationships, salary ranges, and date dimensions for analytics.

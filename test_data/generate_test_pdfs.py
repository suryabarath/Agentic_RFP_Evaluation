"""
Test PDF Generator

Creates synthetic supplier proposal PDFs for testing the RFP evaluation pipeline.
Uses PyMuPDF (fitz) to create simple PDF documents with proposal text.
"""

import fitz  # PyMuPDF
import os

# Sample proposals with varying quality levels
PROPOSALS = {
    "TechCorp_Solutions": {
        "quality": "high",
        "content": """
PROPOSAL FOR RFP-2024-001
Enterprise Software Solution

Submitted by: TechCorp Solutions
Date: January 15, 2024

═══════════════════════════════════════════════════════════════════════════════
EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════════════════════

TechCorp Solutions is pleased to submit this comprehensive proposal for your
enterprise software requirements. With 15 years of industry experience and a
proven track record of successful implementations, we are confident in our
ability to deliver exceptional value.

═══════════════════════════════════════════════════════════════════════════════
TECHNICAL APPROACH
═══════════════════════════════════════════════════════════════════════════════

Our solution leverages modern cloud-native architecture:

• Microservices Architecture: Scalable, independently deployable services
• Kubernetes Orchestration: Container management with auto-scaling
• API-First Design: RESTful APIs with GraphQL support
• Event-Driven Processing: Real-time data synchronization
• Modern Tech Stack: React, Node.js, PostgreSQL, Redis

Technology Highlights:
- 99.99% uptime SLA guarantee
- Horizontal scaling to 10M+ concurrent users
- Sub-100ms response times for 95th percentile
- Multi-region deployment capability

═══════════════════════════════════════════════════════════════════════════════
TEAM EXPERIENCE
═══════════════════════════════════════════════════════════════════════════════

Our delivery team brings extensive expertise:

• Project Manager: 12 years enterprise software experience
• Lead Architect: Former Google engineer, 10+ years
• Development Team: 8 senior developers, avg 7 years experience
• QA Lead: ISTQB certified, 8 years testing experience
• DevOps Engineer: AWS/GCP certified, 6 years

Past Project Success:
- Global Bank Corp: $50M platform, delivered on time
- Healthcare Systems Inc: HIPAA-compliant solution
- Retail Giant Ltd: 500% performance improvement

═══════════════════════════════════════════════════════════════════════════════
IMPLEMENTATION TIMELINE
═══════════════════════════════════════════════════════════════════════════════

Phase 1 - Discovery & Planning (Weeks 1-4):
  • Requirements deep-dive workshops
  • Technical architecture design
  • Project plan finalization

Phase 2 - Core Development (Weeks 5-16):
  • Sprint-based agile delivery
  • Bi-weekly demos to stakeholders
  • Continuous integration/deployment

Phase 3 - Testing & QA (Weeks 17-20):
  • Comprehensive test automation
  • Performance and load testing
  • Security penetration testing
  • User acceptance testing

Phase 4 - Deployment & Training (Weeks 21-24):
  • Staged rollout strategy
  • Staff training program
  • Documentation delivery
  • Go-live support

═══════════════════════════════════════════════════════════════════════════════
PRICING
═══════════════════════════════════════════════════════════════════════════════

Investment Summary:

Implementation Services:
  • Discovery & Planning:      $75,000
  • Core Development:         $280,000
  • Testing & QA:              $65,000
  • Deployment & Training:     $30,000
  ─────────────────────────────────────
  Total Implementation:       $450,000

Ongoing Services (Annual):
  • Software Licensing:        $36,000
  • Maintenance & Support:     $50,000
  • Cloud Infrastructure:      $24,000
  ─────────────────────────────────────
  Total Annual:              $110,000

Value Proposition:
- 30% below market rate for comparable solutions
- ROI typically achieved within 18 months
- Total cost of ownership optimized

═══════════════════════════════════════════════════════════════════════════════
SECURITY & COMPLIANCE
═══════════════════════════════════════════════════════════════════════════════

Our security framework is comprehensive:

Certifications:
✓ SOC 2 Type II Certified (Annual audit)
✓ ISO 27001 Compliant
✓ GDPR Ready
✓ PCI-DSS Level 1

Security Measures:
• End-to-end encryption (AES-256)
• Multi-factor authentication
• Role-based access control
• Regular penetration testing (quarterly)
• 24/7 security monitoring (SOC)
• Automated vulnerability scanning
• Incident response plan (< 1 hour)

Data Protection:
• Encrypted at rest and in transit
• Automated backups (hourly)
• Disaster recovery: RPO 1hr, RTO 4hr
• Data residency compliance

═══════════════════════════════════════════════════════════════════════════════
SUPPORT & MAINTENANCE
═══════════════════════════════════════════════════════════════════════════════

Support Tiers:

Premium Support (Included):
• 24/7/365 phone and email support
• Dedicated account manager
• 4-hour SLA for critical issues
• 8-hour SLA for high priority
• Unlimited support tickets
• Monthly health check reviews

Additional Services:
• On-site support available
• Custom development services
• Training refresher sessions
• Quarterly business reviews

═══════════════════════════════════════════════════════════════════════════════
CONCLUSION
═══════════════════════════════════════════════════════════════════════════════

TechCorp Solutions offers the ideal combination of technical excellence,
proven experience, and competitive pricing. We look forward to partnering
with you on this important initiative.

Contact: proposals@techcorp.example.com
Phone: +1 (555) 123-4567
"""
    },

    "CloudFirst_Inc": {
        "quality": "medium",
        "content": """
PROPOSAL RESPONSE
Cloud-Based Solution Offering

Company: CloudFirst Inc.
Submission Date: January 2024

───────────────────────────────────────────────────────────────────────────────
ABOUT US
───────────────────────────────────────────────────────────────────────────────

CloudFirst Inc. specializes in cloud-native solutions built on AWS. We have
5 years of experience delivering cloud migration and development projects.

───────────────────────────────────────────────────────────────────────────────
TECHNICAL SOLUTION
───────────────────────────────────────────────────────────────────────────────

Our proposed solution:

• AWS-based serverless architecture
• Lambda functions for business logic
• DynamoDB for data storage
• API Gateway for REST endpoints
• S3 for file storage
• CloudFront for content delivery

Key Features:
- Auto-scaling based on demand
- Pay-per-use pricing model
- Managed infrastructure

Technology Used:
- Python and Node.js
- React frontend
- AWS services

───────────────────────────────────────────────────────────────────────────────
TEAM
───────────────────────────────────────────────────────────────────────────────

Project Team:
• Project Manager - 5 years experience
• 4 Developers - AWS certified
• 1 QA Engineer
• 1 DevOps specialist

References available upon request.

───────────────────────────────────────────────────────────────────────────────
TIMELINE
───────────────────────────────────────────────────────────────────────────────

Discovery Phase: 2 weeks
Development: 4 months
Testing: 1 month
Deployment: 2 weeks

Total Duration: Approximately 6 months

───────────────────────────────────────────────────────────────────────────────
PRICING
───────────────────────────────────────────────────────────────────────────────

Project Costs:
• Implementation: $380,000
• Monthly Cloud Costs: ~$5,000
• Annual Support: $40,000

Payment Terms:
- 30% upfront
- 40% at midpoint
- 30% at completion

───────────────────────────────────────────────────────────────────────────────
SECURITY
───────────────────────────────────────────────────────────────────────────────

Security Features:
• AWS Well-Architected framework
• IAM role-based access
• VPC network isolation
• SSL/TLS encryption
• CloudTrail logging

Compliance:
- AWS compliance programs apply
- Working toward SOC 2

───────────────────────────────────────────────────────────────────────────────
SUPPORT
───────────────────────────────────────────────────────────────────────────────

Support Options:
• Email support during business hours
• Monthly check-in calls
• Documentation and knowledge base
• Slack channel for communication

Response Times:
- Critical: 24 hours
- Normal: 48 hours

───────────────────────────────────────────────────────────────────────────────

Thank you for considering CloudFirst Inc.

Contact: sales@cloudfirst.example.com
"""
    },

    "BudgetTech_Ltd": {
        "quality": "low",
        "content": """
PROPOSAL
From BudgetTech Ltd

───────────────────────────────────────────────────────

COMPANY INFO

BudgetTech Ltd. is a new software company. We started
last year and are looking for projects.

───────────────────────────────────────────────────────

WHAT WE OFFER

We can build a software solution for you. We use:
- PHP and MySQL
- Basic hosting
- Standard features

Our team:
- 2 developers
- 1 project manager (part-time)

───────────────────────────────────────────────────────

TIMELINE

We estimate 3-4 months for completion.
Exact timeline depends on requirements.

───────────────────────────────────────────────────────

COST

Total Price: $200,000

This includes everything.

───────────────────────────────────────────────────────

SECURITY

We follow basic security practices.
- Password protection
- Backups

───────────────────────────────────────────────────────

SUPPORT

Email support available.
Response within 3-5 business days.

───────────────────────────────────────────────────────

Contact us at: info@budgettech.example.com
"""
    },

    "GlobalSystems_Corp": {
        "quality": "high",
        "content": """
═══════════════════════════════════════════════════════════════════════════════
                    GLOBAL SYSTEMS CORPORATION
                    Enterprise Solution Proposal
                    RFP Response - January 2024
═══════════════════════════════════════════════════════════════════════════════

COMPANY OVERVIEW
─────────────────────────────────────────────────────────────────────────────

Global Systems Corporation is a Fortune 500 technology partner with over
20 years of experience delivering mission-critical enterprise solutions.
We serve 200+ clients across finance, healthcare, and government sectors.

Awards & Recognition:
• Gartner Magic Quadrant Leader (5 consecutive years)
• Best Enterprise Software Provider 2023
• ISO 27001, SOC 2 Type II, HIPAA Certified

TECHNICAL EXCELLENCE
─────────────────────────────────────────────────────────────────────────────

Architecture Overview:

Our Enterprise Platform leverages cutting-edge technology:

┌─────────────────────────────────────────────────────────────────────┐
│  Presentation Layer                                                   │
│  • React/Angular SPA • Mobile Apps • Progressive Web App              │
├─────────────────────────────────────────────────────────────────────┤
│  API Gateway Layer                                                    │
│  • Kong/AWS API Gateway • Rate Limiting • OAuth 2.0                   │
├─────────────────────────────────────────────────────────────────────┤
│  Service Layer (Microservices)                                        │
│  • Java Spring Boot • .NET Core • Python FastAPI                      │
├─────────────────────────────────────────────────────────────────────┤
│  Data Layer                                                           │
│  • PostgreSQL • MongoDB • Redis • Elasticsearch                       │
├─────────────────────────────────────────────────────────────────────┤
│  Infrastructure                                                       │
│  • Kubernetes • Terraform • Multi-Cloud (AWS/Azure/GCP)               │
└─────────────────────────────────────────────────────────────────────┘

Performance Guarantees:
• 99.999% uptime SLA
• < 50ms API response time (p99)
• Horizontal scaling to 100M+ users
• Zero-downtime deployments

TEAM CREDENTIALS
─────────────────────────────────────────────────────────────────────────────

Dedicated Team for This Project:

Executive Sponsor: Sarah Chen
  - 25 years enterprise software leadership
  - Former CTO at major financial institution

Project Director: Michael Roberts
  - PMP, Scrum Master certified
  - 15 years delivery experience
  - Managed $100M+ programs

Solution Architect: Dr. James Wilson
  - PhD Computer Science, MIT
  - AWS/Azure/GCP certified architect
  - 18 years system design

Development Lead: Priya Sharma
  - 12 years full-stack development
  - Led teams of 30+ engineers
  - Open source contributor

Team Composition:
• 12 Senior Developers
• 4 QA Engineers
• 2 DevOps/SRE
• 1 Security Specialist
• 1 UX Designer

IMPLEMENTATION PLAN
─────────────────────────────────────────────────────────────────────────────

Week 1-2: Project Initiation
  • Kick-off meeting and governance setup
  • Detailed requirements workshops
  • Risk assessment and mitigation planning

Week 3-6: Architecture & Design
  • Solution architecture finalization
  • Security architecture review
  • Development environment setup
  • CI/CD pipeline configuration

Week 7-18: Iterative Development
  • 6 two-week sprints
  • Feature delivery each sprint
  • Continuous integration
  • Regular stakeholder demos

Week 19-22: System Integration & Testing
  • Integration testing
  • Performance testing
  • Security penetration testing
  • User acceptance testing

Week 23-26: Deployment & Transition
  • Staged production rollout
  • Data migration
  • User training
  • Hypercare support

INVESTMENT
─────────────────────────────────────────────────────────────────────────────

Fixed Price Implementation: $520,000

Breakdown:
  • Discovery & Planning:          $60,000
  • Architecture & Design:         $80,000
  • Development (12 sprints):     $300,000
  • Testing & QA:                  $50,000
  • Deployment & Training:         $30,000

Annual Maintenance & Support:      $85,000
  • 24/7 support coverage
  • Quarterly updates
  • Security patches
  • Performance optimization

Cloud Infrastructure (Est.):       $3,000-5,000/month
  • Scales with usage
  • Reserved instance discounts available

Value Guarantee:
  - Fixed price, no overruns
  - Performance SLA guarantees
  - 12-month warranty included

SECURITY & COMPLIANCE
─────────────────────────────────────────────────────────────────────────────

Certifications:
✓ SOC 2 Type II (Annual)
✓ ISO 27001:2022
✓ ISO 9001:2015
✓ HIPAA Compliant
✓ PCI DSS Level 1
✓ FedRAMP Authorized

Security Framework:
• Zero Trust Architecture
• End-to-end encryption (TLS 1.3, AES-256)
• Hardware Security Modules (HSM)
• Multi-factor authentication
• Privileged Access Management
• SIEM integration
• 24/7 Security Operations Center

Compliance Support:
• Dedicated compliance officer
• Audit support and documentation
• Regular vulnerability assessments
• Annual penetration testing by third party

SUPPORT MODEL
─────────────────────────────────────────────────────────────────────────────

Premium Enterprise Support:

• 24/7/365 Global Support
  - Phone, email, chat channels
  - Multi-language support (EN, ES, FR, DE, JP)

• Dedicated Team
  - Named Technical Account Manager
  - Escalation contacts provided

• Response SLAs
  - Critical (P1): 15-minute response, 4-hour resolution
  - High (P2): 1-hour response, 8-hour resolution
  - Medium (P3): 4-hour response, 24-hour resolution
  - Low (P4): 1 business day response

• Proactive Services
  - Quarterly business reviews
  - Annual architecture assessments
  - Roadmap planning sessions
  - Executive briefings

CONCLUSION
─────────────────────────────────────────────────────────────────────────────

Global Systems Corporation offers unmatched expertise, proven methodology,
and enterprise-grade capabilities. Our track record of successful deliveries
and our commitment to excellence make us the ideal partner for your
digital transformation journey.

We look forward to discussing this proposal further.

Contact:
Enterprise Sales Team
proposals@globalsystems.example.com
+1 (800) 555-0100

═══════════════════════════════════════════════════════════════════════════════
"""
    }
}


def create_pdf(filename: str, content: str, output_dir: str) -> str:
    """
    Create a PDF file with the given content.

    Args:
        filename: Name of the PDF file (without extension)
        content: Text content to include in the PDF
        output_dir: Directory to save the PDF

    Returns:
        str: Path to the created PDF
    """
    # Create a new PDF document
    doc = fitz.open()

    # Split content into pages (roughly 60 lines per page)
    lines = content.strip().split('\n')
    lines_per_page = 55

    # Page settings
    page_width = 612  # Letter size
    page_height = 792
    margin = 50
    line_height = 12

    current_line = 0
    while current_line < len(lines):
        # Create a new page
        page = doc.new_page(width=page_width, height=page_height)

        # Starting position
        y_position = margin

        # Add lines to this page
        for i in range(lines_per_page):
            if current_line >= len(lines):
                break

            line = lines[current_line]

            # Insert text
            page.insert_text(
                (margin, y_position),
                line,
                fontname="helv",
                fontsize=10,
                color=(0, 0, 0)
            )

            y_position += line_height
            current_line += 1

    # Save the PDF
    output_path = os.path.join(output_dir, f"{filename}.pdf")
    doc.save(output_path)
    doc.close()

    return output_path


def generate_all_test_pdfs():
    """Generate all test PDFs."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("Generating test proposal PDFs...")
    print()

    created_files = []

    for name, data in PROPOSALS.items():
        pdf_path = create_pdf(name, data["content"], script_dir)
        created_files.append(pdf_path)
        print(f"  ✓ Created: {name}.pdf ({data['quality']} quality)")

    print()
    print(f"Generated {len(created_files)} test PDFs in: {script_dir}")
    print()
    print("Files created:")
    for path in created_files:
        size = os.path.getsize(path)
        print(f"  - {os.path.basename(path)} ({size:,} bytes)")

    return created_files


if __name__ == "__main__":
    generate_all_test_pdfs()

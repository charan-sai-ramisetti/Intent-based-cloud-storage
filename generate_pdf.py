import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
    Preformatted,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Tri-Cloud Vault: Intent-Driven Multi-Cloud Storage Optimization")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Footer
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, text)
        self.drawString(54, 36, "CONFIDENTIAL - Tri-Cloud Vault Technical Architecture Specification")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1A365D")
    secondary_color = colors.HexColor("#2B6CB0")
    dark_text = colors.HexColor("#2D3748")
    code_bg = colors.HexColor("#F7FAFC")
    border_color = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=dark_text,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1A202C"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=dark_text,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    story = []

    # Title Block
    story.append(Paragraph("Tri-Cloud Vault: Technical Architecture Specification", title_style))
    story.append(Paragraph("Intent-Driven Multi-Cloud Storage Optimization & Compensating Rollback Engine", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=10))

    # 1. Executive Overview
    story.append(Paragraph("1. Executive Overview & Core Architectural Guarantee", h1_style))
    story.append(Paragraph(
        "<b>Tri-Cloud Vault</b> is an intent-driven multi-cloud storage optimization platform that transparently places, "
        "replicates, and manages data across <b>Amazon Web Services (AWS S3)</b>, <b>Microsoft Azure (Blob Storage)</b>, "
        "and <b>Google Cloud Platform (GCP Cloud Storage)</b>.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Fundamental Design Guarantee:</b>", body_style
    ))
    story.append(Paragraph(
        "• <b>Strict Semantic Separation:</b> The Large Language Model (LLM) acts strictly as a natural language compiler "
        "that extracts and validates structured constraints (<code>ParsedConstraints</code>) from user intent. "
        "The LLM <b>never</b> makes cloud placement decisions directly.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Deterministic Optimization:</b> Multi-cloud tier placement is determined exclusively by a mathematical "
        "Mixed-Integer Linear Programming (MILP) solver that rigorously minimizes cost or latency subject to SLA constraints.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Asynchronous Orchestration:</b> Multi-cloud direct presigned chunk uploads and atomic rollbacks are governed "
        "by a 17-state Celery/Redis Finite State Machine (FSM).",
        bullet_style
    ))

    # Architecture Diagram Table
    diag_text = (
        "+-------------------------+       Structured JSON       +--------------------------+\n"
        "|    User Natural Text    |  ========================>  |      MILP Optimizer      |\n"
        "|  \"Cold backup, budget   |      (ParsedConstraints)    |       (PuLP / CBC)       |\n"
        "|   under $5, 2 copies\"   |                             |                          |\n"
        "+-------------------------+                             +--------------------------+\n"
        "             |                                                        |\n"
        "       [LLM COMPILER]                                           [DETERMINISTIC]\n"
        "    Extracts Constraints                                      Solves Mathematical\n"
        "  (Never chooses clouds)                                      Optimization Model"
    )
    t_diag = Table([[Preformatted(diag_text, code_style)]], colWidths=[504])
    t_diag.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), code_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 8))

    # 2. Directory & Manifest
    story.append(Paragraph("2. Repository Architecture & File Manifest", h1_style))
    manifest_data = [
        [Paragraph("Module Path", table_header_style), Paragraph("Component", table_header_style), Paragraph("Responsibility", table_header_style)],
        [Paragraph("<code>backend/.../clouds/</code>", table_cell_bold), Paragraph("Cloud SDK Adapters", table_cell_style), Paragraph("AWS S3, Azure Blob, and GCP Cloud Storage clients, presigned URL generators.", table_cell_style)],
        [Paragraph("<code>backend/.../intent/</code>", table_cell_bold), Paragraph("Intent Compiler", table_cell_style), Paragraph("Pydantic schemas, Anthropic/OpenAI/Regex fallback parsers, Django ORM audit models.", table_cell_style)],
        [Paragraph("<code>backend/.../optimizer/</code>", table_cell_bold), Paragraph("MILP Solver", table_cell_style), Paragraph("PuLP optimization formulation, cost matrices, heuristic baseline benchmarks.", table_cell_style)],
        [Paragraph("<code>backend/.../orchestration/</code>", table_cell_bold), Paragraph("17-State FSM", table_cell_style), Paragraph("Celery tasks, Redis state tracking, parallel upload allocator, compensating rollback.", table_cell_style)],
        [Paragraph("<code>backend/.../telemetry/</code>", table_cell_bold), Paragraph("Pricing Matrix", table_cell_style), Paragraph("Dynamic storage, operation, and egress pricing telemetry across AWS, Azure, and GCP.", table_cell_style)],
        [Paragraph("<code>backend/.../experiments/</code>", table_cell_bold), Paragraph("Research Simulation", table_cell_style), Paragraph("Zipfian workload generator, Monte Carlo runner, Pareto sorter, LaTeX/PNG exporter.", table_cell_style)],
        [Paragraph("<code>frontend/</code>", table_cell_bold), Paragraph("Web Dashboard", table_cell_style), Paragraph("Intent wizard UI, FSM progress bar, cloud badge indicators, cost trade-off visualizer.", table_cell_style)],
        [Paragraph("<code>infra/</code>", table_cell_bold), Paragraph("IaC & Automation", table_cell_style), Paragraph("Terraform multi-cloud provisioning, Ansible playbooks, Celery systemd units.", table_cell_style)],
    ]
    t_manifest = Table(manifest_data, colWidths=[120, 100, 284])
    t_manifest.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, code_bg]),
    ]))
    story.append(t_manifest)
    story.append(Spacer(1, 8))

    # 3. Mathematical Optimization Formulation
    story.append(Paragraph("3. MILP Mathematical Optimization Formulation", h1_style))
    story.append(Paragraph(
        "<b>Sets & Indices:</b> Clouds $\\mathcal{C} = \\{\\text{AWS}, \\text{AZURE}, \\text{GCP}\\}$, "
        "Storage Tiers $\\mathcal{T} = \\{\\text{standard}, \\text{infrequent}, \\text{archive}\\}$.<br/>"
        "<b>Decision Variables:</b> $x_{c,t} \\in \\{0, 1\\} \\quad \\forall c \\in \\mathcal{C}, \\forall t \\in \\mathcal{T}$ "
        "where $x_{c,t} = 1$ indicates placement in cloud $c$ tier $t$.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Total Monthly Cost Formulation:</b><br/>"
        "$$\\text{Cost}_{c,t} = (S \\cdot C^{\\text{storage}}_{c,t}) + (W \\cdot C^{\\text{write}}_{c,t}) + (R \\cdot C^{\\text{read}}_{c,t}) + (R \\cdot S \\cdot C^{\\text{egress}}_{c,t})$$<br/>"
        "where $S$ is file size (GB), $W$ is write operations, $R$ is read operations, and $C$ are unit pricing rates.",
        body_style
    ))
    story.append(Paragraph("<b>Optimization Objectives:</b>", h2_style))
    story.append(Paragraph("• <b>Cost Minimization:</b> $\\min \\sum_{c} \\sum_{t} \\text{Cost}_{c,t} \\cdot x_{c,t}$", bullet_style))
    story.append(Paragraph("• <b>Latency Minimization:</b> $\\min \\sum_{c} \\sum_{t} L_{c,t} \\cdot x_{c,t}$", bullet_style))
    story.append(Paragraph("• <b>Balanced Objective:</b> $\\min \\left[ \\alpha \\frac{\\sum \\text{Cost}_{c,t} x_{c,t}}{\\text{Cost}_{\\max}} + (1-\\alpha) \\frac{\\sum L_{c,t} x_{c,t}}{L_{\\max}} \\right]$ with $\\alpha = 0.5$", bullet_style))

    story.append(Paragraph("<b>Mathematical Constraints:</b>", h2_style))
    story.append(Paragraph("1. <b>Replica Redundancy:</b> $\\sum_{c \\in \\mathcal{C}} \\sum_{t \\in \\mathcal{T}} x_{c,t} \\ge K \\quad (K \\in \\{1, 2, 3\\})$", bullet_style))
    story.append(Paragraph("2. <b>Provider Exclusivity:</b> $\\sum_{t \\in \\mathcal{T}} x_{c,t} \\le 1 \\quad \\forall c \\in \\mathcal{C}$ (at most one tier per cloud provider)", bullet_style))
    story.append(Paragraph("3. <b>Budget Bound:</b> $\\sum_{c} \\sum_{t} \\text{Cost}_{c,t} \\cdot x_{c,t} \\le B$ (if monthly budget $B$ is specified)", bullet_style))
    story.append(Paragraph("4. <b>Latency SLA Bound:</b> $\\frac{\\sum_{c,t} L_{c,t} x_{c,t}}{\\sum_{c,t} x_{c,t}} \\le L_{\\text{req}}$ (if max latency $L_{\\text{req}}$ is specified)", bullet_style))
    story.append(Paragraph("5. <b>Geo-Fencing:</b> $x_{c,t} = 0 \\quad \\forall c \\notin \\mathcal{C}_{\\text{allowed}}$", bullet_style))
    story.append(Spacer(1, 8))

    # 4. Dynamic Pricing & Telemetry Table
    story.append(Paragraph("4. Dynamic Pricing & Latency Reference Table (India / Asia South)", h1_style))
    pricing_data = [
        [Paragraph("Provider (Region)", table_header_style), Paragraph("Tier", table_header_style), Paragraph("Storage ($/GB-mo)", table_header_style), Paragraph("Write ($/10k)", table_header_style), Paragraph("Read ($/10k)", table_header_style), Paragraph("Egress ($/GB)", table_header_style), Paragraph("Latency", table_header_style)],
        [Paragraph("AWS (ap-south-1)", table_cell_bold), Paragraph("Standard", table_cell_style), Paragraph("$0.0230", table_cell_style), Paragraph("$0.050", table_cell_style), Paragraph("$0.0040", table_cell_style), Paragraph("$0.090", table_cell_style), Paragraph("45 ms", table_cell_style)],
        [Paragraph("AWS (ap-south-1)", table_cell_bold), Paragraph("Infrequent", table_cell_style), Paragraph("$0.0125", table_cell_style), Paragraph("$0.100", table_cell_style), Paragraph("$0.0100", table_cell_style), Paragraph("$0.090", table_cell_style), Paragraph("65 ms", table_cell_style)],
        [Paragraph("AWS (ap-south-1)", table_cell_bold), Paragraph("Archive", table_cell_style), Paragraph("$0.0040", table_cell_style), Paragraph("$0.050", table_cell_style), Paragraph("$0.0500", table_cell_style), Paragraph("$0.090", table_cell_style), Paragraph("180s", table_cell_style)],
        [Paragraph("Azure (centralindia)", table_cell_bold), Paragraph("Standard", table_cell_style), Paragraph("$0.0180", table_cell_style), Paragraph("$0.045", table_cell_style), Paragraph("$0.0035", table_cell_style), Paragraph("$0.085", table_cell_style), Paragraph("40 ms", table_cell_style)],
        [Paragraph("Azure (centralindia)", table_cell_bold), Paragraph("Infrequent", table_cell_style), Paragraph("$0.0100", table_cell_style), Paragraph("$0.090", table_cell_style), Paragraph("$0.0090", table_cell_style), Paragraph("$0.085", table_cell_style), Paragraph("60 ms", table_cell_style)],
        [Paragraph("Azure (centralindia)", table_cell_bold), Paragraph("Archive", table_cell_style), Paragraph("$0.0020", table_cell_style), Paragraph("$0.100", table_cell_style), Paragraph("$0.0500", table_cell_style), Paragraph("$0.085", table_cell_style), Paragraph("300s", table_cell_style)],
        [Paragraph("GCP (asia-south1)", table_cell_bold), Paragraph("Standard", table_cell_style), Paragraph("$0.0200", table_cell_style), Paragraph("$0.050", table_cell_style), Paragraph("$0.0040", table_cell_style), Paragraph("$0.080", table_cell_style), Paragraph("42 ms", table_cell_style)],
        [Paragraph("GCP (asia-south1)", table_cell_bold), Paragraph("Infrequent", table_cell_style), Paragraph("$0.0100", table_cell_style), Paragraph("$0.100", table_cell_style), Paragraph("$0.0100", table_cell_style), Paragraph("$0.080", table_cell_style), Paragraph("58 ms", table_cell_style)],
        [Paragraph("GCP (asia-south1)", table_cell_bold), Paragraph("Archive", table_cell_style), Paragraph("$0.0025", table_cell_style), Paragraph("$0.050", table_cell_style), Paragraph("$0.0500", table_cell_style), Paragraph("$0.080", table_cell_style), Paragraph("240s", table_cell_style)],
    ]
    t_pricing = Table(pricing_data, colWidths=[95, 65, 75, 65, 65, 65, 54])
    t_pricing.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, code_bg]),
    ]))
    story.append(t_pricing)
    story.append(Spacer(1, 8))

    # 5. 17-State Asynchronous FSM & Rollback
    story.append(Paragraph("5. 17-State Asynchronous FSM & Compensating Rollback", h1_style))
    story.append(Paragraph(
        "Upload lifecycle is orchestrated asynchronously via Celery and Redis. The state machine guarantees atomic multi-cloud "
        "consistency: if any chunk upload or integrity validation fails, a compensating rollback cleans up all allocated cloud resources.",
        body_style
    ))
    fsm_states_text = (
        "1. INITIALIZED          -> 7. ALLOCATING_PRESIGNED  -> 13. INTEGRITY_CONFIRMED\n"
        "2. PARSING_INTENT        -> 8. PRESIGNED_READY       -> 14. COMPLETED (Terminal Success)\n"
        "3. INTENT_PARSED        -> 9. UPLOADING_PARTS       -> 15. ROLLING_BACK\n"
        "4. OPTIMIZING_POLICY    -> 10. PARTS_UPLOADED       -> 16. ROLLED_BACK (Compensated)\n"
        "5. POLICY_DETERMINED    -> 11. COMPLETING_SESSIONS  -> 17. FAILED (Fatal Error)\n"
        "6. PREPARING_CLOUDS     -> 12. VERIFYING_INTEGRITY"
    )
    t_fsm = Table([[Preformatted(fsm_states_text, code_style)]], colWidths=[504])
    t_fsm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), code_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_fsm)
    story.append(Paragraph(
        "<b>Compensating Rollback Execution:</b><br/>"
        "• <b>AWS S3:</b> Aborts active multipart upload IDs (<code>s3.abort_multipart_upload</code>) or deletes uploaded objects.<br/>"
        "• <b>Azure Blob:</b> Deletes uncommitted block lists and staging blobs (<code>blob_client.delete_blob</code>).<br/>"
        "• <b>GCP Storage:</b> Deletes incomplete composite chunks and uploaded objects (<code>blob.delete</code>).",
        body_style
    ))
    story.append(Spacer(1, 8))

    # 6. REST API Reference
    story.append(Paragraph("6. REST API Endpoint Reference", h1_style))
    api_data = [
        [Paragraph("Endpoint", table_header_style), Paragraph("Method", table_header_style), Paragraph("Description & Payload", table_header_style)],
        [Paragraph("<code>/api/intent/parse/</code>", table_cell_bold), Paragraph("POST", table_cell_style), Paragraph("Extracts constraints from natural text. <code>{\"user_text\": \"...\", \"file_size_bytes\": N}</code>", table_cell_style)],
        [Paragraph("<code>/api/optimizer/solve/</code>", table_cell_bold), Paragraph("POST", table_cell_style), Paragraph("Solves MILP placement model. <code>{\"constraints\": {...}, \"file_size_bytes\": N}</code>", table_cell_style)],
        [Paragraph("<code>/api/orchestration/upload/start/</code>", table_cell_bold), Paragraph("POST", table_cell_style), Paragraph("Initiates async FSM pipeline. Returns <code>operation_id</code>.", table_cell_style)],
        [Paragraph("<code>/api/orchestration/status/&lt;op_id&gt;/</code>", table_cell_bold), Paragraph("GET", table_cell_style), Paragraph("Polls FSM progress, current state, and direct presigned upload URLs.", table_cell_style)],
        [Paragraph("<code>/api/orchestration/complete/&lt;op_id&gt;/</code>", table_cell_bold), Paragraph("POST", table_cell_style), Paragraph("Signals chunk upload completion to trigger integrity check & final commit.", table_cell_style)],
        [Paragraph("<code>/api/telemetry/pricing/</code>", table_cell_bold), Paragraph("GET", table_cell_style), Paragraph("Returns live multi-cloud pricing tables and latency benchmarks.", table_cell_style)],
    ]
    t_api = Table(api_data, colWidths=[160, 45, 299])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, code_bg]),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 8))

    # 7. Verification & Operational Guidelines
    story.append(Paragraph("7. Testing, Benchmarking & Deployment Operations", h1_style))
    story.append(Paragraph(
        "<b>1. Run Full Unit Test Suite:</b><br/>"
        "<code>python -m unittest discover -s . -p \"tests.py\"</code> (Verifies intent, optimizer, and FSM modules with 100% pass rate).",
        body_style
    ))
    story.append(Paragraph(
        "<b>2. Execute Research Simulation Suite:</b><br/>"
        "<code>python manage.py run_benchmark --num-workloads 100 --out-dir ./benchmark_results</code><br/>"
        "Generates <code>benchmark_data.csv</code>, publication LaTeX table <code>table_comparison.tex</code>, and Matplotlib figures.",
        body_style
    ))
    story.append(Paragraph(
        "<b>3. Automated Production Cloud Deployment:</b><br/>"
        "• Provision infrastructure via Terraform: <code>terraform apply -var-file=\"environments/dev/terraform.tfvars\"</code><br/>"
        "• Deploy application & services via Ansible: <code>ansible-playbook -i inventory/aws_ec2.yml playbook.yml</code><br/>"
        "• Target Git URL: <code>https://github.com/charan-sai-ramisetti/Intent-based-cloud-storage.git</code>",
        body_style
    ))
    story.append(Paragraph(
        "<b>4. Critical Architectural Invariants for Future AI Agents:</b><br/>"
        "• Never allow an LLM to select cloud providers directly; all requirements must compile into <code>ParsedConstraints</code>.<br/>"
        "• Preserve multi-cloud rollback parity for any newly introduced cloud provider or storage tier.<br/>"
        "• Always use UTC timezone-aware datetimes (<code>datetime.now(timezone.utc)</code>).",
        body_style
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")


if __name__ == "__main__":
    out_file = os.path.join(os.getcwd(), "project details.pdf")
    build_pdf(out_file)

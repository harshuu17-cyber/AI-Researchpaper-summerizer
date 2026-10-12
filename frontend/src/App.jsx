import { useState, useRef } from "react";
import axios from "axios";
import {
  Upload,
  FileText,
  Sparkles,
  BarChart3,
  Target,
  FlaskConical,
  Lightbulb,
  AlertCircle,
  Loader2,
  Download,
  CheckCircle2,
  FileCode,
  FileType,
  Copy,
  Check,
  Printer,
  Zap,
  Award,
  Briefcase,
} from "lucide-react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

import "./App.css";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL !== undefined
    ? import.meta.env.VITE_API_BASE_URL
    : (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");


function App() {

  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const toastTimeoutRef = useRef(null);


  const showToast = (message) => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
    }
    setToastMessage(message);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage("");
    }, 3200);
  };


  const handleFileChange = (event) => {

    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setError("Please select a PDF file.");
      return;
    }

    setFile(selectedFile);
    setError("");
    setResult(null);
  };


  const analyzePaper = async () => {

    if (!file) {
      setError("Please select a research paper PDF first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {

      // -----------------------------------------
      // STEP 1: Upload PDF
      // -----------------------------------------

      const formData = new FormData();

      formData.append("file", file);

      const uploadResponse = await axios.post(
        `${API_BASE_URL}/api/paper/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const paperId = uploadResponse.data.paper_id;


      // -----------------------------------------
      // STEP 2: Analyze paper
      // -----------------------------------------

      const analysisResponse = await axios.post(
        `${API_BASE_URL}/api/paper/analyze/${paperId}`
      );


      setResult(analysisResponse.data);

    } catch (err) {

      console.error(err);

      const message =
        err.response?.data?.detail ||
        "Something went wrong while analyzing the paper.";

      setError(message);

    } finally {

      setLoading(false);

    }
  };


  const getSafeTitle = () => {
    const paperTitle = result?.analysis?.title || "Research_Paper";
    return paperTitle
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 45) || "paper";
  };


  const generateMarkdownContent = () => {
    if (!result) return "";
    const analysisData = result.analysis || {};
    const numerical = result.numerical_results?.results || [];

    let md = `# ResearchLens Summary: ${analysisData.title || "Research Paper"}\n\n`;
    md += `**Authors:** ${analysisData.authors || "Not specified"}  \n`;
    md += `**Research Area:** ${analysisData.research_area || "Not specified"}  \n`;
    if (analysisData.keywords?.length) {
      md += `**Keywords:** ${analysisData.keywords.join(", ")}  \n`;
    }
    md += `**Document Info:** ${result.page_count || "N/A"} pages | ${
      result.word_count ? result.word_count.toLocaleString() : "N/A"
    } words  \n\n`;
    md += `---\n\n`;

    if (analysisData.tldr && analysisData.tldr !== "Not specified in the paper") {
      md += `> **Executive TL;DR:** ${analysisData.tldr}\n\n---\n\n`;
    }

    md += `## 1. Abstract Summary\n${analysisData.abstract_summary || "Not specified"}\n\n---\n\n`;

    md += `## 2. Research Problem & Objective\n`;
    md += `### Research Problem\n${analysisData.research_problem || "Not specified"}\n\n`;
    md += `### Objective\n${analysisData.objective || "Not specified"}\n\n`;

    if (analysisData.key_contributions?.length) {
      md += `### Key Novel Contributions\n`;
      analysisData.key_contributions.forEach((c) => {
        md += `- ${c}\n`;
      });
      md += `\n`;
    }
    md += `---\n\n`;

    md += `## 3. Methodology & System Architecture\n${analysisData.methodology || "Not specified"}\n\n`;
    if (analysisData.models_or_algorithms?.length) {
      md += `### Models / Algorithms\n`;
      analysisData.models_or_algorithms.forEach((m) => {
        md += `- ${m}\n`;
      });
      md += `\n`;
    }
    md += `### Dataset\n${analysisData.dataset || "Not specified"}\n\n---\n\n`;

    md += `## 4. Key Findings & Results\n`;
    if (analysisData.key_findings?.length) {
      md += `### Key Findings\n`;
      analysisData.key_findings.forEach((f) => {
        md += `- ${f}\n`;
      });
      md += `\n`;
    }
    if (analysisData.key_results?.length) {
      md += `### Key Results\n`;
      analysisData.key_results.forEach((r) => {
        md += `- ${r}\n`;
      });
      md += `\n`;
    }
    md += `---\n\n`;

    if (analysisData.practical_applications?.length) {
      md += `## 5. Practical Applications & Use Cases\n`;
      analysisData.practical_applications.forEach((a) => {
        md += `- ${a}\n`;
      });
      md += `\n---\n\n`;
    }

    if (numerical.length > 0) {
      md += `## 6. Quantitative Evidence & Numerical Results\n\n`;
      md += `| Metric | Measurement / Value | Unit | Context / Label |\n`;
      md += `| :--- | :--- | :--- | :--- |\n`;
      numerical.forEach((item) => {
        md += `| ${item.metric || "N/A"} | ${item.value} | ${item.unit || ""} | ${item.label || "Overall"} |\n`;
      });
      md += `\n---\n\n`;
    }

    md += `## 6. Conclusion\n${analysisData.conclusion || "Not specified"}\n\n---\n\n`;

    md += `## 7. Limitations & Future Work\n`;
    if (analysisData.limitations?.length) {
      md += `### Limitations\n`;
      analysisData.limitations.forEach((l) => {
        md += `- ${l}\n`;
      });
      md += `\n`;
    }
    if (analysisData.future_work?.length) {
      md += `### Future Work\n`;
      analysisData.future_work.forEach((fw) => {
        md += `- ${fw}\n`;
      });
      md += `\n`;
    }

    md += `---\n*Generated by ResearchLens — AI-Powered Research Paper Intelligence*\n`;
    return md;
  };


  const generatePlainTextContent = () => {
    if (!result) return "";
    const analysisData = result.analysis || {};
    const numerical = result.numerical_results?.results || [];

    const border = "=".repeat(76);
    const subborder = "-".repeat(76);

    let txt = `${border}\n`;
    txt += `RESEARCHLENS - EXECUTIVE RESEARCH PAPER SUMMARY\n`;
    txt += `${border}\n`;
    txt += `TITLE:         ${analysisData.title || "Research Paper"}\n`;
    txt += `AUTHORS:       ${analysisData.authors || "Not specified"}\n`;
    txt += `RESEARCH AREA: ${analysisData.research_area || "Not specified"}\n`;
    if (analysisData.keywords?.length) {
      txt += `KEYWORDS:      ${analysisData.keywords.join(", ")}\n`;
    }
    txt += `DOCUMENT INFO: ${result.page_count || "N/A"} pages | ${
      result.word_count ? result.word_count.toLocaleString() : "N/A"
    } words\n\n`;

    txt += `${subborder}\n1. ABSTRACT SUMMARY\n${subborder}\n`;
    txt += `${analysisData.abstract_summary || "Not specified"}\n\n`;

    txt += `${subborder}\n2. RESEARCH PROBLEM & OBJECTIVE\n${subborder}\n`;
    txt += `Problem:\n  ${analysisData.research_problem || "Not specified"}\n\n`;
    txt += `Objective:\n  ${analysisData.objective || "Not specified"}\n\n`;

    txt += `${subborder}\n3. METHODOLOGY & SYSTEM ARCHITECTURE\n${subborder}\n`;
    txt += `${analysisData.methodology || "Not specified"}\n\n`;
    if (analysisData.models_or_algorithms?.length) {
      txt += `Models / Algorithms:\n`;
      analysisData.models_or_algorithms.forEach((m) => {
        txt += `  * ${m}\n`;
      });
      txt += `\n`;
    }
    txt += `Dataset: ${analysisData.dataset || "Not specified"}\n\n`;

    txt += `${subborder}\n4. KEY FINDINGS & RESULTS\n${subborder}\n`;
    if (analysisData.key_findings?.length) {
      txt += `Key Findings:\n`;
      analysisData.key_findings.forEach((f) => {
        txt += `  * ${f}\n`;
      });
      txt += `\n`;
    }
    if (analysisData.key_results?.length) {
      txt += `Key Results:\n`;
      analysisData.key_results.forEach((r) => {
        txt += `  * ${r}\n`;
      });
      txt += `\n`;
    }

    if (numerical.length > 0) {
      txt += `${subborder}\n5. QUANTITATIVE EVIDENCE & NUMERICAL RESULTS\n${subborder}\n`;
      numerical.forEach((item) => {
        txt += `  - ${item.metric || "N/A"}: ${item.value} ${item.unit || ""} (${item.label || "Overall"})\n`;
      });
      txt += `\n`;
    }

    txt += `${subborder}\n6. CONCLUSION\n${subborder}\n`;
    txt += `${analysisData.conclusion || "Not specified"}\n\n`;

    txt += `${subborder}\n7. LIMITATIONS & FUTURE WORK\n${subborder}\n`;
    if (analysisData.limitations?.length) {
      txt += `Limitations:\n`;
      analysisData.limitations.forEach((l) => {
        txt += `  * ${l}\n`;
      });
      txt += `\n`;
    }
    if (analysisData.future_work?.length) {
      txt += `Future Work:\n`;
      analysisData.future_work.forEach((fw) => {
        txt += `  * ${fw}\n`;
      });
      txt += `\n`;
    }

    txt += `${border}\nGenerated by ResearchLens — AI-Powered Research Paper Intelligence\n${border}\n`;
    return txt;
  };


  const downloadSummaryFile = async (format = "pdf") => {
    if (!result) return;
    const safeTitle = getSafeTitle();

    if (format === "print") {
      window.print();
      return;
    }

    if (format === "pdf") {
      setDownloading(true);
      try {
        if (result.paper_id) {
          const response = await axios.get(
            `${API_BASE_URL}/api/paper/download/${result.paper_id}?format=pdf`,
            { responseType: "blob" }
          );
          const blob = new Blob([response.data], { type: "application/pdf" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${safeTitle}_summary.pdf`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          showToast("PDF summary downloaded successfully!");
          return;
        }
      } catch (err) {
        console.warn("Backend PDF download fallback:", err);
      } finally {
        setDownloading(false);
      }

      // Fallback: trigger print dialog for saving as PDF
      window.print();
      showToast("Print / Save as PDF opened!");
      return;
    }

    if (format === "json") {
      const dataStr = JSON.stringify(result, null, 2);
      const blob = new Blob([dataStr], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeTitle}_analysis.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("JSON analysis exported successfully!");
      return;
    }

    if (format === "txt") {
      const text = generatePlainTextContent();
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeTitle}_summary.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("Plain text summary downloaded!");
      return;
    }

    // Default: Markdown summary
    const md = generateMarkdownContent();
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeTitle}_summary.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Markdown summary downloaded successfully!");
  };


  const copySummaryText = async () => {
    if (!result) return;
    try {
      const md = generateMarkdownContent();
      await navigator.clipboard.writeText(md);
      setCopied(true);
      showToast("Summary copied to clipboard!");
      setTimeout(() => setCopied(false), 2600);
    } catch (err) {
      console.error("Failed to copy:", err);
      showToast("Could not copy to clipboard.");
    }
  };


  const analysis = result?.analysis;

  const charts = result?.charts?.charts || [];


  return (
    <div className="app">

      {/* ---------------------------------------- */}
      {/* HEADER */}
      {/* ---------------------------------------- */}

      <header className="header">

        <div className="brand">

          <div className="brand-icon">
            <Sparkles size={22} />
          </div>

          <div>
            <h1>ResearchLens</h1>

            <p>
              AI-Powered Research Paper Intelligence
            </p>
          </div>

        </div>

        {result && analysis && (
          <div className="header-actions">
            <button
              className="header-download-btn primary"
              onClick={() => downloadSummaryFile("pdf")}
              title="Download Paper Summary as PDF"
              disabled={downloading}
            >
              <Download size={15} />
              <span>{downloading ? "Preparing PDF..." : "Download Summary"}</span>
            </button>
            <button
              className="header-download-btn secondary"
              onClick={() => downloadSummaryFile("md")}
              title="Download Markdown Summary (.md)"
            >
              <FileText size={15} />
              <span>.MD</span>
            </button>
          </div>
        )}

      </header>


      {/* ---------------------------------------- */}
      {/* MAIN */}
      {/* ---------------------------------------- */}

      <main className="container">


        {/* -------------------------------------- */}
        {/* HERO */}
        {/* -------------------------------------- */}

        <section className="hero">

          <div className="hero-content">

            <span className="badge">
              <Sparkles size={15} />
              AI Research Assistant
            </span>

            <h2>
              Understand research papers
              <span> faster.</span>
            </h2>

            <p>
              Upload a research paper and let ResearchLens
              extract the key ideas, methodology, results,
              numerical evidence and visual insights.
            </p>

          </div>

        </section>


        {/* -------------------------------------- */}
        {/* UPLOAD CARD */}
        {/* -------------------------------------- */}

        <section className="upload-card">

          <div className="upload-icon">
            <Upload size={30} />
          </div>

          <h3>
            Upload Research Paper
          </h3>

          <p>
            Select a PDF research paper to begin analysis.
          </p>


          <label className="file-input">

            <FileText size={18} />

            <span>
              {file
                ? file.name
                : "Choose PDF file"}
            </span>

            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
            />

          </label>


          <button
            className="analyze-button"
            onClick={analyzePaper}
            disabled={loading || !file}
          >

            {loading ? (
              <>
                <Loader2
                  size={18}
                  className="spin"
                />

                Analyzing Paper...
              </>
            ) : (
              <>
                <Sparkles size={18} />

                Analyze Research Paper
              </>
            )}

          </button>


          {error && (

            <div className="error-message">

              <AlertCircle size={18} />

              {error}

            </div>

          )}

        </section>


        {/* -------------------------------------- */}
        {/* DOWNLOAD ACTION TOOLBAR */}
        {/* -------------------------------------- */}

        {result && analysis && (

          <>

            <section className="download-toolbar-card">

              <div className="toolbar-info">

                <div className="status-pill">
                  <span className="status-pulse-dot"></span>
                  <CheckCircle2 size={16} />
                  <span>Analysis Ready</span>
                </div>

                <h3 className="toolbar-heading">
                  Download Summarized Paper
                </h3>

                <p className="toolbar-meta">
                  <strong>{result.page_count}</strong> pages &bull;{" "}
                  <strong>
                    {result.word_count?.toLocaleString()}
                  </strong>{" "}
                  words synthesized &bull; AI structured
                </p>

              </div>

              <div className="toolbar-actions">

                <button
                  className="download-action-btn primary"
                  onClick={() => downloadSummaryFile("pdf")}
                  title="Download executive academic summary as formatted PDF document"
                  disabled={downloading}
                >
                  {downloading ? <Loader2 size={17} className="spin" /> : <Download size={17} />}
                  <span>{downloading ? "Generating PDF..." : "Download PDF Summary"}</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("md")}
                  title="Download academic summary as formatted Markdown (.md)"
                >
                  <FileText size={16} />
                  <span>Markdown (.md)</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("txt")}
                  title="Download clean plain text (.txt) document"
                >
                  <FileType size={16} />
                  <span>Plain Text (.txt)</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("json")}
                  title="Export structured analytical data as JSON"
                >
                  <FileCode size={16} />
                  <span>Export JSON</span>
                </button>

                <button
                  className="download-action-btn outline"
                  onClick={copySummaryText}
                  title="Copy formatted summary to clipboard"
                >
                  {copied ? <Check size={16} className="icon-success" /> : <Copy size={16} />}
                  <span>{copied ? "Copied!" : "Copy Text"}</span>
                </button>

                <button
                  className="download-action-btn outline"
                  onClick={() => downloadSummaryFile("print")}
                  title="Print summary or save as PDF via system dialog"
                >
                  <Printer size={16} />
                  <span>Print</span>
                </button>

              </div>

            </section>


            {/* ---------------------------------- */}
            {/* PAPER OVERVIEW */}
            {/* ---------------------------------- */}

            <section className="section">

              <div className="section-heading">

                <FileText />

                <div>

                  <h2>
                    Paper Overview
                  </h2>

                  <p>
                    AI-generated understanding of the paper
                  </p>

                </div>

              </div>


              <div className="overview-card">

                <div className="overview-header-row">

                  <h3>
                    {analysis.title}
                  </h3>

                  <button
                    className="card-quick-download"
                    onClick={() => downloadSummaryFile("pdf")}
                    title="Quick Download PDF Summary"
                  >
                    <Download size={14} />
                    <span>Download Summary</span>
                  </button>

                </div>

                <p className="authors">
                  {analysis.authors}
                </p>

                <div className="tags">

                  <span>
                    {analysis.research_area}
                  </span>

                  {analysis.keywords?.slice(0, 5).map(
                    (keyword, index) => (
                      <span key={index}>
                        {keyword}
                      </span>
                    )
                  )}

                </div>

                {analysis.tldr && analysis.tldr !== "Not specified in the paper" && (
                  <div className="tldr-callout">
                    <div className="tldr-badge">
                      <Zap size={14} />
                      <span>Executive TL;DR</span>
                    </div>
                    <p>{analysis.tldr}</p>
                  </div>
                )}

                <p className="summary">
                  {analysis.abstract_summary}
                </p>

              </div>

            </section>


            {/* ---------------------------------- */}
            {/* RESEARCH PROBLEM + OBJECTIVE */}
            {/* ---------------------------------- */}

            <section className="two-column">

              <InfoCard
                icon={<Target />}
                title="Research Problem"
                text={analysis.research_problem}
              />

              <InfoCard
                icon={<Lightbulb />}
                title="Objective"
                text={analysis.objective}
              />

            </section>


            {/* ---------------------------------- */}
            {/* KEY NOVEL CONTRIBUTIONS */}
            {/* ---------------------------------- */}

            {analysis.key_contributions?.length > 0 && (

              <section className="section">

                <div className="section-heading">

                  <Award />

                  <div>

                    <h2>
                      Key Novel Contributions
                    </h2>

                    <p>
                      What this research introduces that did not exist in prior literature
                    </p>

                  </div>

                </div>

                <div className="contributions-card">

                  <ul className="contributions-list">

                    {analysis.key_contributions.map((contribution, index) => (
                      <li key={index}>
                        <span className="contribution-num">{index + 1}</span>
                        <span>{contribution}</span>
                      </li>
                    ))}

                  </ul>

                </div>

              </section>

            )}


            {/* ---------------------------------- */}
            {/* METHODOLOGY */}
            {/* ---------------------------------- */}

            <section className="section">

              <div className="section-heading">

                <FlaskConical />

                <div>

                  <h2>
                    Methodology
                  </h2>

                  <p>
                    How the research was conducted
                  </p>

                </div>

              </div>


              <div className="methodology-card">

                <p>
                  {analysis.methodology}
                </p>

                <div className="method-grid">

                  <div>
                    <strong>Dataset</strong>

                    <p>
                      {analysis.dataset}
                    </p>
                  </div>


                  <div>
                    <strong>Models / Algorithms</strong>

                    <div className="algorithm-list">

                      {analysis.models_or_algorithms?.map(
                        (model, index) => (
                          <span key={index}>
                            {model}
                          </span>
                        )
                      )}

                    </div>

                  </div>

                </div>

              </div>

            </section>


            {/* ---------------------------------- */}
            {/* RESULTS CHARTS */}
            {/* ---------------------------------- */}

            <section className="section">

              <div className="section-heading">

                <BarChart3 />

                <div>

                  <h2>
                    Research Results
                  </h2>

                  <p>
                    Numerical evidence extracted directly
                    from the paper
                  </p>

                </div>

              </div>


              {charts.length > 0 ? (

                <div className="charts-grid">

                  {charts.map((chart) => (

                    <div
                      className="chart-card"
                      key={chart.id}
                    >

                      <h3>
                        {chart.title}
                      </h3>

                      <ResponsiveContainer
                        width="100%"
                        height={320}
                      >

                        <BarChart
                          data={chart.data}
                        >

                          <CartesianGrid
                            strokeDasharray="3 3"
                          />

                          <XAxis
                            dataKey="label"
                          />

                          <YAxis />

                          <Tooltip />

                          <Bar
                            dataKey="value"
                            name={chart.metric}
                          />

                        </BarChart>

                      </ResponsiveContainer>

                    </div>

                  ))}

                </div>

              ) : (

                <div className="empty-state">

                  No suitable numerical data was found
                  for visualization.

                </div>

              )}

            </section>


            {/* ---------------------------------- */}
            {/* KEY RESULTS */}
            {/* ---------------------------------- */}

            <section className="two-column">

              <InfoListCard
                icon={<BarChart3 />}
                title="Key Results"
                items={analysis.key_results}
              />

              <InfoListCard
                icon={<Sparkles />}
                title="Key Findings"
                items={analysis.key_findings}
              />

            </section>


            {/* ---------------------------------- */}
            {/* PRACTICAL APPLICATIONS */}
            {/* ---------------------------------- */}

            {analysis.practical_applications?.length > 0 && (

              <section className="section">

                <div className="section-heading">

                  <Briefcase />

                  <div>

                    <h2>
                      Practical Applications & Impact
                    </h2>

                    <p>
                      Real-world domains and industry systems where this research applies
                    </p>

                  </div>

                </div>

                <div className="applications-grid">

                  {analysis.practical_applications.map((app, index) => (
                    <div className="app-card" key={index}>
                      <div className="app-card-icon">
                        <Sparkles size={16} />
                      </div>
                      <p>{app}</p>
                    </div>
                  ))}

                </div>

              </section>

            )}


            {/* ---------------------------------- */}
            {/* CONCLUSION */}
            {/* ---------------------------------- */}

            <section className="section">

              <div className="conclusion-card">

                <h2>
                  Conclusion
                </h2>

                <p>
                  {analysis.conclusion}
                </p>

              </div>

            </section>


            {/* ---------------------------------- */}
            {/* LIMITATIONS + FUTURE WORK */}
            {/* ---------------------------------- */}

            <section className="two-column">

              <InfoListCard
                icon={<AlertCircle />}
                title="Limitations"
                items={analysis.limitations}
              />

              <InfoListCard
                icon={<Lightbulb />}
                title="Future Work"
                items={analysis.future_work}
              />

            </section>


            {/* ---------------------------------- */}
            {/* BOTTOM EXPORT CARD */}
            {/* ---------------------------------- */}

            <section className="export-footer-card">

              <div className="export-footer-content">

                <div className="export-footer-icon">
                  <Sparkles size={26} />
                </div>

                <div>
                  <h3>Ready to use this paper summary?</h3>
                  <p>
                    Save this academic analysis, methodologies, key findings, and numerical results to reference in your research.
                  </p>
                </div>

              </div>

              <div className="export-footer-buttons">

                <button
                  className="download-action-btn primary"
                  onClick={() => downloadSummaryFile("pdf")}
                  disabled={downloading}
                >
                  <Download size={17} />
                  <span>Download PDF Summary</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("md")}
                >
                  <FileText size={16} />
                  <span>Markdown (.md)</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("txt")}
                >
                  <FileType size={16} />
                  <span>Plain Text (.txt)</span>
                </button>

                <button
                  className="download-action-btn secondary"
                  onClick={() => downloadSummaryFile("json")}
                >
                  <FileCode size={16} />
                  <span>Export JSON</span>
                </button>

                <button
                  className="download-action-btn outline"
                  onClick={copySummaryText}
                >
                  {copied ? <Check size={16} className="icon-success" /> : <Copy size={16} />}
                  <span>{copied ? "Copied!" : "Copy Summary"}</span>
                </button>

              </div>

            </section>

          </>

        )}

      </main>


      {/* ---------------------------------------- */}
      {/* FOOTER */}
      {/* ---------------------------------------- */}

      <footer>

        <p>
          ResearchLens • AI-Powered Research Paper
          Intelligence
        </p>

      </footer>


      {/* ---------------------------------------- */}
      {/* TOAST FEEDBACK */}
      {/* ---------------------------------------- */}

      {toastMessage && (
        <div className="download-toast">
          <CheckCircle2 size={18} />
          <span>{toastMessage}</span>
        </div>
      )}

    </div>
  );
}


/* ============================================= */
/* INFO CARD */
/* ============================================= */

function InfoCard({
  icon,
  title,
  text
}) {

  return (

    <div className="info-card">

      <div className="info-icon">
        {icon}
      </div>

      <h3>
        {title}
      </h3>

      <p>
        {text}
      </p>

    </div>

  );
}


/* ============================================= */
/* LIST CARD */
/* ============================================= */

function InfoListCard({
  icon,
  title,
  items
}) {

  return (

    <div className="info-card">

      <div className="info-icon">
        {icon}
      </div>

      <h3>
        {title}
      </h3>

      {items?.length ? (

        <ul>

          {items.map(
            (item, index) => (
              <li key={index}>
                {item}
              </li>
            )
          )}

        </ul>

      ) : (

        <p>
          Not specified in the paper.
        </p>

      )}

    </div>

  );
}


export default App;
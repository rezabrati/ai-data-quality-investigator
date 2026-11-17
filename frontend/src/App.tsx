import { useState } from "react";
import Markdown from "react-markdown";
import ColumnExplorer from "./ColumnExplorer";
import TargetSummary from "./TargetSummary";
import type { TargetProfile } from "./TargetSummary";
import type { ColumnProfile } from "./ColumnExplorer";

type InvestigationResult = {
  dataset_id: string;
  profile: {
    dataset_id: string;
    summary: {
      target_summary: TargetProfile | null;
      columns: ColumnProfile[];
      row_count: number;
      column_count: number;
      duplicate_row_count: number;
      findings: {
        code: string;
        column: string | null;
        count: number;
        message: string;
      }[];
    };
  };
  category_frequencies: {
    column: string;
    percent_basis: string;
    categories: {
      value: string;
      count: number;
      percent: number;
    }[];
    other_count: number;
  } | null;
  suggested_investigations: string;
};

const dashboardTabs = [
  { id: "overview", label: "Overview" },
  { id: "target", label: "Target" },
  { id: "columns", label: "Columns" },
  { id: "ai", label: "AI suggestions" },
] as const;

type DashboardTab = (typeof dashboardTabs)[number]["id"];

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState<
    "" | "classification" | "regression"
  >("");
  const [investigating, setInvestigating] = useState(false);
  const [investigation, setInvestigation] =
    useState<InvestigationResult | null>(null);
  const [activeTab, setActiveTab] =
    useState<DashboardTab>("overview");

  function clearResults() {
    setDatasetId(null);
    setInvestigation(null);
    setError(null);
    setActiveTab("overview");
  }

  async function uploadDataset() {
    if (!file || uploading || investigating) return;

    const target = targetColumn.trim();

    if (Boolean(target) !== Boolean(taskType)) {
      setError(
        "Provide both target column and task type, or leave both empty."
      );
      return;
    }

    setUploading(true);
    clearResults();

    try {
      const formData = new FormData();
      formData.append("file", file);

      if (target && taskType) {
        formData.append("target_column", target);
        formData.append("task_type", taskType);
      }

      const response = await fetch("/api/datasets/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Upload failed (${response.status}).`
        );
      }

      if (typeof data.dataset_id !== "string") {
        throw new Error("The server did not return a dataset ID.");
      }

      setDatasetId(data.dataset_id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not upload the dataset."
      );
    } finally {
      setUploading(false);
    }
  }

  async function runInvestigation() {
    if (!datasetId || uploading || investigating) return;

    setInvestigating(true);
    setInvestigation(null);
    setError(null);
    setActiveTab("overview");

    try {
      const response = await fetch(
        `/api/datasets/${datasetId}/investigate`,
        { method: "POST" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Investigation failed (${response.status}).`
        );
      }

      setInvestigation(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not investigate the dataset."
      );
    } finally {
      setInvestigating(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Dataset controls">
        <section className="card">
          <h2>Upload your dataset</h2>
          <p>Choose a CSV file with comma or semicolon separators.</p>

          <label htmlFor="dataset">CSV file</label>
          <input
            id="dataset"
            type="file"
            accept=".csv"
            disabled={uploading || investigating}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              clearResults();
            }}
          />

          {file && (
            <div className="selection">
              <strong>{file.name}</strong>
              <span>{(file.size / 1_000_000).toFixed(4)} MB</span>
            </div>
          )}

          <label htmlFor="target-column">
            Target column (optional)
          </label>
          <input
            id="target-column"
            type="text"
            placeholder="For example: y"
            value={targetColumn}
            disabled={uploading || investigating}
            onChange={(event) => {
              setTargetColumn(event.target.value);
              clearResults();
            }}
          />

          <label htmlFor="task-type">Task type (optional)</label>
          <select
            id="task-type"
            value={taskType}
            disabled={uploading || investigating}
            onChange={(event) => {
              const value = event.target.value;

              if (
                value === "" ||
                value === "classification" ||
                value === "regression"
              ) {
                setTaskType(value);
              }

              clearResults();
            }}
          >
            <option value="">No target analysis</option>
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
          </select>

          <button
            type="button"
            onClick={uploadDataset}
            disabled={!file || uploading || investigating}
          >
            {uploading ? "Uploading…" : "Upload dataset"}
          </button>

          {error && <p role="alert">{error}</p>}

          {datasetId && (
            <>
              <p role="status">
                Dataset uploaded successfully.
                <br />
                ID: <code>{datasetId}</code>
              </p>

              <button
                type="button"
                onClick={runInvestigation}
                disabled={uploading || investigating}
              >
                {investigating
                  ? "Investigating…"
                  : "Run investigation"}
              </button>
            </>
          )}

          {investigating && (
            <p role="status">
              Inspecting the dataset and generating follow-up questions…
            </p>
          )}
        </section>
      </aside>

      <main className="main-content">
        <header>
          <span className="badge">AI-powered investigation</span>
          <h1>AI Data Quality Investigator</h1>
          <p>
            Inspect your data, review quality findings, and explore
            suggested next investigations.
          </p>
        </header>

        {investigation === null && (
          <section className="card empty-state">
            <h2>
              {investigating
                ? "Investigation in progress"
                : "Your results will appear here"}
            </h2>
            <p>
              {investigating
                ? "The agents are inspecting your dataset. Please wait."
                : "Upload a CSV using the sidebar, then run an investigation."}
            </p>
          </section>
        )}

        {investigation !== null && (
          <section className="card dashboard-results">
            <h2>Dataset dashboard</h2>

            <nav
              className="dashboard-tabs"
              aria-label="Dashboard sections"
            >
              {dashboardTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`dashboard-tab ${
                    activeTab === tab.id ? "is-active" : ""
                  }`}
                  aria-pressed={activeTab === tab.id}
                  aria-controls="dashboard-panel"
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            <div
              id="dashboard-panel"
              className="dashboard-panel"
              role="region"
              aria-label={
                dashboardTabs.find((tab) => tab.id === activeTab)?.label
              }
            >
              {activeTab === "overview" && (
                <>
                  <div className="metrics">
                    <div className="metric">
                      <span>Rows</span>
                      <strong>
                        {investigation.profile.summary.row_count.toLocaleString()}
                      </strong>
                    </div>

                    <div className="metric">
                      <span>Columns</span>
                      <strong>
                        {investigation.profile.summary.column_count}
                      </strong>
                    </div>

                    <div className="metric">
                      <span>Duplicate rows</span>
                      <strong>
                        {investigation.profile.summary.duplicate_row_count.toLocaleString()}
                      </strong>
                    </div>

                    <div className="metric">
                      <span>Findings</span>
                      <strong>
                        {investigation.profile.summary.findings.length}
                      </strong>
                    </div>
                  </div>

                  <h3>Quality findings</h3>
                  <p>
                    These checks identify review candidates. Outliers
                    and placeholders are not automatically errors.
                  </p>

                  {investigation.profile.summary.findings.length === 0 ? (
                    <p>
                      No findings were reported by the implemented checks.
                    </p>
                  ) : (
                    <ul className="findings">
                      {investigation.profile.summary.findings.map(
                        (finding, index) => (
                          <li
                            key={`${finding.code}-${finding.column}-${index}`}
                          >
                            {finding.message}
                          </li>
                        )
                      )}
                    </ul>
                  )}
                </>
              )}

              {activeTab === "target" && (
                investigation.profile.summary.target_summary ? (
                  <TargetSummary
                    target={
                      investigation.profile.summary.target_summary
                    }
                  />
                ) : (
                  <div className="tab-empty">
                    <h3>No target configured</h3>
                    <p>
                      To include target analysis, upload the dataset
                      with a target column and task type.
                    </p>
                  </div>
                )
              )}

              {/* Keep mounted to preserve the selected column. */}
              <div hidden={activeTab !== "columns"}>
                <ColumnExplorer
                  key={investigation.dataset_id}
                  datasetId={investigation.dataset_id}
                  columns={investigation.profile.summary.columns}
                />
              </div>

              {activeTab === "ai" && (
                <div className="ai-suggestions">
                  <h3>Suggested investigations</h3>
                  <p className="ai-label">
                    AI-generated questions for further review.
                    These checks have not been performed.
                  </p>

                  <Markdown skipHtml>
                    {investigation.suggested_investigations}
                  </Markdown>
                </div>
              )}
            </div>

            <details>
              <summary>View full API response</summary>
              <pre className="json-result">
                {JSON.stringify(investigation, null, 2)}
              </pre>
            </details>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;